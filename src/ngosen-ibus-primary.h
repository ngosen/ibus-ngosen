/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <string>

namespace ngosen {

    // The X11 primary selection as UTF-8, asked of whoever owns it. GNOME on Wayland hands what apps
    // select to Xwayland, so this also reads Firefox and LibreOffice there, which tell IBus nothing of
    // their selection. Empty without an X server or libxcb, when nobody owns it, or after timeoutMs.
    std::string readPrimarySelection(int timeoutMs);

} // namespace ngosen
