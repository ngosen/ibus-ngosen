/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <functional>
#include <string>

namespace ngosen {

    // Opens the settings window on its What's new page.
    void openWhatsNew();

    // Tells an updated user what the release brought, with a button that runs open. Does nothing for
    // an empty release. The engine starts with the session, and a notice sent before the desktop is
    // up is lost, so it waits a few seconds.
    void announceRelease(const std::string& release, unsigned delaySeconds = 5, std::function<void()> open = openWhatsNew);

} // namespace ngosen
