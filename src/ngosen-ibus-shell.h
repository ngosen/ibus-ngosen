/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <string>

namespace ngosen {

    // Starts following GNOME Shell on the session bus, once. Enables the forward-keys extension at
    // most once for this user, where it is needed: enabledMark records that, so an extension the user
    // turns off stays off.
    void watchShell(const std::string& enabledMark);

    // Whether keys an engine forwards reach apps through GNOME Shell. False until the Shell has
    // answered, so a field types with the preedit rather than lose a deletion.
    bool shellDeliversKeys();

} // namespace ngosen
