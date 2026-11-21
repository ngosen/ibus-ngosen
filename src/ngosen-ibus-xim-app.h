/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <string>

namespace ngosen {

    // IBus names every XIM client "xim"; the core's rules for one app need the name fcitx5 gives it.
    void               noteXimFocus();
    const std::string& ximFocusedApp();
    void               setXimFocusedAppForTest(std::string program);

} // namespace ngosen
