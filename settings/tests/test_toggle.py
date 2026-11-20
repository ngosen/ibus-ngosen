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

    def requests(self):
        if not os.path.isdir(self.folder):
            return []
        return [n for n in os.listdir(self.folder) if n.startswith(toggle.REQUEST_PREFIX)]

    def run_toggle(self, engine, running=True):
        return toggle.toggle(self.folder, lambda: engine, lambda: running)

    def test_each_run_leaves_its_own_request(self):
        self.assertEqual(self.run_toggle("ngosen"), (0, ""))
        self.assertEqual(self.run_toggle("ngosen"), (0, ""))
        self.assertEqual(len(self.requests()), 2)

    def test_nothing_is_left_when_another_input_source_is_in_use(self):
        code, message = self.run_toggle("xkb:us::eng")
        self.assertEqual(code, 1)
        self.assertIn("not the input source in use", message)
        self.assertEqual(self.requests(), [])

    def test_nothing_is_left_without_ibus(self):
        self.assertEqual(self.run_toggle("", running=False), (1, "IBus is not running."))
        self.assertEqual(self.requests(), [])

    def test_a_request_is_left_when_each_field_has_its_own_engine(self):
        # ibus engine names no engine then; the engine decides.
        self.assertEqual(self.run_toggle(""), (0, ""))
        self.assertEqual(len(self.requests()), 1)

    def test_the_request_has_a_name_the_engine_takes(self):
        # src/ngosen-ibus-resources.cpp, isToggleName
        self.run_toggle("ngosen")
        self.assertTrue(self.requests()[0].startswith("toggle-"))


if __name__ == "__main__":
    unittest.main()
