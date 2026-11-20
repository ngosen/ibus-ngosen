# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
import tempfile
import unittest

from ngosen_settings import emoji_words
from ngosen_settings.emoji_words import EmojiWords
from ngosen_settings.store import Store, read_text, write_text

from .test_store import FakeEngine

HERE = os.path.dirname(os.path.abspath(__file__))
CORE_TABLE = os.path.join(HERE, "..", "..", "ngosen", "settings-gui", "core", "emoji_table.py")
OWN_TABLE = os.path.join(HERE, "..", "ngosen_settings", "emoji_table.py")


class Folder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = self.temp.name

    def tearDown(self):
        self.temp.cleanup()

    def path(self, name):
        return os.path.join(self.folder, name)

    def store(self):
        return Store(FakeEngine({}, self.folder), self.folder)

    def words(self):
        return EmojiWords(self.store())

    def saved_words(self):
        return emoji_words.parse_edits(read_text(self.path("ngosen-emoji-words.conf")))


class TableTest(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(CORE_TABLE), "the ngosen submodule is not checked out")
    def test_the_table_is_the_cores(self):
        # The engine's default words come from the core, so the page must list the same ones.
        with open(CORE_TABLE, "rb") as core, open(OWN_TABLE, "rb") as own:
            self.assertEqual(
                own.read(), core.read(), "copy ngosen/settings-gui/core/emoji_table.py"
            )


class ChipsTest(Folder):
    def test_default_words_are_on_and_name_words_off(self):
        chips = dict(self.words().chips("😂"))
        self.assertTrue(chips["cười"])
        self.assertTrue(chips["haha"])
        self.assertFalse(chips["nước mắt"])

    def test_turning_a_default_word_off_saves_only_that(self):
        store = self.store()
        self.assertTrue(store.set_emoji_edits(EmojiWords(store).toggled("😂", "cười")))
        self.assertEqual(self.saved_words(), {("😂", "cười"): False})
        self.assertIn(
            "[Words/0]\nKeyword=cười\nEmoji=😂\nOn=False\n",
            read_text(self.path("ngosen-emoji-words.conf")),
        )
        self.assertFalse(dict(EmojiWords(store).chips("😂"))["cười"])

    def test_turning_it_back_on_removes_the_file(self):
        store = self.store()
        words = EmojiWords(store)
        store.set_emoji_edits(words.toggled("😂", "cười"))
        store.set_emoji_edits(words.toggled("😂", "cười"))
        self.assertFalse(words.changed("😂"))
        self.assertFalse(os.path.exists(self.path("ngosen-emoji-words.conf")))

    def test_a_word_of_its_name_turns_on(self):
        store = self.store()
        store.set_emoji_edits(EmojiWords(store).toggled("😂", "nước mắt"))
        self.assertEqual(self.saved_words(), {("😂", "nước mắt"): True})

    def test_an_added_word_is_kept_lower_case_and_stays_when_turned_off(self):
        store = self.store()
        words = EmojiWords(store)
        store.set_emoji_edits(words.added("👔", "  Sếp   lớn "))
        self.assertTrue(dict(words.chips("👔"))["sếp lớn"])
        store.set_emoji_edits(words.toggled("👔", "sếp lớn"))
        self.assertIn(("sếp lớn", False), words.chips("👔"))
        self.assertEqual(self.saved_words(), {("👔", "sếp lớn"): False})

    def test_an_empty_or_existing_word_is_not_added(self):
        words = self.words()
        self.assertIsNone(words.added("😂", "   "))
        self.assertIsNone(words.added("😂", "Cười"))

    def test_as_before_drops_every_change_to_an_emoji(self):
        store = self.store()
        words = EmojiWords(store)
        store.set_emoji_edits(words.toggled("😂", "cười"))
        store.set_emoji_edits(words.added("😂", "vui ghê"))
        store.set_emoji_edits(words.toggled("🤣", "cười"))
        store.set_emoji_edits(words.reset("😂"))
        self.assertFalse(words.changed("😂"))
        self.assertTrue(words.changed("🤣"))

    def test_the_fcitx5_file_is_read_back(self):
        write_text(
            self.path("ngosen-emoji-words.conf"),
            "[Words/0]\nKeyword=cười\nEmoji=😂\nOn=False\n\n[Words/1]\nKeyword=sếp\nEmoji=👔\nOn=True\n",
        )
        words = self.words()
        self.assertFalse(dict(words.chips("😂"))["cười"])
        self.assertTrue(dict(words.chips("👔"))["sếp"])

    def test_keywords_in_the_file_are_kept_as_written(self):
        # The engine compares keywords as written, so "Cười" never stands in for "cười".
        text = (
            "[Words/0]\nKeyword=cười\nEmoji=😂\nOn=False\n\n"
            "[Words/1]\nKeyword=Cười\nEmoji=😂\nOn=True\n\n"
        )
        edits = emoji_words.parse_edits(text)
        self.assertEqual(edits, {("😂", "cười"): False, ("😂", "Cười"): True})
        self.assertEqual(emoji_words.parse_edits(emoji_words.edits_text(edits)), edits)

    def test_spaces_around_a_quoted_keyword_are_kept(self):
        text = (
            "[Words/0]\nKeyword=cười\nEmoji=😂\nOn=False\n\n"
            '[Words/1]\nKeyword=" cười "\nEmoji=😂\nOn=True\n\n'
        )
        edits = emoji_words.parse_edits(text)
        self.assertEqual(edits, {("😂", "cười"): False, ("😂", " cười "): True})
        self.assertEqual(emoji_words.parse_edits(emoji_words.edits_text(edits)), edits)

    def test_a_word_on_twice_stays_on_whatever_the_order(self):
        # The engine offers the emoji for any entry that turns it on.
        for first, second in (("True", "False"), ("False", "True")):
            text = (
                f"[Words/0]\nKeyword=cười\nEmoji=😂\nOn={first}\n\n"
                f"[Words/1]\nKeyword=cười\nEmoji=😂\nOn={second}\n\n"
            )
            self.assertEqual(emoji_words.parse_edits(text), {("😂", "cười"): True})

    def test_undo_puts_the_words_back(self):
        store = self.store()
        store.set_emoji_edits(EmojiWords(store).toggled("😂", "cười"))
        store.undo()
        self.assertEqual(store.emoji_edits, {})
        self.assertFalse(os.path.exists(self.path("ngosen-emoji-words.conf")))


