import unittest2

from reportbug import checkversions

class TestCheckversions(unittest2.TestCase):

    def test_compare_versions(self):
        # <current, upstream>
        # 1 upstream newer than current
        # 0 same version or upsteam none
        # -1 current newer than upstream
        self.assertEqual(checkversions.compare_versions('1.2.3', '1.2.4'), 1)

        self.assertEqual(checkversions.compare_versions('123', None), 0)
        self.assertEqual(checkversions.compare_versions('1.2.3', '1.2.3'), 0)
        self.assertEqual(checkversions.compare_versions(None, None), 0)

        self.assertEqual(checkversions.compare_versions('1.2.4', '1.2.3'), -1)

    def test_later_version(self):
        # mock the test_compare_Versions() test

        self.assertEqual(checkversions.later_version('1.2.3', '1.2.4'), '1.2.4')

        self.assertEqual(checkversions.later_version('123', None), '123')
        self.assertEqual(checkversions.later_version('1.2.3', '1.2.3'), '1.2.3')
        self.assertIsNone(checkversions.later_version(None, None))

        self.assertEqual(checkversions.later_version('1.2.4', '1.2.3'), '1.2.4')
