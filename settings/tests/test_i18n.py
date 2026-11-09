# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import unittest
from unittest import mock

from ngosen_settings import i18n


class I18nTest(unittest.TestCase):
    def languages(self, settings):
        with tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, "ngosen"))
            if settings is not None:
                with open(os.path.join(home, "ngosen", "ngosen.conf"), "w") as f:
                    f.write(settings)
            asked = []

            def translation(_domain, _localedir, languages, fallback):
                asked.append(languages)
                return i18n.gettext.NullTranslations()

            with (
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": home}),
                mock.patch.object(i18n.gettext, "translation", translation),
            ):
                i18n.setup("/nowhere")
            return asked

    def test_vietnamese_unless_english_is_picked(self):
        self.assertEqual(self.languages(None), [["vi"]])
        self.assertEqual(self.languages("UiLanguage=Vietnamese\n"), [["vi"]])
        self.assertEqual(self.languages("UiLanguage=English\n"), [])
        self.assertEqual(self.languages("UiLanguage=Klingon\n"), [["vi"]])


if __name__ == "__main__":
    unittest.main()
