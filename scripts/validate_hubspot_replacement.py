"""Read-only live readiness report. Aggregate output only; no CRM export committed."""
import collections
import csv
import json
import math
import re
from pathlib import Path
from sync_hubspot_at import api, mapping, norm, coordinates, export_rows


def main():
    props = api('/crm/v3/properties/companies')['results']
    try:
        config = mapping(props)
    except ValueError:
        # Definitions are metadata, never company record values.
        for prop in props:
            if norm(prop.get('name')) == 'lifecyclestage' or 'public' in norm(prop.get('label')):
                print('Filter definition:', json.dumps({k: prop.get(k) for k in
                      ('name', 'label', 'options')}, ensure_ascii=False))
        raise
    lc, public, networks, yes = config
    available = {p['name'] for p in props}
    wanted = ['name', 'address', 'zip', 'city', 'country', 'hs_country_code', 'country_code',
              'land', 'partner_id', 'forms_partner_id_focus_id', 'unternehmensname_mit_id',
              'latitude', 'longitude', 'hs_latitude', 'hs_longitude',
              'hs_gps_latitude', 'hs_gps_longitude', 'kundenstatus', lc, public]
    records, after, seen = [], None, set()
    while True:
        params = {'limit': 100, 'properties': ','.join(k for k in wanted if k in available)}
        if after is not None:
            params['after'] = after
        page = api('/crm/v3/objects/companies', params)
        records.extend(page['results'])
        after = page.get('paging', {}).get('next', {}).get('after')
        if after is None:
            break
        if str(after) in seen:
            raise ValueError('Repeated cursor')
        seen.add(str(after))
    at = records  # No country gate: HubSpot country metadata is unreliable.
    eligible = [r for r in at if r['properties'].get(lc) in networks
                and r['properties'].get(public) == yes]
    incomplete = [r for r in eligible if not all(str(r['properties'].get(k) or '').strip()
                  for k in ('name', 'address', 'zip', 'city'))]
    print('READINESS_REPORT')
    status_prop = next((p for p in props if p['name']=='kundenstatus'), None)
    print('Status field metadata:', json.dumps(status_prop, ensure_ascii=False))
    print('Allowed-lifecycle status counts:', dict(collections.Counter(r['properties'].get('kundenstatus') or '<empty>' for r in records if r['properties'].get(lc) in networks)))
    from sync_hubspot_at import INTERNAL_EXCEPTIONS
    print('Czeczelits exception status counts:', dict(collections.Counter(r['properties'].get('kundenstatus') or '<empty>' for r in records if str(r['id']) in INTERNAL_EXCEPTIONS)))

    print('HubSpot companies scanned (all countries):', len(at))
    print('Allowed lifecycle:', sum(r['properties'].get(lc) in networks for r in at))
    print('Public + allowed lifecycle:', len(eligible))
    print('Eligible by network:', dict(collections.Counter(networks[r['properties'][lc]] for r in eligible)))
    print('Eligible incomplete address:', len(incomplete))
    print('Eligible missing coordinates:', sum(not coordinates(r['properties'])[0] for r in eligible))
    print('Eligible coordinates by network:', dict(collections.Counter(networks[r['properties'][lc]]
          for r in eligible if coordinates(r['properties'])[0])))
    old_rows = list(csv.reader(Path('daten.csv').open(encoding='utf-8-sig', newline='')))
    hi = next(i for i, row in enumerate(old_rows) if 'KST' in row and 'Netzwerk' in row)
    old = [dict(zip(old_rows[hi], row)) for row in old_rows[hi+1:] if any(row)]
    def keys(p, legacy=False):
        name, street, city, zip_code = (p.get(k) for k in
            (('Gesellschaft', 'Strasse', 'Ort', 'PLZ') if legacy else ('name', 'address', 'city', 'zip')))
        name = re.sub(r'^\s*\d{3}[A-Za-z]\s+', '', str(name or ''))
        street = re.sub(r'str\.(?=\s|$)', 'strasse', str(street or ''), flags=re.I)
        keys = set()
        if norm(street) and norm(city): keys.add(('address', norm(street), norm(city)))
        if norm(street) and norm(zip_code): keys.add(('streetzip', norm(street), norm(zip_code).removeprefix('a')))
        if norm(name) and norm(city): keys.add(('namecity', norm(name), norm(city)))
        fields = ('KST', 'Netzkennung') if legacy else ('partner_id', 'forms_partner_id_focus_id')
        for k in fields:
            if norm(p.get(k)): keys.add(('id', norm(p[k])))
        return keys
    indexed = collections.defaultdict(set)
    for i, record in enumerate(at):
        for key in keys(record['properties']): indexed[key].add(i)
    distances = []
    result, bynetwork, used = collections.Counter(), collections.defaultdict(collections.Counter), set()
    unresolved = collections.defaultdict(list)
    for legacy_index, row in enumerate(old, 1):
        matches = set()
        rowkeys = keys(row, True)
        for tier in ('streetzip', 'address', 'id', 'namecity'):
            for key in rowkeys:
                if key[0] == tier: matches.update(indexed[key])
            if matches: break
        if len(matches) > 1:
            # Same address may have an old operator and a current company.
            named = [i for i in matches if norm(row.get('Gesellschaft')) == norm(
                re.sub(r'^\s*\d{3}[A-Za-z]\s+', '', str(at[i]['properties'].get('name') or '')))]
            identified = [i for i in matches if any(k[0]=='id' and k in keys(at[i]['properties']) for k in rowkeys)]
            if len(identified)==1: matches=set(identified)
            elif len(named)==1: matches=set(named)
        if len(matches) != 1:
            category = 'ambiguous' if matches else 'not_matched'
        else:
            idx = next(iter(matches)); used.add(idx); p = at[idx]['properties']
            if p.get(lc) not in networks: category = 'excluded_lifecycle'
            elif p.get(public) != yes: category = 'excluded_public_status'
            elif not coordinates(p)[0]: category = 'eligible_missing_coordinates'
            else:
                category = 'eligible_with_coordinates'
                try:
                    a,b = coordinates(p)
                    x,y = (float(str(row[k]).replace(',', '.')) for k in ('Lat./Breitengard','Long./Längengrad'))
                    lat1,lat2 = math.radians(x),math.radians(float(a))
                    dlat,dlon = lat2-lat1,math.radians(float(b)-y)
                    km=6371*2*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))
                    distances.append(km)
                except (ValueError, KeyError): pass
        if category in ("not_matched", "ambiguous"):
            unresolved[category].append(legacy_index)
        result[category] += 1
        bynetwork[row.get('Netzwerk', '')][category] += 1
    print('Legacy unresolved row ordinals (1-based data rows):', json.dumps(dict(unresolved)))
    print('Legacy CSV rows:', len(old))
    print('Legacy match categories:', dict(result))
    print('Matched public locations with position deviation >1km:', sum(d>1 for d in distances))
    print('Matched public locations with position deviation >5km:', sum(d>5 for d in distances))
    print('Legacy match categories by network:', {k: dict(v) for k,v in bynetwork.items()})
    print('Eligible HubSpot companies not uniquely linked to legacy rows:',
          sum(i not in used and r in eligible for i,r in enumerate(at)))
    for audience in ('public', 'internal'):
        try:
            output = export_rows(records, config, audience)
            print('EXPORT_AUDIENCE:', audience, '| rows:', len(output),
                  '| networks:', dict(collections.Counter(r[1] for r in output)),
                  '| missing_coordinates:', sum(not r[8] for r in output))
        except ValueError as exc:
            print('EXPORT_AUDIENCE:', audience, '| ERROR:', str(exc))
            if audience == 'internal': raise
    if incomplete:
        print('EXPORT_READY: NO - incomplete addresses')
    else:
        rows = export_rows(records, config)
        print('Actual export validation rows:', len(rows))
        print('EXPORT_READY: YES')
    print('MAP_COORDINATES_PRESENT:', 'YES' if eligible and not incomplete and all(coordinates(r['properties'])[0]
          for r in eligible) else 'NO')
    print('Read only. No files changed; no names, addresses, IDs or tokens logged.')


if __name__ == '__main__':
    main()
