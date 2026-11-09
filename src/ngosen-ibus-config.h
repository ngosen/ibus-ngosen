/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include "ngosen-engine-resources.h"
#include "ngosen-options.h"

#include <functional>
#include <map>
#include <string>
#include <vector>

namespace ngosen {

    // fcitx5's ini format and key names, so importing the fcitx5 edition's files is a copy.
    struct IniFile {
        std::map<std::string, std::string>                        top;
        std::map<std::string, std::map<std::string, std::string>> sections;
    };

    IniFile parseIni(const std::string& text);
    // The spaces fcitx5 strips around a line.
    std::string              trimIni(const std::string& text);
    std::string              escapeIniValue(const std::string& value);

    std::vector<KeymapEntry> iniList(const IniFile& ini, const std::string& name);
    // The values of [name], keyed 0, 1, …, as fcitx5 stores a key list.
    std::vector<std::string> iniKeyList(const IniFile& ini, const std::string& name);

    // The names the Vietnamese engine knows, for the settings window to offer.
    const std::vector<std::string>& inputMethodNames();
    const std::vector<std::string>& charsetNames();

    struct IBusSettings {
        Options options;
        bool    enableDictionary   = false;
        bool    enableCustomKeymap = false;
        // Straight into fields that can delete around the cursor, underlined elsewhere.
        bool directTyping = true;
        // Switches between English and Vietnamese; empty when the user turned the key off.
        std::vector<std::string> toggleKeys;
        // Opens the menu of typing modes; empty when the user turned it off.
        std::vector<std::string> modeMenuKeys;
        // The keys that pick each mode in that menu: one letter or digit.
        std::string shortcutSen     = "1";
        std::string shortcutPreedit = "q";
        std::string shortcutOff     = "e";
        std::string shortcutDefault = "r";
        // Which modes the menu shows, and in what order; fcitx5's names, Emoji included.
        bool        showModeSen     = true;
        bool        showModePreedit = true;
        bool        showModeOff     = true;
        bool        showModeDefault = true;
        std::string modeOrder       = "Sen,Preedit,Emoji,Off,Default";
        // Which items the top bar menu shows, as fcitx5 hides items of its tray menu.
        bool showMenuInputMethod     = true;
        bool showMenuCharset         = true;
        bool showMenuSpellCheck      = true;
        bool showMenuMacro           = true;
        bool showMenuCapitalizeMacro = true;
        bool showMenuAutoCapitalize  = true;
        bool showMenuAutoRestore     = true;
        bool showMenuDictionary      = true;
        // Menus and notices in English when "English"; Vietnamese otherwise, as in fcitx5.
        std::string uiLanguage = "Vietnamese";
        // Moves the app to the next mode in that order; off by default, as in fcitx5.
        std::vector<std::string> cycleModeKeys;
    };

    // The fcitx5 edition's defaults, without the features that delete text the app already has.
    IBusSettings defaultSettings();
    // Reads only the keys the IBus edition uses; a missing or unknown value keeps the default.
    IBusSettings readSettings(const IniFile& ini);
    // Writes every key readSettings() reads, so the settings window finds them all in the file.
    std::string settingsText(const IBusSettings& settings);
    // Sets one key and keeps the rest of the file as the user or the settings window wrote it.
    std::string withSetting(const std::string& text, const std::string& key, const std::string& value);

    struct SettingsPaths {
        std::string          configDir;      // ~/.config/ngosen
        std::string          dataDir;        // ~/.local/share/ngosen
        std::string          fcitxConfigDir; // ~/.config/fcitx5/conf
        std::string          fcitxDataDir;   // ~/.local/share/fcitx5/ngosen
        std::string          stateDir;       // ~/.local/state/ngosen

        static SettingsPaths fromEnvironment();
        std::string          settingsFile() const;
        std::string          macroFile() const;
        std::string          keymapFile() const;
        std::string          dictionaryFile() const;
        std::string          appModesFile() const;
        std::string          appSwitchesFile() const;
        // Marks the import as done, so deleting ngosen.conf brings back the defaults.
        std::string importedMark() const;
        // Marks Sen as switched on once, so turning it off afterwards sticks.
        std::string senDefaultMark() const;
        // There while typing English. Not a setting: deleting ngosen.conf does not switch back.
        std::string englishMark() const;
        // Marks the forward-keys extension as enabled once, so turning it off is not undone.
        std::string extensionEnabledMark() const;
    };

    bool readFile(const std::string& path, std::string& content);
    // Through a temporary file in the same directory, so a reader never sees half a file.
    bool writeFileAtomically(const std::string& path, const std::string& content);

    using FileWriter = std::function<bool(const std::string& path, const std::string& content)>;

    bool readEnglishOn(const SettingsPaths& paths);
    bool saveEnglishOn(const SettingsPaths& paths, bool on);

    // On the first run, copies the fcitx5 edition's settings, or writes the defaults when it has none.
    // Never overwrites a file. The import is marked done last, so a run stopped halfway is finished
    // by the next one. Returns false when a write failed.
    bool prepareSettings(const SettingsPaths& paths, const FileWriter& write = writeFileAtomically);

} // namespace ngosen
