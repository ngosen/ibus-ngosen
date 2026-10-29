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
    IBusPropList*         newSettingsMenu(const IBusSettings& settings);

    constexpr const char* SettingsWindowItem = "Settings";
    constexpr const char* SaveTypingLogItem  = "SaveTypingLog";

    // The ngosen.conf change a click on an item asks for. False when it changes nothing: a radio
    // item being unchecked, or a name the menu does not have.
    bool settingForClick(const std::string& name, bool checked, std::string& key, std::string& value);

} // namespace ngosen