class FilterTest(Folder):
    def test_a_group_shows_its_emoji_only(self):
        shown = [e for e, *_ in self.words().rows(group="Food & Drink")]
        self.assertIn("🍜", shown)
        self.assertNotIn("😂", shown)

    def test_search_ignores_case_and_finds_the_emoji_itself(self):
        words = self.words()
        self.assertIn("💰", [e for e, *_ in words.rows(query="tiền")])
        self.assertIn("😂", [e for e, *_ in words.rows(query="CƯỜI")])
        self.assertEqual([e for e, *_ in words.rows(query="🐱")], ["🐱"])

    def test_only_emoji_with_a_word_on(self):
        store = self.store()
        # Almost every emoji has an English word on.
        store.set("EnglishEmojiKeywords", "False")
        words = EmojiWords(store)
        self.assertNotIn("📱", [e for e, *_ in words.rows(only_on=True)])
        store.set_emoji_edits(words.toggled("📱", "điện thoại"))
        self.assertIn("📱", [e for e, *_ in words.rows(only_on=True)])


class OffAppsTest(Folder):
    def apps_file(self, *apps):
        write_text(self.path("ngosen-emoji-off-apps.conf"), emoji_words.apps_text(apps))

    def saved_apps(self):
        return emoji_words.parse_apps(read_text(self.path("ngosen-emoji-off-apps.conf")))

    def test_turning_emoji_back_on_and_undo(self):
        self.apps_file("firefox", "kate")
        store = self.store()
        self.assertEqual(store.emoji_off_apps, ["firefox", "kate"])
        self.assertTrue(store.enable_emoji_in("firefox"))
        self.assertEqual(self.saved_apps(), ["kate"])
        store.undo()
        self.assertEqual(self.saved_apps(), ["firefox", "kate"])
        self.assertEqual(store.emoji_off_apps, ["firefox", "kate"])

    def test_turning_back_on_keeps_an_app_turned_off_since(self):
        self.apps_file("firefox")
        store = self.store()
        self.apps_file("firefox", "kate")
        store.enable_emoji_in("firefox")
        self.assertEqual(self.saved_apps(), ["kate"])
        self.assertEqual(store.emoji_off_apps, ["kate"])

    def test_undo_keeps_an_app_turned_off_since(self):
        self.apps_file("firefox")
        store = self.store()
        store.enable_emoji_in("firefox")
        self.apps_file("kate")
        store.undo()
        self.assertEqual(self.saved_apps(), ["firefox", "kate"])

    def test_turning_back_on_drops_every_name_of_the_app(self):
        # fcitx5 may have saved the names the engine shortens to "firefox".
        self.apps_file("firefox.desktop", "firefox_firefox", "kate")
        store = self.store()
        self.assertEqual(store.emoji_off_apps, ["firefox", "kate"])
        self.assertTrue(store.enable_emoji_in("firefox"))
        self.assertEqual(self.saved_apps(), ["kate"])

    def test_undo_after_the_engine_saved_the_app_again_adds_no_second_name(self):
        self.apps_file("firefox.desktop")
        store = self.store()
        store.enable_emoji_in("firefox")
        self.apps_file("firefox")
        store.undo()
        self.assertEqual(self.saved_apps(), ["firefox"])

    def test_the_file_keeps_the_engines_header(self):
        self.apps_file("firefox", "kate")
        self.store().enable_emoji_in("kate")
        self.assertEqual(
            read_text(self.path("ngosen-emoji-off-apps.conf")),
            "# Apps where Ngó Sen offers no emoji, one per line\nfirefox\n",
        )


