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

    IniFile                  parseIni(const std::string& text);
    std::string              escapeIniValue(const std::string& value);

    std::vector<KeymapEntry> iniList(const IniFile& ini, const std::string& name);

    // The names the Vietnamese engine knows, for the settings window to offer.
    const std::vector<std::string>& inputMethodNames();
    const std::vector<std::string>& charsetNames();

    struct IBusSettings {
        Options options;
        bool    enableDictionary   = false;
        bool    enableCustomKeymap = false;
        // Straight into fields that can delete around the cursor, underlined elsewhere.
        bool directTyping = false;
        // Held in the preedit and changed there, so the core's own versions, which delete, stay off.
        bool doubleSpaceToPeriod  = false;
        bool doubleHyphenToEmDash = false;
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

        static SettingsPaths fromEnvironment();
        std::string          settingsFile() const;
        std::string          macroFile() const;
        std::string          keymapFile() const;
        std::string          dictionaryFile() const;
        // Marks the import as done, so deleting ngosen.conf brings back the defaults.
        std::string importedMark() const;
    };

    bool readFile(const std::string& path, std::string& content);
    // Through a temporary file in the same directory, so a reader never sees half a file.
    bool writeFileAtomically(const std::string& path, const std::string& content);

    using FileWriter = std::function<bool(const std::string& path, const std::string& content)>;

    // On the first run, copies the fcitx5 edition's settings, or writes the defaults when it has none.
    // Never overwrites a file. The import is marked done last, so a run stopped halfway is finished
    // by the next one. Returns false when a write failed.
    bool prepareSettings(const SettingsPaths& paths, const FileWriter& write = writeFileAtomically);

} // namespace ngosen
