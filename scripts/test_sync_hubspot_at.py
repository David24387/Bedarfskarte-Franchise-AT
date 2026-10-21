import unittest
from sync_hubspot_at import LIFECYCLES, mapping, export_rows, INTERNAL_EXCEPTIONS


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.props = [
            {'name': 'lifecyclestage', 'options': [
                {'label': label, 'value': str(i)} for i, label in enumerate(LIFECYCLES)]},
            {'name': 'public', 'label': 'Public_Status', 'options': [
                {'label': 'Public', 'value': 'yes'},
                {'label': 'Not public', 'value': 'no'}]}]
        self.config = mapping(self.props)

    def record(self, i='1', **changes):
        props = dict(lifecyclestage='0', public='yes', country='Österreich',
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

    def test_internal_includes_nonpublic_regular_partners_and_new_records(self):
        records = [self.record('new-1', public='no'), self.record('new-2', public=None)]
        self.assertEqual(len(export_rows(records, self.config, audience='internal')), 2)
        self.assertEqual(export_rows(records, self.config, audience='public'), [])

    def test_internal_explicit_czeczelits_exceptions_do_not_leak_to_public_export(self):
        records = [self.record(i, public='no', lifecyclestage='inactive') for i in INTERNAL_EXCEPTIONS]
        self.assertEqual([r[1] for r in export_rows(records, self.config, 'internal')], ['PLP', 'PLP'])
        self.assertEqual(export_rows(records, self.config, 'public'), [])
        self.assertEqual(export_rows([self.record('other-inactive', lifecyclestage='inactive')], self.config, 'internal'), [])

    def test_archived_partner_is_never_exported(self):
        row = self.record(); row['archived'] = True
        self.assertEqual(export_rows([row], self.config, 'internal'), [])

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


if __name__ == '__main__':
    unittest.main()
