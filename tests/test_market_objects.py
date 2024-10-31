# SPDX-FileCopyrightText: Florian Maurer
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import unittest

from emarketpy.market_objects import OnlyHours


class TestOnlyHours(unittest.TestCase):
    def test_only_hours_creation(self):
        hours = OnlyHours(9, 17)
        self.assertEqual(hours[0], 9)
        self.assertEqual(hours[1], 17)

    def test_only_hours_unpacking(self):
        start, end = OnlyHours(8, 16)
        self.assertEqual(start, 8)
        self.assertEqual(end, 16)

    def test_only_hours_equality(self):
        hours1 = OnlyHours(10, 18)
        hours2 = OnlyHours(10, 18)
        hours3 = OnlyHours(9, 17)
        self.assertEqual(hours1, hours2)
        self.assertNotEqual(hours1, hours3)

    def test_only_hours_repr(self):
        hours = OnlyHours(11, 19)
        self.assertEqual(repr(hours), "OnlyHours(begin_hour=11, end_hour=19)")


if __name__ == "__main__":
    unittest.main()
