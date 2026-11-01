/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include "ngosen-ibus-config.h"

#include <ibus.h>
#include <string>

namespace ngosen {

    // The items of the fcitx5 edition's tray menu, shown in the GNOME input source menu.
    IBusPropList*         newSettingsMenu(const IBusSettings& settings, bool english = false);

    constexpr const char* SettingsWindowItem = "Settings";
    constexpr const char* SaveTypingLogItem  = "SaveTypingLog";
    // GNOME Shell shows the symbol of the item with this key in the top bar, whatever its type.
    constexpr const char* InputModeItem = "InputMode";

    // The ngosen.conf change a click on an item asks for; an on/off item flips its value in
    // settings. False when it changes nothing: a radio item being unchecked, or a name the menu
    // does not have.
    bool settingForClick(const std::string& name, bool checked, const IBusSettings& settings, std::string& key, std::string& value);

} // namespace ngosen
