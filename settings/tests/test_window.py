# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import unittest

from ngosen_settings import ini, keymap
from ngosen_settings.store import Store, read_text, write_text

try:
    from ngosen_settings import window  # Picks the GTK and libadwaita versions first.

    Adw, GLib = window.Adw, window.GLib
except (ImportError, ValueError):
    window = None


class Vietnamese:
    """Labels that differ from the saved values, as they do in the real window."""

    def gettext(self, text):
        # A real catalog answers the empty string with its header.
        if not text:
            return "Project-Id-Version: ibus-ngosen"
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


def labels(widget):
    child = widget.get_first_child()
    while child is not None:
        if isinstance(child, window.Gtk.Label):
            yield child
        yield from labels(child)
        child = child.get_next_sibling()


class FakeSources:
    """GNOME input sources kept in memory, so no test changes the desktop it runs on."""

    def __init__(self, sources=None):
        self.sources = sources

    def get(self):
        return self.sources

    def set(self, sources):
        self.sources = list(sources)
        return True

    def gnome_keys(self):
        return ["<Super>space", "<Shift><Super>space", "<Super>a"], [
            "grp:ctrl_alt_toggle_bidir",
            "grp:alt_caps_toggle",
        ]


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
        self.window = window.Window(None, self.store, names, "1.0.0", FakeSources())

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

    def test_keymap_add_edit_remove(self):
        page = self.window.keymap
        for bad in ("ss", " "):
            page.key_row.set_text(bad)
            self.assertFalse(page.add_button.get_sensitive(), bad)
            self.assertTrue(page.key_row.has_css_class("error"), bad)
        page.key_row.set_text("s")
        page.action.set_selected(keymap.ACTION_CODES.index("DauSac"))
        page._add()
        self.assertEqual(self.store.keymap, [("s", "DauSac")])
        self.assertEqual(page.key_row.get_text(), "")
        self.assertEqual(page.list.get_row_at_index(0).get_subtitle(), "Sắc tone")
        page.list.get_row_at_index(0).activate()
        self.assertEqual(page.key_row.get_text(), "s")
        page.action.set_selected(keymap.ACTION_CODES.index("DauHoi"))
        page._add()
        self.assertEqual(self.store.keymap, [("s", "DauHoi")])
        page._remove("s")
        self.assertEqual(self.store.keymap, [])
        self.window.undo()
        self.assertEqual(self.store.keymap, [("s", "DauHoi")])
        self.assertEqual(page.list.get_row_at_index(0).get_title(), "s")

    def test_keymap_duplicate_key_updates(self):
        page = self.window.keymap
        page.key_row.set_text("s")
        page._add()
        page.key_row.set_text("s")
        self.assertEqual(page.add_button.get_label(), "Update")
        self.assertIn("Update replaces it", page.editor.get_description())
        page.action.set_selected(keymap.ACTION_CODES.index("DauNga"))
        page._add()
        self.assertEqual(self.store.keymap, [("s", "DauNga")])
        self.assertFalse(page.editor.get_description())

    def test_keymap_preset_and_switch(self):
        page = self.window.keymap
        page.preset.set_selected(1)
        page.apply_preset()
        self.assertEqual(self.store.keymap, keymap.PRESETS[1][1])
        self.window.undo()
        self.assertEqual(self.store.keymap, [])
        self.window.rows.rows["EnableCustomKeymap"].set_active(True)
        self.assertEqual(self.settings()["EnableCustomKeymap"], "True")

    def test_keymap_hint_escapes_markup(self):
        page = self.window.keymap
        self.store.set_keymap([("&", "XoaDauThanh")])
        page.refresh()
        page.key_row.set_text("&")
        # What the label shows: libadwaita 1.5 returns the parsed text from
        # get_description(), and a label whose markup fails to parse keeps its old text.
        shown = [label.get_text() for label in labels(page.editor)]
        self.assertIn("& already does “Remove the tone mark”; Update replaces it.", shown)

    def test_keymap_unknown_action_is_not_overwritten(self):
        page = self.window.keymap
        self.store.set_keymap([("q", "FutureAction")])
        page.refresh()
        page.action.set_selected(keymap.ACTION_CODES.index("DauSac"))
        page.list.get_row_at_index(0).activate()
        self.assertEqual(page.key_row.get_text(), "q")
        shown = page.action.get_model().get_string(page.action.get_selected())
        self.assertEqual(shown, "FutureAction")
        self.assertFalse(page.add_button.get_sensitive())
        page._add()
        self.assertEqual(self.store.keymap, [("q", "FutureAction")])
        page.action.set_selected(keymap.ACTION_CODES.index("DauNga"))
        self.assertTrue(page.add_button.get_sensitive())
        page._add()
        self.assertEqual(self.store.keymap, [("q", "DauNga")])
        self.assertEqual(page.action.get_model().get_n_items(), len(keymap.ACTION_CODES))

    def test_keymap_same_preset_twice_keeps_undo(self):
        page = self.window.keymap
        page.preset.set_selected(1)
        page.apply_preset()
        toast = self.window.toast
        page.apply_preset()
        self.assertIs(self.window.toast, toast)
        self.window.undo()
        self.assertEqual(self.store.keymap, [])

    def test_switch_dialog_copies_the_command(self):
        dialog = window.pages.show_switch_dialog(self.window, self.window._show)
        dialog.emit("response", "close")
        self.assertIsNone(self.window.toast)
        dialog = window.pages.show_switch_dialog(self.window, self.window._show)
        dialog.emit("response", "copy")
        self.assertEqual(self.window.toast.get_title(), "Command copied.")

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

    def capture(self, *names):
        """Picks Other keys, then holds the keys named and lets them go."""
        row = self.window.rows.rows["ToggleKey"]
        row.set_selected(row.get_model().get_n_items() - 1)
        capture = self.window.rows.capture
        for code, name in enumerate(names):
            capture.press(name, code)
        for code in range(len(names)):
            capture.release(code)
        return capture

    def test_toggle_key_from_pressed_keys(self):
        capture = self.capture("Control_L", "grave")
        self.assertEqual(capture.shown.get_label(), "Ctrl+`")
        capture.dialog.emit("response", "save")
        self.assertEqual(self.settings()["ToggleKey"], "Control+grave")
        row = self.window.rows.rows["ToggleKey"]
        self.assertEqual(row.get_model().get_string(row.get_selected()), "Ctrl+`")

    def test_toggle_key_same_as_a_suggestion(self):
        self.capture("Shift_L", "Meta_L").dialog.emit("response", "save")
        self.assertEqual(self.settings()["ToggleKey"], window.options.TOGGLE_KEYS[1][0])

    def test_toggle_key_refused(self):
        row = self.window.rows.rows["ToggleKey"]
        before = row.get_selected()
        for names in (
            ["Control_L"],
            ["Shift_L", "a"],
            ["Super_L", "space"],
            ["Alt_L", "Caps_Lock"],
        ):
            capture = self.capture(*names)
            self.assertFalse(capture.dialog.get_response_enabled("save"), names)
            capture.dialog.emit("response", "cancel")
        self.assertNotIn("ToggleKey", self.settings())
        self.assertEqual(row.get_selected(), before)

    def test_toggle_key_note_empty_without_problem(self):
        self.assertEqual(self.capture("Control_L", "Shift_L").note.get_label(), "")

    def test_toggle_key_lost_release(self):
        row = self.window.rows.rows["ToggleKey"]
        row.set_selected(row.get_model().get_n_items() - 1)
        capture = self.window.rows.capture
        capture.press("Alt_L", 9)
        # Alt+Tab to another window: the release of Alt goes there.
        window.Gtk.Widget.notify(self.window, "is-active")
        capture.press("Control_L", 1)
        capture.press("Shift_L", 2)
        capture.release(1)
        capture.release(2)
        self.assertEqual(capture.shown.get_label(), "Ctrl+Shift")

    def test_toggle_key_gnome_shortcuts_refused(self):
        for names in (["Super_L", "a"], ["Control_L", "Alt_L"]):
            capture = self.capture(*names)
            self.assertFalse(capture.dialog.get_response_enabled("save"), names)
            capture.dialog.emit("response", "cancel")

    def test_toggle_key_navigation_keys_pass(self):
        capture = self.capture()
        self.assertFalse(capture.press("Tab", 1))
        capture.release(1)
        self.assertEqual(capture.shown.get_label(), "")
        self.assertTrue(capture.press("Control_L", 2))
        self.assertTrue(capture.press("Tab", 1))

    def test_toggle_key_shifted_repeat(self):
        row = self.window.rows.rows["ToggleKey"]
        row.set_selected(row.get_model().get_n_items() - 1)
        capture = self.window.rows.capture
        capture.press("Control_L", 0)
        capture.press("Shift_L", 1)
        capture.press("exclam", 2)
        for code in range(3):
            capture.release(code)
        self.assertEqual(capture.shown.get_label(), "Ctrl+Shift+!")
        capture.dialog.emit("response", "save")
        self.assertEqual(self.settings()["ToggleKey"], "Control+Shift+exclam")

    def test_toggle_key_modifiers_first(self):
        # The engine gets the key as the modifiers held at its press make it.
        capture = self.capture("Control_L", "1", "Shift_L")
        self.assertFalse(capture.dialog.get_response_enabled("save"))
        self.assertEqual(capture.note.get_label(), window.keys.MODIFIERS_FIRST)

    def test_toggle_key_forget_ends_navigation(self):
        capture = self.capture()
        capture.press("Shift_L", 0)
        capture.press("ISO_Left_Tab", 1)
        window.Gtk.Widget.notify(self.window, "is-active")
        capture.press("Control_L", 2)
        capture.press("Shift_L", 3)
        capture.release(2)
        capture.release(3)
        self.assertEqual(capture.shown.get_label(), "Ctrl+Shift")

    def test_toggle_key_shift_tab_navigates(self):
        capture = self.capture()
        capture.press("Shift_L", 0)
        self.assertFalse(capture.press("ISO_Left_Tab", 1))
        capture.release(1)
        capture.press("Control_L", 2)
        capture.release(2)
        capture.release(0)
        self.assertEqual(capture.note.get_label(), "")
        self.assertFalse(capture.dialog.get_response_enabled("save"))

    def test_toggle_key_unnamed_key(self):
        capture = self.capture()
        capture.press(None, 3)
        capture.press("Tab", 1)
        capture.release(1)
        capture.release(3)
        capture.press("Control_L", 4)
        capture.press("Shift_L", 5)
        capture.release(4)
        capture.release(5)
        self.assertEqual(capture.shown.get_label(), "Ctrl+Shift")

    def test_custom_binding_without_schema(self):
        # GSettings aborts the app on a missing schema or a bad path.
        self.assertEqual(window.check_page.custom_binding("not/a/path"), "")

    def test_toggle_key_stray_release(self):
        capture = self.capture()
        capture.release(5)
        self.assertEqual(capture.note.get_label(), "")
        self.assertFalse(capture.dialog.get_response_enabled("save"))

    def test_toggle_key_alt_letter_warns(self):
        capture = self.capture("Alt_L", "z")
        self.assertTrue(capture.dialog.get_response_enabled("save"))
        self.assertIn("menu bar", capture.note.get_label())

    def test_check_page_counts_the_steps_left(self):
        check = self.window.check
        self.assertEqual(self.window.check_tab.get_badge_number(), len(check.findings))
        self.assertEqual(len(check.rows), len(check.found))
        self.assertIn("Ngó Sen", check.report_text())

    def tearDown(self):
        self.window.destroy()
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)


if __name__ == "__main__":
    unittest.main()
