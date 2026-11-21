/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <optional>
#include <string>

namespace ngosen {

    // The X11 primary selection as UTF-8, asked of whoever owns it. GNOME on Wayland hands what apps
    // select to Xwayland, so this also reads Firefox and LibreOffice there, which tell IBus nothing of
    // their selection. Empty without an X server or libxcb, when nobody owns it, or after timeoutMs.
    std::string readPrimarySelection(int timeoutMs);

    // The primary selection through the Wayland data-control protocol, which KDE, Sway and Hyprland offer
    // and GNOME does not. nullopt when it cannot be read this way, so the caller asks X11 instead.
    std::optional<std::string> readWaylandPrimarySelection(int timeoutMs);

} // namespace ngosen
