import unittest
from unittest.mock import patch
from sync_hubspot_at import LIFECYCLES, mapping, export_rows as internal_export_rows, detail_mapping, export_details, fetch_partner_details


def export_rows(records, config, audience='public'):
    return internal_export_rows(records, config, audience)

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.props = [
            {'name': 'lifecyclestage', 'options': [
                {'label': label, 'value': str(i)} for i, label in enumerate(LIFECYCLES)]},
            {'name': 'public', 'label': 'Public_Status', 'options': [
                {'label': 'Public', 'value': 'yes'},
                {'label': 'Not public', 'value': 'no'}]},
            {'name':'kundenstatus','options':[{'label':'Aktiv','value':'Aktiv'},{'label':'Inaktiv','value':'Inaktiv'}]}]
        self.config = mapping(self.props)

    def record(self, i='1', **changes):
        props = dict(kundenstatus='Aktiv', lifecyclestage='0', public='yes', country='Österreich',
                     name='Test GmbH', address='Teststraße 1', zip='1010', city='Wien',
                     latitude='48,2', longitude='16,3')
        props.update(changes)
        return dict(id=i, properties=props)

    def test_all_four_lifecycles_and_frpl_mapping(self):
        rows = export_rows([self.record(str(i), lifecyclestage=str(i))
                            for i in range(4)], self.config)
        self.assertEqual([r[1] for r in rows], ['Franchise', 'Franchise', 'EFR', 'PLP'])

    def test_excludes_nonpublic_missing_public_unknown_lifecycle(self):
        records = [self.record(public='no'), self.record(public=None),
                   self.record(lifecyclestage='customer')]
        self.assertEqual(export_rows(records, self.config), [])

    def test_country_metadata_does_not_override_explicit_publication_rules(self):
        for country in ('DE', 'United States', None, ''):
            self.assertEqual(len(export_rows([self.record(country=country)], self.config)), 1)

    def test_new_public_partner_is_added_without_legacy_csv(self):
        rows = export_rows([self.record('new-company')], self.config)
        self.assertEqual(rows[0][0], 'new-company')

    def test_no_audience_can_bypass_public_filter(self):
        for public in ('no', None, '', 'unknown'):
            self.assertEqual(export_rows([self.record(public=public)], self.config), [])
        self.assertEqual(len(export_rows([self.record(public='no')], self.config, 'internal')), 1)
        for state in ('Inaktiv', None, ''):
            self.assertEqual(export_rows([self.record(kundenstatus=state)], self.config, 'internal'), [])
            self.assertEqual(export_rows([self.record(kundenstatus=state)], self.config, 'public'), [])

    def test_departed_deleted_and_revoked_partners_leave_snapshot(self):
        self.assertEqual(export_rows([self.record(lifecyclestage='inactive')], self.config), [])
        self.assertEqual(export_rows([self.record(public='no')], self.config), [])
        self.assertEqual(export_rows([], self.config), [])

    def test_archived_partner_is_never_exported(self):
        row = self.record(); row['archived'] = True
        self.assertEqual(export_rows([row], self.config), [])

    def test_update_and_revoke_snapshot(self):
        self.assertEqual(export_rows([self.record(name='New name')], self.config)[0][4], 'New name')
        self.assertEqual(export_rows([self.record(public='no')], self.config), [])

    def test_internal_values_are_resolved_from_labels(self):
        self.assertEqual(self.config[1], 'public')
        self.assertEqual(self.config[3], 'yes')
        self.props[0]['options'].pop()
        with self.assertRaises(ValueError):
            mapping(self.props)

    def test_missing_coordinates_keep_directory_entry_without_inventing_position(self):
        row = export_rows([self.record(latitude=None)], self.config)[0]
        self.assertEqual(row[8:], ['', ''])

    def test_incomplete_address_and_duplicate_id_fail(self):
        with self.assertRaises(ValueError):
            export_rows([self.record(address='')], self.config)
        with self.assertRaises(ValueError):
            export_rows([self.record(), self.record()], self.config)

    def test_details_only_include_published_ids_and_allowed_fields(self):
        props = [{'name': 'services', 'options': [{'value': 'tyres', 'label': 'Reifen'}]},
                 {'name': 'owneremail'}, {'name': 'rechnungs_kontakt_e_mailadresse'}]
        records = [self.record(services='tyres', phone='SECRET'), self.record('2', public='no')]
        details = export_details(records, export_rows(records, self.config), detail_mapping(props))
        self.assertEqual(details['partners'], [{'id': '1', 'services': ['Reifen'], 'partnerType': ''}])
        self.assertEqual(export_details(records, [], detail_mapping(props))['partners'], [])

    def test_ambiguous_detail_alias_fails_instead_of_guessing(self):
        with self.assertRaises(ValueError):
            detail_mapping([{'name': 'state'}, {'name': 'custom_state', 'label': 'State'}])

    def test_missing_detail_fields_are_not_invented(self):
        self.assertEqual(detail_mapping([]), {})
        records = [self.record()]
        self.assertEqual(export_details(records, export_rows(records, self.config), {})['partners'], [{'id': '1', 'partnerType': ''}])


class AdditionalFieldTests(unittest.TestCase):
    def test_verified_hubspot_fields_and_labels(self):
        props = [{'name': n, 'options': []} for n in ['ermweb', 'bg_status', 'phone', 'e_mail_adresse', 'kundenstatus', 'firmenbuchnummer', 'ust_idnr', 'vertragsstartdatum', 'geschaftsfuhrung']]
        props.append({'name': 'lifecyclestage', 'options': [{'value': 'light', 'label': 'Partner (FRPL–Franchise Partner Light)'}]})
        fields = detail_mapping(props)
        record = {'id': '1', 'properties': {'ermweb': 'https://example.com', 'bg_status': 'Nein', 'phone': '+43 123', 'e_mail_adresse': 'demo@example.com', 'kundenstatus': 'Aktiv', 'firmenbuchnummer': 'FN-DEMO', 'ust_idnr': 'AT-DEMO', 'vertragsstartdatum': '1577836800000', 'geschaftsfuhrung': 'Demo <Name>', 'lifecyclestage': 'light'}}
        partner = export_details([record], [['1']], fields)['partners'][0]
        self.assertEqual(partner['locationUrl'], 'https://example.com')
        self.assertEqual(partner['contractStart'], '2020-01-01')
        self.assertEqual(partner['partnerType'], 'FRPL')
        self.assertEqual(partner['partnerStatus'], 'Aktiv')
        self.assertEqual(partner['oem'], 'Nein')
        self.assertEqual(partner['management'], 'Demo <Name>')

    @patch('sync_hubspot_at.api')
    def test_additional_fields_only_requested_for_eligible_ids(self, api):
        api.return_value = {'status': 'COMPLETE', 'results': [{'id': 'public-1'}]}
        fetch_partner_details([['public-1']], {'email': {'name': 'e_mail_adresse'}})
        self.assertEqual(api.call_args.kwargs['body']['inputs'], [{'id': 'public-1'}])
        self.assertEqual(api.call_args.kwargs['body']['properties'], ['e_mail_adresse'])
        api.reset_mock()
        self.assertEqual(fetch_partner_details([], {'email': {'name': 'e_mail_adresse'}}), [])
        api.assert_not_called()

    @patch('sync_hubspot_at.api')
    def test_partial_batch_cannot_publish_incomplete_profiles(self, api):
        api.return_value = {'status': 'COMPLETE', 'results': []}
        with self.assertRaises(ValueError):
            fetch_partner_details([['missing']], {'email': {'name': 'e_mail_adresse'}})


if __name__ == '__main__':
    unittest.main()
