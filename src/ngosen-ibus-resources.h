/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include "ngosen-engine-resources.h"
#include "ngosen-ibus-config.h"

#include <gio/gio.h>
#include <memory>

namespace ngosen {

    // Settings and tables every field shares. No emoji list: the IBus edition has no emoji picker.
    class IBusResources final : public EngineResources {
      public:
        // The handles a Vietnamese engine was built with. Each field holds the set it was built
        // with, so a reload frees the old set only once no engine uses it.
        struct Tables {
            uintptr_t dictionary = 0;
            uintptr_t macroTable = 0;
            Tables()             = default;
            ~Tables();
            Tables(const Tables&)            = delete;
            Tables& operator=(const Tables&) = delete;
        };

        explicit IBusResources(SettingsPaths paths);
        ~IBusResources() override;
        IBusResources(const IBusResources&)            = delete;
        IBusResources& operator=(const IBusResources&) = delete;

        const Options& options() const override {
            return settings_.options;
        }
        std::vector<KeymapEntry> customKeymap() const override {
            return settings_.enableCustomKeymap ? keymap_ : std::vector<KeymapEntry>{};
        }
        uintptr_t dictionary() const override {
            return tables_->dictionary;
        }
        uintptr_t macroTable() const override {
            return tables_->macroTable;
        }
        std::vector<EmojiEntry> emojiHistory() override {
            return {};
        }
        std::vector<EmojiEntry> searchEmoji(const std::string& /*prefix*/) override {
            return {};
        }
        void      recordEmoji(const EmojiEntry& /*entry*/) override {}
        Recorder& recorder() override {
            return recorder_;
        }

        std::shared_ptr<const Tables> tables() const {
            return tables_;
        }
        // Counts reloads, so a field knows its engine was built from older settings.
        unsigned generation() const {
            return generation_;
        }
        // Rereads the settings if a file changed since the last load.
        void reloadIfChanged();

      private:
        void                     load();
        void                     openDictionary(Tables& tables) const;

        SettingsPaths            paths_;
        IBusSettings             settings_;
        std::vector<KeymapEntry> keymap_;
        std::shared_ptr<Tables>  tables_;
        unsigned                 generation_ = 0;
        bool                     changed_    = false;
        GFileMonitor*            monitor_    = nullptr;
        Recorder                 recorder_;
    };

} // namespace ngosen
