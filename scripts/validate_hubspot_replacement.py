"""Read-only live readiness report. Aggregate output only; no CRM export committed."""
import collections
import csv
import json
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
              'hs_gps_latitude', 'hs_gps_longitude', lc, public]
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
    at = [r for r in records if any(norm(r['properties'].get(k)) in
          ('at', 'aut', 'austria', 'osterreich') for k in
          ('country', 'hs_country_code', 'country_code', 'land'))]
    eligible = [r for r in at if r['properties'].get(lc) in networks
                and r['properties'].get(public) == yes]
    incomplete = [r for r in eligible if not all(str(r['properties'].get(k) or '').strip()
                  for k in ('name', 'address', 'zip', 'city'))]
    print('READINESS_REPORT')
    print('HubSpot AT companies:', len(at))
    print('Allowed lifecycle AT:', sum(r['properties'].get(lc) in networks for r in at))
    print('Public + allowed lifecycle AT:', len(eligible))
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
        keys = set()
        if norm(street) and norm(city): keys.add(('address', norm(street), norm(city)))
        if norm(street) and norm(zip_code): keys.add(('streetzip', norm(street), norm(zip_code).removeprefix('a')))
        if norm(name) and norm(city): keys.add(('namecity', norm(name), norm(city)))
        fields = ('Netzkennung',) if legacy else ('partner_id', 'forms_partner_id_focus_id')
        for k in fields:
            if norm(p.get(k)): keys.add(('id', norm(p[k])))
        return keys
    indexed = collections.defaultdict(set)
    for i, record in enumerate(at):
        for key in keys(record['properties']): indexed[key].add(i)
    result, bynetwork, used = collections.Counter(), collections.defaultdict(collections.Counter), set()
    for row in old:
        matches = set()
        for key in keys(row, True): matches.update(indexed[key])
        if len(matches) != 1:
            category = 'ambiguous' if matches else 'not_matched'
        else:
            idx = next(iter(matches)); used.add(idx); p = at[idx]['properties']
            if p.get(lc) not in networks: category = 'excluded_lifecycle'
            elif p.get(public) != yes: category = 'excluded_public_status'
            elif not coordinates(p)[0]: category = 'eligible_missing_coordinates'
            else: category = 'eligible_with_coordinates'
        result[category] += 1
        bynetwork[row.get('Netzwerk', '')][category] += 1
    print('Legacy CSV rows:', len(old))
    print('Legacy match categories:', dict(result))
    print('Legacy match categories by network:', {k: dict(v) for k,v in bynetwork.items()})
    print('Eligible HubSpot companies not uniquely linked to legacy rows:',
          sum(i not in used and r in eligible for i,r in enumerate(at)))
    if incomplete:
        print('EXPORT_READY: NO - incomplete addresses')
    else:
        rows = export_rows(records, config)
        print('Actual export validation rows:', len(rows))
        print('EXPORT_READY: YES')
    print('MAP_READY:', 'YES' if eligible and not incomplete and all(coordinates(r['properties'])[0]
          for r in eligible) else 'NO')
    print('Read only. No files changed; no names, addresses, IDs or tokens logged.')


if __name__ == '__main__':
    main()
