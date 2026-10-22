#!/usr/bin/env python3
"""Export active AT partners by audience. No CRM values or credentials in logs."""
import csv
from datetime import datetime, timezone
import argparse
import io
import json
import os
from pathlib import Path
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

LIFECYCLES = {
    'Partner (FRP-Franchise)': 'Franchise',
    'Partner (FRPL–Franchise Partner Light)': 'Franchise',
    'Partner (EFR)': 'EFR',
    'Partner (PLP)': 'PLP',
}
HEADER = ['KST', 'Netzwerk', 'Status', 'Netzkennung', 'Gesellschaft', 'Strasse',
          'PLZ', 'Ort', 'Lat./Breitengard', 'Long./Längengrad']

# Exact aliases only; never collect unrelated free-text or contact properties.
DETAIL_FIELDS = {
    'state': ('state', 'bundesland'),
    'services': ('dienstleistungen', 'leistungen', 'services'),
    'openingHours': ('kernoeffnungszeiten', 'kernöffnungszeiten', 'oeffnungszeiten', 'öffnungszeiten', 'opening_hours'),
    'website': ('website',),
    'locationUrl': ('ermweb', 'euromaster_standort_url', 'euromaster_link', 'standort_url'),
    'oem': ('bg_status', 'oem'),
    'phone': ('phone',),
    'email': ('e_mail_adresse',),
    'partnerStatus': ('kundenstatus',),
    'lifecycle': ('lifecyclestage',),
    'companyRegister': ('firmenbuchnummer',),
    'vatId': ('ust_idnr',),
    'contractStart': ('vertragsstartdatum',),
    'management': ('geschaftsfuhrung',),
}


def detail_mapping(properties):
    result = {}
    for field, aliases in DETAIL_FIELDS.items():
        for alias in aliases:
            matches = [p for p in properties if norm(p['name']) == norm(alias)
                       or norm(p.get('label')) == norm(alias)]
            if len(matches) > 1:
                raise ValueError('Ambiguous directory property: ' + field)
            if matches:
                result[field] = matches[0]
                break
    return result


def export_details(records, rows, fields):
    eligible = {r[0] for r in rows}
    partners = []
    for record in records:
        if str(record['id']) not in eligible:
            continue
        partner = {'id': str(record['id'])}
        for field, prop in fields.items():
            value = str(record.get('properties', {}).get(prop['name']) or '').strip()
            labels = {o['value']: o['label'] for o in prop.get('options', [])}
            if field == 'services':
                partner[field] = [labels.get(v.strip(), v.strip()) for v in value.split(';') if v.strip()]
            elif field == 'contractStart':
                try:
                    partner[field] = (datetime.fromtimestamp(float(value) / 1000, timezone.utc).date().isoformat()
                                      if value.isdigit() else datetime.fromisoformat(value.replace('Z', '+00:00')).date().isoformat()) if value else ''
                except (ValueError, OverflowError, OSError):
                    raise ValueError('Invalid contract date; export unchanged') from None
            else:
                partner[field] = labels.get(value, value)
        lifecycle = partner.get('lifecycle', '')
        partner['partnerType'] = next((code for code, label in [
            ('FRP', 'Partner (FRP-Franchise)'), ('FRPL', 'Partner (FRPL–Franchise Partner Light)'),
            ('EFR', 'Partner (EFR)'), ('PLP', 'Partner (PLP)')]
            if norm(lifecycle) == norm(label)), '')
        partners.append(partner)
    return {'schemaVersion': 1, 'source': 'HubSpot',
            'partners': sorted(partners, key=lambda p: p['id'])}


def norm(value):
    return re.sub(r'[^a-z0-9]', '', ''.join(
        c for c in unicodedata.normalize('NFKD', str(value or '').casefold())
        if not unicodedata.combining(c)))


