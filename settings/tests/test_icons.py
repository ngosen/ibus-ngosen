# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import re
import unittest

# Adwaita drops icons between releases and a missing one shows as a broken image, so only names that every
# supported system's Adwaita has.
ADWAITA_EVERYWHERE = {
    "accessories-dictionary-symbolic",
    "dialog-error-symbolic",
    "dialog-information-symbolic",
    "dialog-warning-symbolic",
    "face-smile-symbolic",
    "document-edit-symbolic",
    "edit-find-replace-symbolic",
    "go-next-symbolic",
    "input-keyboard-symbolic",
    "object-select-symbolic",
    "open-menu-symbolic",
    "preferences-desktop-keyboard-symbolic",
    "preferences-system-symbolic",
    "user-trash-symbolic",
}

# Shipped inside libadwaita, not the icon theme.
LIBADWAITA = {"adw-external-link-symbolic"}

SOURCES = os.path.join(os.path.dirname(__file__), "..", "ngosen_settings")


class IconTest(unittest.TestCase):
    def test_every_symbolic_icon_exists_on_supported_systems(self):
        used = set()
        for name in os.listdir(SOURCES):
            if name.endswith(".py"):
                with open(os.path.join(SOURCES, name), encoding="utf-8") as f:
                    used |= set(re.findall(r"""["']([a-z0-9-]+-symbolic)["']""", f.read()))
        self.assertTrue(used)
        self.assertEqual(sorted(used - ADWAITA_EVERYWHERE - LIBADWAITA), [])


if __name__ == "__main__":
    unittest.main()
