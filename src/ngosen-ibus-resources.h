/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include "ngosen-engine-resources.h"

namespace ngosen {

    // Settings and tables every field shares. No emoji list: the IBus edition has no emoji picker.
    class IBusResources final : public EngineResources {
      public:
        IBusResources();
        ~IBusResources() override;
        IBusResources(const IBusResources&)            = delete;
        IBusResources& operator=(const IBusResources&) = delete;

        const Options& options() const override {
            return options_;
        }
        std::vector<KeymapEntry> customKeymap() const override {
            return {};
        }
        uintptr_t dictionary() const override {
            return dictionary_;
        }
        uintptr_t macroTable() const override {
            return macroTable_;
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

      private:
        Options   options_;
        uintptr_t dictionary_ = 0;
        uintptr_t macroTable_ = 0;
        Recorder  recorder_;
    };

} // namespace ngosen