def api(path, params=None, body=None):
    url = 'https://api.hubapi.com' + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    for attempt in range(5):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers={
            'Authorization': 'Bearer ' + os.environ['HUBSPOT_TOKEN'],
            'Accept': 'application/json', 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise RuntimeError('HubSpot HTTP %s; export unchanged' % exc.code) from None
            time.sleep(2 ** attempt)
    raise RuntimeError('HubSpot unavailable')


def fetch_partner_details(rows, fields):
    """Additional company fields are requested only for eligible Public partners."""
    records = []
    ids = [r[0] for r in rows]
    if not fields:
        return [{'id': id, 'properties': {}} for id in ids]
    for offset in range(0, len(ids), 100):
        batch = ids[offset:offset + 100]
        result = api('/crm/v3/objects/companies/batch/read', body={
            'properties': sorted({p['name'] for p in fields.values()}),
            'inputs': [{'id': id} for id in batch]})
        received = result.get('results', [])
        if (result.get('errors') or result.get('numErrors') or
                result.get('status') not in (None, 'COMPLETE') or
                len(received) != len(batch) or
                {str(r['id']) for r in received} != set(batch)):
            raise ValueError('Incomplete partner details; export unchanged')
        records.extend(received)
    return records


def resolve_property(properties, label):
    matches = [p for p in properties if norm(p['name']) == norm(label)
               or norm(p.get('label')) == norm(label)]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous property: ' + label)
    return matches[0]


def resolve_option(prop, label):
    matches = [o['value'] for o in prop.get('options', [])
               if norm(o.get('label')) == norm(label)]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous option: ' + label)
    return matches[0]


def mapping(properties):
    lifecycle = resolve_property(properties, 'lifecyclestage')
    public = resolve_property(properties, 'Public_Status')
    networks = {resolve_option(lifecycle, label): network
                for label, network in LIFECYCLES.items()}
    if len(networks) != 4:
        raise ValueError('Lifecycle values must be distinct')
    active = resolve_property(properties, 'kundenstatus')
    return lifecycle['name'], public['name'], networks, resolve_option(public, 'Public'), active['name'], resolve_option(active, 'Aktiv')


def coordinates(p):
    for a, b in [('latitude', 'longitude'), ('hs_latitude', 'hs_longitude'),
                 ('hs_gps_latitude', 'hs_gps_longitude')]:
        try:
            lat, lng = [float(str(p.get(k) or '').replace(',', '.')) for k in (a, b)]
            if 46.2 <= lat <= 49.1 and 9.4 <= lng <= 17.3:
                return str(lat), str(lng)
        except ValueError:
            pass
    return '', ''


def export_rows(records, config, audience='internal'):
    if audience not in ('public', 'internal'):
        raise ValueError('Unknown audience')
    lifecycle, public, networks, public_value, active, active_value = config
    rows = []
    for record in records:
        p = record.get('properties', {})
        network = networks.get(p.get(lifecycle))
        if not network or p.get(active) != active_value or (audience == 'public' and p.get(public) != public_value):
            continue
        if record.get('archived'):
            continue
        if not all(str(p.get(k) or '').strip() for k in ('name', 'address', 'zip', 'city')):
            raise ValueError('Eligible partner has incomplete business address; export unchanged')
        lat, lng = coordinates(p)
        rows.append([str(record['id']), network, 'geöffnet',
                     p.get('partner_id') or p.get('forms_partner_id_focus_id') or '',
                     p['name'], p['address'], p['zip'], p['city'], lat, lng])
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError('Duplicate HubSpot company ID')
    return sorted(rows, key=lambda r: r[0])


def fetch_active(properties, request=None):
    request = request or api
    config = mapping(properties)
    lifecycle, public, networks, public_value, active, active_value = config
    names = {p['name'] for p in properties}
    fields = detail_mapping(properties)
    wanted = {'name', 'address', 'zip', 'city', 'partner_id', 'forms_partner_id_focus_id',
        'latitude', 'longitude', 'hs_latitude', 'hs_longitude', 'hs_gps_latitude',
        'hs_gps_longitude', lifecycle, public, active}
    wanted.update(p['name'] for p in fields.values())
    records, after, cursors = [], None, set()
    while True:
        body = {'filterGroups': [{'filters': [
            {'propertyName': lifecycle, 'operator': 'IN', 'values': list(networks)},
            {'propertyName': active, 'operator': 'EQ', 'value': active_value}
        ]}], 'properties': sorted(wanted & names), 'limit': 100}
        if after is not None:
            body['after'] = str(after)
        page = request('/crm/v3/objects/companies/search', body=body)
        if not isinstance(page.get('results'), list) or int(page.get('total', 0)) >= 10000:
            raise ValueError('Invalid or oversized search response')
        records.extend(page['results'])
        after = page.get('paging', {}).get('next', {}).get('after')
        if after is None:
            if 'total' not in page or len(records) != int(page['total']):
                raise ValueError('Incomplete search response')
            break
        if str(after) in cursors or len(cursors) >= 99:
            raise ValueError('Invalid search pagination')
        cursors.add(str(after))
    for record in records:
        p = record.get('properties', {})
        if p.get(active) != active_value or p.get(lifecycle) not in networks:
            raise ValueError('Search filter mismatch')
    return records, config, fields


def main():
    if not os.environ.get('HUBSPOT_TOKEN'):
        raise SystemExit('HUBSPOT_TOKEN secret missing in Bedarfskarte-Franchise-AT')
    properties = api('/crm/v3/properties/companies')['results']
    records, config, fields = fetch_active(properties)
    rows = export_rows(records, config, 'internal')
    details = export_details(records, rows, fields)
    details.update(audience='internal', selection='active')
    buf = io.StringIO(newline=''); writer = csv.writer(buf); writer.writerow(HEADER); writer.writerows(rows)
    status = {'schemaVersion':1, 'source':'HubSpot', 'audience':'internal', 'selection':'active',
              'exportedAt':datetime.now(timezone.utc).isoformat(), 'partners':len(rows),
              'missingCoordinates':sum(not r[8] for r in rows)}
    outputs = {'daten.csv':buf.getvalue(), 'standorte.json':json.dumps(details,ensure_ascii=False),
               'export_status.json':json.dumps(status,ensure_ascii=False)}
    for name, content in outputs.items():
        Path(name+'.new').write_text(content,encoding='utf-8')
    for name in outputs: Path(name+'.new').replace(name)
    print('Active partners including Non Public:',len(rows),'| Missing coordinates:',status['missingCoordinates'])

if __name__ == '__main__':
    try: main()
    except (ValueError, RuntimeError) as exc: raise SystemExit(str(exc)) from None
    except Exception: raise SystemExit('Sync failed; previous snapshot unchanged; no raw CRM data logged.') from None
