/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include "ngosen-ibus-config.h"

#include <functional>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace ngosen {

    // A GNOME input source: ("xkb", "us") or ("ibus", "ngosen").
    using InputSource = std::pair<std::string, std::string>;

    struct InputSourceStore {
        // Empty where GNOME's settings are not installed.
        std::function<std::optional<std::vector<InputSource>>()> get;
        std::function<bool(const std::vector<InputSource>&)>     set;
    };

    // The US layout next to Ngó Sen only switches to the same keys, which the toggle key already does.
    std::vector<InputSource> withoutDuplicateLayout(const std::vector<InputSource>& sources);

    // Removes that source the first time the engine runs as a GNOME input source with a toggle key, and
    // never again, so a user who adds it back keeps it. Returns false when a write failed.
    bool             dropDuplicateLayoutOnce(const SettingsPaths& paths, bool hasToggleKey, const InputSourceStore& store, const FileWriter& write = writeFileAtomically);

    InputSourceStore gnomeInputSources();

} // namespace ngosen
