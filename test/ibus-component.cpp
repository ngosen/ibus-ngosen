/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-menu.h"

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

int main() {
    std::ifstream      file(NGOSEN_COMPONENT_XML_IN);
    std::ostringstream text;
    text << file.rdbuf();
    // ibus-ui-gtk3, the tray icon outside GNOME, shows V or E only from the item named here.
    const std::string want = std::string("<icon_prop_key>") + ngosen::InputModeItem + "</icon_prop_key>";
    if (!file || text.str().find(want) == std::string::npos) {
        std::cout << "FAIL " << NGOSEN_COMPONENT_XML_IN << " lacks " << want << "\n";
        return 1;
    }
    return 0;
}
