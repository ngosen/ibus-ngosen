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
#include <set>
#include <string>
#include <unordered_set>

namespace ngosen {

    // The typing mode picked for one app in the mode menu; Off types English until the toggle key
    // switches the app back.
    enum class AppMode {
        Sen,
        Preedit,
        Off
    };

    using AppModeMap = std::map<std::string, AppMode>;

    // The name a mode is remembered by, from the program a field reports. Empty when the name stands for
    // no single app: GNOME Shell before the portal names the app, ibus-ui-gtk3 as the Wayland input method
    // of Plasma, Qt and XIM clients of any app.
    std::string modeAppName(const std::string& program);

    // The fcitx5 edition's ngosen-app-rules.conf format: "app=number", 0 for Off, 2 for Sen and 5 for
    // Preedit. Emoji (6) has no meaning here and is skipped.
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

    // Whether the toggle key last left each app in Vietnamese (true) or English.
    using AppSwitchMap = std::map<std::string, bool>;

    // The fcitx5 edition's ngosen-app-switch.conf, an fcitx5 list: "[Switches/0]", "App=", "Vietnamese=".
    AppSwitchMap parseAppSwitches(const std::string& text);
    std::string  appSwitchesText(const AppSwitchMap& switches);

    class AppSwitches {
      public:
        explicit AppSwitches(std::string path, FileWriter write = writeFileAtomically);

        std::optional<bool> find(const std::string& app);
        // nullopt forgets the app, so it follows its mode or the last switch again.
        bool set(const std::string& app, std::optional<bool> vietnamese);

      private:
        void                                           reloadIfChanged();

        std::string                                    path_;
        FileWriter                                     write_;
        AppSwitchMap                                   switches_;
        std::optional<std::filesystem::file_time_type> mtime_;
        bool                                           loaded_ = false;
    };

    // The fcitx5 edition's app lists, such as ngosen-vim-apps.conf: one app per line, # for comments.
    using AppNameSet = std::set<std::string>;
    // The first lines fcitx5 writes, so the files look the same from either edition.
    constexpr const char* VimAppsHeader      = "# Apps where Ngó Sen follows Vim's normal-mode keys, one per line";
    constexpr const char* EmojiAppsHeader    = "# Apps where Ngó Sen offers emoji, one per line";
    constexpr const char* TeencodeAppsHeader = "# Apps where Ngó Sen keeps teencode, one per line";
    AppNameSet            parseAppList(const std::string& text);
    std::string           appListText(const std::string& header, const AppNameSet& apps);

    // Apps where the core found an xterm.js terminal. Names stay as the field reported them, since the
    // core matches them exactly; GNOME Shell's "window:N" names last one session and are not written.
    constexpr const char*           WebTerminalAppsHeader = "# Apps where Ngó Sen found an xterm.js terminal, one per line";
    std::unordered_set<std::string> readWebTerminalApps(const std::string& path);
    bool                            writeWebTerminalApps(const std::string& path, const std::unordered_set<std::string>& apps, const FileWriter& write = writeFileAtomically);

    // Apps picked in the mode menu for a switch kept per app, such as Vim mode.
    class AppList {
      public:
        // header: the comment line the file starts with.
        AppList(std::string path, std::string header, FileWriter write = writeFileAtomically);

        bool has(const std::string& app);
        // False when the file was not written.
        bool set(const std::string& app, bool on);

      private:
        void                                           reloadIfChanged();

        std::string                                    path_;
        std::string                                    header_;
        FileWriter                                     write_;
        AppNameSet                                     apps_;
        std::optional<std::filesystem::file_time_type> mtime_;
        bool                                           loaded_ = false;
    };

} // namespace ngosen
