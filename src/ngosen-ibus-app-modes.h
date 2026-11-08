/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include "ngosen-ibus-config.h"

#include <filesystem>
#include <map>
#include <optional>
#include <string>

namespace ngosen {

    // The typing mode picked for one app in the mode menu. English stays shared by every app, as the
    // toggle key switches it everywhere at once.
    enum class AppMode {
        Sen,
        Preedit
    };

    using AppModeMap = std::map<std::string, AppMode>;

    // The name a mode is remembered by, from the program a field reports. Empty when the name stands for
    // no single app: GNOME Shell before the portal names the app, Qt and XIM clients of any app.
    std::string modeAppName(const std::string& program);

    // The fcitx5 edition's ngosen-app-rules.conf format: "app=number", 2 for Sen and 5 for Preedit. The
    // other numbers fcitx5 writes (Off, Emoji) have no per-app meaning here and are skipped.
    AppModeMap  parseAppModes(const std::string& text);
    std::string appModesText(const AppModeMap& modes);

    class AppModes {
      public:
        explicit AppModes(std::string path, FileWriter write = writeFileAtomically);

        std::optional<AppMode> find(const std::string& app);
        // nullopt forgets the app, so it follows the shared mode again. False when the file was not written.
        bool set(const std::string& app, std::optional<AppMode> mode);

      private:
        // Rereads the file when it changed, so an edit by hand applies without a restart.
        void        reloadIfChanged();

        std::string path_;
        FileWriter  write_;
        AppModeMap  modes_;
        // Unset until the file was read; a missing file reads as no modes.
        std::optional<std::filesystem::file_time_type> mtime_;
        bool                                           loaded_ = false;
    };

} // namespace ngosen
