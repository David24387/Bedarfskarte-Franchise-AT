import unittest
from sync_hubspot_at import LIFECYCLES, mapping, export_rows


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

    def test_excludes_nonpublic_missing_public_unknown_lifecycle_and_other_country(self):
        records = [self.record(public='no'), self.record(public=None),
                   self.record(lifecyclestage='customer'), self.record(country='DE')]
        self.assertEqual(export_rows(records, self.config), [])

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
