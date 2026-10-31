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

    // The modes the menu offers. Every app shares one: IBus on Wayland does not tell apps apart.
    enum class MenuMode {
        Sen,
        Preedit,
        English
    };

    struct MenuItem {
        MenuMode    mode;
        std::string label;
        guint       key = 0;
    };

    std::vector<MenuItem> modeMenuItems(const IBusSettings& settings);

    // keymap is the custom keymap in use, if any.
    bool opensModeMenu(const IBusSettings& settings, const std::vector<KeymapEntry>& keymap, guint keyval, guint state);

    // What a key pressed while the menu is open does.
    struct MenuKey {
        enum Kind {
            Swallow,
            Close,
            Up,
            Down,
            PickCursor,
            Pick,
            TypeMenuKey
        } kind        = Swallow;
        MenuMode mode = MenuMode::Sen;
    };

    MenuKey          menuKey(const IBusSettings& settings, guint keyval, guint state);

    IBusLookupTable* newModeMenuTable(const std::vector<MenuItem>& items, guint cursor);

} // namespace ngosen
