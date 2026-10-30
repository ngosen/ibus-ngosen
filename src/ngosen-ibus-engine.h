/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <atomic>
#include <ibus.h>
#include <thread>

namespace ngosen {

    // Registers the "ngosen" engine with the factory.
    void addEngine(IBusFactory* factory);

    // Watches mouse clicks on an X11 session until stop is set; an empty thread elsewhere.
    std::thread watchClicks(const std::atomic<bool>& stop);

} // namespace ngosen
