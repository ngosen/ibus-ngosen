/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-resources.h"

#include "bamboo-core.h"
#include "ngosen-log.h"

#include <cstdlib>
#include <fcntl.h>

namespace ngosen {

    namespace {

        uintptr_t newMacroTable(const std::vector<KeymapEntry>& macros) {
            std::vector<char*> definition;
            definition.reserve((macros.size() * 2) + 1);
            for (const auto& macro : macros) {
                // The C API takes char** but does not write through it.
                definition.push_back(const_cast<char*>(macro.key.data()));   //NOLINT
                definition.push_back(const_cast<char*>(macro.value.data())); //NOLINT
            }
            definition.push_back(nullptr);
            return NewMacroTable(definition.data());
        }

        std::vector<KeymapEntry> readList(const std::string& path, const char* name) {
            std::string text;
            return readFile(path, text) ? iniList(parseIni(text), name) : std::vector<KeymapEntry>{};
        }

        uintptr_t openDictionaryAt(const std::string& path) {
            const int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
            return fd != -1 ? NewDictionary(static_cast<uintptr_t>(fd)) : 0;
        }

        // Editors and atomic saves also leave temporary files there.
        bool isSettingsFile(GFile* file) {
            if (file == nullptr)
                return false;
            gchar*     name  = g_file_get_basename(file);
            const bool known = g_strcmp0(name, "ngosen.conf") == 0 || g_strcmp0(name, "ngosen-macro-table.conf") == 0 || g_strcmp0(name, "ngosen-custom-keymap.conf") == 0;
            g_free(name);
            return known;
        }

        void onDirChanged(GFileMonitor* /*monitor*/, GFile* file, GFile* other, GFileMonitorEvent /*event*/, gpointer changed) {
            if (isSettingsFile(file) || isSettingsFile(other))
                *static_cast<bool*>(changed) = true;
        }

    } // namespace

    IBusResources::IBusResources(SettingsPaths paths) : paths_(std::move(paths)) {
        Init();
        prepareSettings(paths_);
        load();
        GFile* dir = g_file_new_for_path(paths_.configDir.c_str());
        monitor_   = g_file_monitor_directory(dir, G_FILE_MONITOR_WATCH_MOVES, nullptr, nullptr);
        g_object_unref(dir);
        if (monitor_ != nullptr)
            g_signal_connect(monitor_, "changed", G_CALLBACK(onDirChanged), &changed_);
    }

    IBusResources::~IBusResources() {
        if (monitor_ != nullptr)
            g_object_unref(monitor_);
        DeleteObject(macroTable_);
        DeleteObject(dictionary_);
    }

    void IBusResources::reloadIfChanged() {
        if (!changed_)
            return;
        changed_ = false;
        load();
        ++generation_;
        NGOSEN_INFO("Settings reloaded");
    }

    bool IBusResources::saveSetting(const std::string& key, const std::string& value, IBusSettings& saved) const {
        std::string text;
        // A deleted file comes back whole, so the settings window still finds every key.
        if (!readFile(paths_.settingsFile(), text))
            text = settingsText(settings_);
        text = withSetting(text, key, value);
        if (!writeFileAtomically(paths_.settingsFile(), text))
            return false;
        saved = readSettings(parseIni(text));
        return true;
    }

    void IBusResources::load() {
        std::string text;
        settings_ = readFile(paths_.settingsFile(), text) ? readSettings(parseIni(text)) : defaultSettings();
        keymap_   = readList(paths_.keymapFile(), "CustomKeymap");
        // An engine keeps its own reference to the tables, so the old handles can go now.
        DeleteObject(macroTable_);
        DeleteObject(dictionary_);
        macroTable_ = newMacroTable(readList(paths_.macroFile(), "Macro"));
        dictionary_ = openDictionary();
    }

    // The user's dictionary only with the custom dictionary on, as the fcitx5 edition does. The
    // spell check reads the packaged one otherwise.
    uintptr_t IBusResources::openDictionary() const {
        if (settings_.enableDictionary) {
            if (const uintptr_t dictionary = openDictionaryAt(paths_.dictionaryFile())) {
                NGOSEN_INFO("Dictionary: " << paths_.dictionaryFile());
                return dictionary;
            }
        }
        // Lets the tests run the engine from the build tree.
        const char*     override   = std::getenv("NGOSEN_IBUS_DICTIONARY");
        const char*     path       = override != nullptr ? override : NGOSEN_IBUS_DICTIONARY;
        const uintptr_t dictionary = openDictionaryAt(path);
        if (dictionary != 0)
            NGOSEN_INFO("Dictionary: " << path);
        else
            NGOSEN_WARN("No dictionary at " << path);
        return dictionary;
    }

} // namespace ngosen
