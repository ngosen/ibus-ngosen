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

    IBusResources::IBusResources() {
        Init();
        char* empty[] = {nullptr};
        macroTable_   = NewMacroTable(empty);
        // The spell check reads this even with the custom dictionary off. The variable lets the
        // tests run the engine from the build tree.
        const char* override = std::getenv("NGOSEN_IBUS_DICTIONARY");
        const char* path     = override != nullptr ? override : NGOSEN_IBUS_DICTIONARY;
        const int   fd       = ::open(path, O_RDONLY | O_CLOEXEC);
        if (fd != -1)
            dictionary_ = NewDictionary(static_cast<uintptr_t>(fd));
        else
            NGOSEN_WARN("No dictionary at " << path);
    }

    IBusResources::~IBusResources() {
        DeleteObject(macroTable_);
        DeleteObject(dictionary_);
    }

} // namespace ngosen
