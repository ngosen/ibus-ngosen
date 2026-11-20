/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include "ngosen-engine-resources.h"
#include "ngosen-ibus-config.h"

#include <glib.h>
#include <string>
#include <vector>

typedef struct _IBusLookupTable IBusLookupTable;

namespace ngosen {

    // The modes the menu offers, kept for the app in use. Vim and Emoji are no modes but switch Vim mode
    // and emoji suggestions for the app, as in fcitx5.
    enum class MenuMode {
        Sen,
        Preedit,
        Off,
        Vim,
        Emoji
    };

    struct MenuItem {
        MenuMode    mode;
        std::string label;
        guint       key = 0;
        // The mode the app types in now, which the menu marks; the cursor may move away from it.
        bool current = false;
    };

    // The shown modes in ModeOrder, then the ones it leaves out; a key an earlier item has picks nothing.
    // vimOn, emojiOn: whether the app in use has Vim mode and emoji suggestions, which their items say.
    std::vector<MenuItem> modeMenuItems(const IBusSettings& settings, bool vimOn = false, bool emojiOn = true);

    // As in fcitx5 the cycle key goes through only the modes ModeOrder names, the switches left out.
    std::vector<MenuMode> cycleMenuModes(const IBusSettings& settings);

    bool                  cyclesMode(const IBusSettings& settings, guint keyval, guint state);
    bool                  convertsSelection(const IBusSettings& settings, guint keyval, guint state);

    // keymap is the custom keymap in use, if any.
    bool opensModeMenu(const IBusSettings& settings, const std::vector<KeymapEntry>& keymap, guint keyval, guint state);

    // What a key pressed while the menu is open does.
    struct MenuKey {
        enum Kind {
            // Closes the menu and lets the key type as if the menu was never opened.
            Pass,
            Close,
            Up,
            Down,
            PickCursor,
            Pick,
            TypeMenuKey
        } kind        = Pass;
        MenuMode mode = MenuMode::Sen;
    };

    MenuKey          menuKey(const IBusSettings& settings, guint keyval, guint state);

    IBusLookupTable* newModeMenuTable(const std::vector<MenuItem>& items, guint cursor);

} // namespace ngosen
