# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import unittest

from ngosen_settings import ini, options
from ngosen_settings.store import Engine, Store, read_text, write_text


class FakeEngine:
    def __init__(self, values):
        self.values = values

    def settings(self):
        return dict(self.values)


class IniTest(unittest.TestCase):
    def test_round_trip(self):
        values = [
            "Telex",
            "%I:%M %p",
            'say "hi"',
            '"quoted"',
            "a\\b",
            "two\nlines",
            " padded ",
            "khô gà",
            "",
        ]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(ini.parse(f"Key={ini.escape(value)}\n")[0].get("Key"), value)

    def test_reads_values_as_fcitx5_does(self):
        self.assertEqual(ini.unescape("a\\n"), "a\\n")  # Unquoted values are literal.
        self.assertEqual(ini.unescape('"a\\tb"'), "a\tb")
        self.assertIsNone(ini.unescape('"a"b"'))
        self.assertIsNone(ini.unescape('"a\\xb"'))

    def test_parse(self):
        top, sections = ini.parse(
            '# c\n A = 1\nB="x y"\n[Macro/0]\nKey=kg\nValue="khô gà"\n[Macro/2]\nKey=z\n'
        )
        self.assertEqual(top, {"A ": " 1", "B": "x y"})
        self.assertEqual(ini.read_list(sections, "Macro"), [("kg", "khô gà")])

    def test_set_value_keeps_other_lines(self):
        text = "# note\nInputMethod=Telex\nUnknownKey=kept\n\n[Group]\nInputMethod=other\n"
        self.assertEqual(
            ini.set_value(text, "InputMethod", "VNI"),
            "# note\nInputMethod=VNI\nUnknownKey=kept\n\n[Group]\nInputMethod=other\n",
        )
        self.assertEqual(
            ini.set_value(text, "TimeFormat", "%I:%M %p"),
            '# note\nInputMethod=Telex\nUnknownKey=kept\n\nTimeFormat="%I:%M %p"\n[Group]\nInputMethod=other\n',
        )

    def test_macro_keys(self):
        self.assertTrue(options.valid_macro_key("kg"))
        self.assertTrue(options.valid_macro_key("đt2"))
        self.assertFalse(options.valid_macro_key("k g"))
        self.assertFalse(options.valid_macro_key("k.g"))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.settings = os.path.join(self.folder, "ngosen.conf")
        self.macros = os.path.join(self.folder, "ngosen-macro-table.conf")
        write_text(self.settings, "InputMethod=Telex\nFutureKey=kept\n")

    def store(self):
        return Store(FakeEngine({"InputMethod": "Telex"}), self.folder)

    def test_set_keeps_unknown_keys_and_undoes(self):
        store = self.store()
        self.assertFalse(store.set("InputMethod", "Telex"))
        self.assertFalse(store.can_undo())
        self.assertTrue(store.set("InputMethod", "VNI"))
        self.assertEqual(read_text(self.settings), "InputMethod=VNI\nFutureKey=kept\n")
        store.undo()
        self.assertEqual(read_text(self.settings), "InputMethod=Telex\nFutureKey=kept\n")
        self.assertEqual(store.values["InputMethod"], "Telex")

    def test_macros(self):
        write_text(self.macros, "[Other]\nA=1\n[Macro/0]\nKey=ko\nValue=không\n")
        store = self.store()
        self.assertEqual(store.macros, [("ko", "không")])
        store.set_macros([("ko", "không"), ("kg", "khô gà")])
        top, sections = ini.parse(read_text(self.macros))
        self.assertEqual(ini.read_list(sections, "Macro"), [("ko", "không"), ("kg", "khô gà")])
        self.assertEqual(sections["Other"], {"A": "1"})
        store.set_macros([("kg", "khô gà")])
        self.assertNotIn("Macro/1", ini.parse(read_text(self.macros))[1])
        store.undo()
        self.assertEqual(store.macros, [("ko", "không"), ("kg", "khô gà")])
        self.assertEqual(ini.read_list(ini.parse(read_text(self.macros))[1], "Macro"), store.macros)

    def test_undo_removes_a_file_it_created(self):
        store = self.store()
        store.set_macros([("ko", "không")])
        store.undo()
        self.assertFalse(os.path.exists(self.macros))


@unittest.skipUnless(os.environ.get("NGOSEN_IBUS_ENGINE"), "needs the built engine")
class EngineTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.home, "config")
        os.environ["XDG_DATA_HOME"] = os.path.join(self.home, "data")
        self.engine = Engine(os.environ["NGOSEN_IBUS_ENGINE"])

    def test_window_shows_every_setting_the_engine_reads(self):
        self.assertEqual(set(self.engine.settings()), set(options.LABELS))

    def test_engine_reads_what_the_window_writes(self):
        store = Store(self.engine)
        for key, value in [
            ("TimeFormat", "%I:%M %p"),
            ("InputMethod", "VNI"),
            ("W2U", "Everywhere"),
        ]:
            store.set(key, value)
        settings = self.engine.settings()
        self.assertEqual(settings["TimeFormat"], "%I:%M %p")
        self.assertEqual(settings["InputMethod"], "VNI")
        self.assertEqual(settings["W2U"], "Everywhere")

    def test_offered_names_are_accepted(self):
        store = Store(self.engine)
        for name in self.engine.input_methods():
            store.set("InputMethod", name)
            self.assertEqual(self.engine.settings()["InputMethod"], name)
        self.assertIn("Unicode", self.engine.charsets())


if __name__ == "__main__":
    unittest.main()
