# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import unittest

from ngosen_settings import ini
from ngosen_settings.store import Store, read_text, write_text

try:
    from ngosen_settings import window  # Picks the GTK and libadwaita versions first.

    Adw, GLib = window.Adw, window.GLib
except (ImportError, ValueError):
    window = None


class Vietnamese:
    """Labels that differ from the saved values, as they do in the real window."""

    def gettext(self, text):
        return {"Everywhere": "Mọi nơi", "Non-Start": "Không phải đầu từ"}.get(text, text)


class FakeEngine:
    def __init__(self, folder):
        self.folder = folder

    def dictionary_paths(self):
        return os.path.join(self.folder, "own.dict"), os.path.join(self.folder, "bundled.dict")

    def settings(self):
        return {
            "InputMethod": "Telex",
            "OutputCharset": "Unicode",
            "SpellCheck": "True",
            "W2U": "Non-Start",
            "TimeFormat": "%H:%M:%S %Z",
            "EnableMacro": "True",
            "EnableDictionary": "True",
        }


CAN_RUN = bool(window and os.environ.get("DISPLAY"))
# CI sets this, so a missing package fails the run instead of skipping these tests.
REQUIRED = os.environ.get("NGOSEN_WINDOW_TESTS") == "required"


class RequiredTest(unittest.TestCase):
    @unittest.skipUnless(REQUIRED, "not required here")
    def test_window_tests_run(self):
        self.assertTrue(CAN_RUN, "the window tests need GTK 4, libadwaita and xvfb-run")


@unittest.skipUnless(CAN_RUN, "needs GTK 4, libadwaita and a display")
class WindowTest(unittest.TestCase):
    """Builds the real window on the oldest libadwaita CI has, and saves through its rows."""

    def setUp(self):
        Adw.init()
        window.i18n._translation = Vietnamese()
        self.folder = tempfile.mkdtemp()
        write_text(os.path.join(self.folder, "ngosen.conf"), "SpellCheck=True\nFutureKey=kept\n")
        write_text(os.path.join(self.folder, "bundled.dict"), "việt\nnam\n")
        self.store = Store(FakeEngine(self.folder), self.folder)
        names = {
            "InputMethod": ["Telex", "VNI", "Telex + VNI"],
            "OutputCharset": ["Unicode", "TCVN3 (ABC)"],
        }
        self.window = window.Window(None, self.store, names, "1.0.0")

    def settings(self):
        return ini.parse(read_text(self.store.settings_file))[0]

    def test_switch_saves_and_undoes(self):
        self.window.rows.rows["SpellCheck"].set_active(False)
        self.assertEqual(self.settings(), {"SpellCheck": "False", "FutureKey": "kept"})
        self.assertIsNotNone(self.window.toast)
        self.window.undo()
        self.assertEqual(self.settings()["SpellCheck"], "True")
        self.assertTrue(self.window.rows.rows["SpellCheck"].get_active())

    def test_combo_saves_the_value_not_the_label(self):
        self.window.rows.rows["W2U"].set_selected(2)
        self.window.rows.rows["InputMethod"].set_selected(2)
        self.assertEqual(self.settings()["W2U"], "Everywhere")
        self.assertEqual(self.settings()["InputMethod"], "Telex + VNI")

    def test_hand_written_value_is_kept(self):
        row = self.window.rows.rows["TimeFormat"]
        self.assertEqual(row.get_model().get_string(row.get_selected()), "%H:%M:%S %Z")
        self.assertNotIn("TimeFormat", self.settings())

    def test_macro_add_and_remove(self):
        macros = self.window.macros
        macros.key_row.set_text("k g")
        self.assertFalse(macros.add_button.get_sensitive())
        macros.key_row.set_text("kg")
        macros.value_row.set_text("khô gà")
        macros._add()
        self.assertEqual(self.store.macros, [("kg", "khô gà")])
        self.assertEqual(macros.key_row.get_text(), "")
        macros._remove("kg")
        self.assertEqual(self.store.macros, [])
        self.window.undo()
        self.assertEqual(self.store.macros, [("kg", "khô gà")])
        self.assertIsNotNone(macros.list.get_row_at_index(0))

    def test_dictionary_add_and_remove(self):
        page = self.window.dictionary
        page.word_row.set_text("ngo ãy")
        self.assertFalse(page.add_button.get_sensitive())
        page.word_row.set_text("việt")
        self.assertFalse(page.add_button.get_sensitive())
        page.word_row.set_text("ngoãy")
        page._add()
        self.assertEqual(self.store.words, ["việt", "nam", "ngoãy"])
        self.assertEqual(page.list.get_row_at_index(0).get_title(), "ngoãy")
        page._remove("ngoãy")
        self.assertFalse(os.path.exists(self.store.dictionary_file))
        self.window.undo()
        self.assertEqual(read_text(self.store.dictionary_file), "việt\nnam\nngoãy\n")

    def test_dictionary_list_follows_the_switch(self):
        page = self.window.dictionary
        self.assertTrue(page.editor.get_sensitive())
        self.window.rows.rows["EnableDictionary"].set_active(False)
        self.assertFalse(page.editor.get_sensitive())

    def tearDown(self):
        self.window.destroy()
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)


if __name__ == "__main__":
    unittest.main()