class ShareTest(Folder):
    def test_export_then_import_adds_the_words_turned_on(self):
        edits = {("😂", "sếp cười"): True, ("😂", "cười"): False}
        path = self.path("shared.json")
        self.assertEqual(emoji_words.export_words(edits, path), 1)
        self.assertEqual(emoji_words.read_shared(path), [("😂", "sếp cười")])
        words = EmojiWords(self.store())
        merged, added = words.merged(emoji_words.read_shared(path))
        self.assertEqual((merged, added), ({("😂", "sếp cười"): True}, 1))

    def test_import_keeps_a_word_turned_off(self):
        store = self.store()
        store.emoji_edits = {("😂", "cười"): False}
        merged, added = EmojiWords(store).merged([("😂", "cười"), ("😂", "haha")])
        self.assertEqual((merged, added), ({("😂", "cười"): False}, 0))

    def test_unknown_emoji_and_long_words_are_skipped(self):
        path = self.path("shared.json")
        items = [
            {"Emoji": "not an emoji", "Keyword": "x"},
            {"Emoji": [], "Keyword": "x"},
            {"Emoji": "😂", "Keyword": "a" * 41},
            {"Emoji": "😂", "Keyword": " Sếp  Cười "},
        ]
        write_text(
            path, json.dumps({"meta": {"kind": emoji_words.SHARE_KIND}, "emoji_words": items})
        )
        self.assertEqual(emoji_words.read_shared(path), [("😂", "sếp cười")])

    def test_a_backup_or_a_damaged_file_is_refused(self):
        path = self.path("shared.json")
        for data in (
            {"config": {}},
            {"meta": {"kind": emoji_words.SHARE_KIND}, "emoji_words": [1]},
            {"meta": {"kind": emoji_words.SHARE_KIND}, "emoji_words": {}},
        ):
            with self.subTest(data=data):
                write_text(path, json.dumps(data))
                with self.assertRaises(ValueError):
                    emoji_words.read_shared(path)
