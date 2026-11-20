# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import unittest

from ngosen_settings import toggle


class ToggleTest(unittest.TestCase):
    def setUp(self):
        self.folder = os.path.join(tempfile.mkdtemp(), "ngosen")
        self.request = os.path.join(self.folder, toggle.REQUEST)

    def test_leaves_a_request_for_the_engine_in_use(self):
        self.assertEqual(toggle.toggle(self.folder, lambda: "ngosen"), (0, ""))
        self.assertTrue(os.path.exists(self.request))

    def test_nothing_is_left_when_another_input_source_is_in_use(self):
        code, message = toggle.toggle(self.folder, lambda: "xkb:us::eng")
        self.assertEqual(code, 1)
        self.assertIn("not the input source in use", message)
        self.assertFalse(os.path.exists(self.request))

    def test_nothing_is_left_without_ibus(self):
        self.assertEqual(toggle.toggle(self.folder, lambda: ""), (1, "IBus is not running."))
        self.assertFalse(os.path.exists(self.request))

    def test_the_request_has_the_name_the_engine_watches(self):
        # src/ngosen-ibus-config.cpp, SettingsPaths::toggleRequest
        self.assertEqual(toggle.REQUEST, "toggle")


if __name__ == "__main__":
    unittest.main()
