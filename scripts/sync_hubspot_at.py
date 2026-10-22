#!/usr/bin/env python3
"""Export only public AT partners. No CRM record values or credentials in logs."""
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
    'locationUrl': ('euromaster_standort_url', 'euromaster_link', 'standort_url'),
    'oem': ('oem',),
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
            else:
                partner[field] = labels.get(value, value)
        partners.append(partner)
    return {'schemaVersion': 1, 'source': 'HubSpot',
            'partners': sorted(partners, key=lambda p: p['id'])}


def norm(value):
    return re.sub(r'[^a-z0-9]', '', ''.join(
        c for c in unicodedata.normalize('NFKD', str(value or '').casefold())
        if not unicodedata.combining(c)))


def api(path, params=None):
    url = 'https://api.hubapi.com' + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    for attempt in range(5):
        req = urllib.request.Request(url, headers={
            'Authorization': 'Bearer ' + os.environ['HUBSPOT_TOKEN'],
            'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise RuntimeError('HubSpot HTTP %s; export unchanged' % exc.code) from None
            time.sleep(2 ** attempt)
    raise RuntimeError('HubSpot unavailable')


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
    return lifecycle['name'], public['name'], networks, resolve_option(public, 'Public')


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


def export_rows(records, config, audience='public'):
    if audience != 'public':
        raise ValueError('Only Public partners may be exported')
    lifecycle, public, networks, public_value = config
    rows = []
    for record in records:
        p = record.get('properties', {})
        network = networks.get(p.get(lifecycle))
        if not network or p.get(public) != public_value:
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audience', choices=('public',), default='public')
    args = parser.parse_args()
    if not os.environ.get('HUBSPOT_TOKEN'):
        raise SystemExit('HUBSPOT_TOKEN secret missing')
    properties = api('/crm/v3/properties/companies')['results']
    config = mapping(properties)
    names = {p['name'] for p in properties}
    fields = detail_mapping(properties)
    wanted = ['name', 'address', 'zip', 'city', 'country', 'hs_country_code',
              'country_code', 'land', 'partner_id', 'forms_partner_id_focus_id',
              'latitude', 'longitude', 'hs_latitude', 'hs_longitude',
              'hs_gps_latitude', 'hs_gps_longitude', config[0], config[1]]
    wanted.extend(p['name'] for p in fields.values())
    records, after, seen = [], None, set()
    while True:
        params = {'limit': 100, 'properties': ','.join(k for k in wanted if k in names)}
        if after is not None:
            params['after'] = after
        page = api('/crm/v3/objects/companies', params)
        records.extend(page['results'])
        after = page.get('paging', {}).get('next', {}).get('after')
        if after is None:
            break
        if str(after) in seen:
            raise ValueError('Repeated pagination cursor')
        seen.add(str(after))
    rows = export_rows(records, config, audience=args.audience)
    details = export_details(records, rows, fields)
    # Empty snapshots are valid: revoked publication must remove old partners too.
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(HEADER)
    writer.writerows(rows)
    missing = sum(not r[8] for r in rows)
    status = {'schemaVersion': 1, 'source': 'HubSpot',
              'exportedAt': datetime.now(timezone.utc).isoformat(),
              'partners': len(rows), 'missingCoordinates': missing,
              'mappedDetailFields': sorted(fields),
              'missingDetailFields': sorted(set(DETAIL_FIELDS) - set(fields))}
    outputs = {'daten.csv': buffer.getvalue(),
               'standorte.json': json.dumps(details, ensure_ascii=False),
               'export_status.json': json.dumps(status, ensure_ascii=False)}
    # Prepare all files before replacement; the workflow publishes one commit.
    for name, content in outputs.items():
        Path(name + '.new').write_text(content, encoding='utf-8')
    for name in outputs:
        Path(name + '.new').replace(Path(name))
    print('Mapped directory fields:', ', '.join(sorted(fields)))
    print('Unavailable directory fields:', ', '.join(status['missingDetailFields']))
    print('HubSpot partners (' + args.audience + '):', len(rows), '| Missing HubSpot coordinates:', missing)
    print('Only business directory fields exported. No individual records logged.')


if __name__ == '__main__':
    main()
