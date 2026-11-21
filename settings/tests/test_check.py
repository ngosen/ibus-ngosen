# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from ngosen_settings import check
from ngosen_settings import system_check as sc


class NoGnome:
    def get(self):
        return None

    def ibus_engines(self):
        return None

    def switch_keys(self):
        return [], []


FOUND = [
    sc.Finding(sc.OK, "IBus is running", "unused fix"),
    sc.Finding(sc.FAIL, "Ngó Sen is not an input source", "Add it in Settings.", "add", "cmd x"),
]


class TerminalReportTest(unittest.TestCase):
    def test_starts_with_the_guide_and_gives_each_fix(self):
        f = sc.Facts(env={"XDG_SESSION_TYPE": "wayland"}, ngosen_version="1.3.0")
        text = sc.terminal_report(f, FOUND)
        self.assertTrue(
            text.startswith("# Ngó Sen (IBus) check. Guide for AI assistants: https://")
        )
        self.assertIn("[X] Ngó Sen is not an input source\n    Add it in Settings.", text)
        self.assertNotIn("unused fix", text)
        self.assertNotIn("cmd x", text)


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def test_reads_the_saved_settings_without_an_engine(self):
        with open(os.path.join(self.folder, "ngosen.conf"), "w", encoding="utf-8") as f:
            f.write("DirectTyping=True\nOutputCharset=TCVN3\n")
        values, _folder = check.saved_settings("/nonexistent/ibus-engine-ngosen", self.folder)
        self.assertEqual(values["DirectTyping"], "True")
        self.assertEqual(values["OutputCharset"], "TCVN3")

    def test_passes_the_settings_to_the_check(self):
        with open(os.path.join(self.folder, "ngosen.conf"), "w", encoding="utf-8") as f:
            f.write("DirectTyping=True\nToggleKey=Alt+z\n")
        with mock.patch.object(sc, "collect", wraps=sc.collect) as collect:
            text = check.check("/nonexistent", "1.3.0", NoGnome(), self.folder)
        kwargs = collect.call_args.kwargs
        self.assertTrue(kwargs["direct_typing"])
        self.assertTrue(kwargs["toggle_key"])
        self.assertEqual(
            kwargs["app_modes_file"], os.path.join(self.folder, "ngosen-app-rules.conf")
        )
        self.assertTrue(text.startswith("# Ngó Sen (IBus) check."))

    def test_needs_no_gtk(self):
        code = "import sys; import ngosen_settings.check; print('gi.repository.Gtk' in sys.modules)"
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        self.assertEqual(out.stdout.strip(), "False", out.stderr)


if __name__ == "__main__":
    unittest.main()
