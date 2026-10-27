/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-log.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <syslog.h>

namespace ngosen {

    namespace {
        // Lets the tests read what the engine logs.
        FILE* logFile() {
            static FILE* file = [] {
                const char* path = std::getenv("NGOSEN_IBUS_LOG_FILE");
                return path != nullptr ? std::fopen(path, "ae") : nullptr;
            }();
            return file;
        }
    } // namespace

    // NGOSEN_DEBUG=1 in the engine's environment turns on the debug and info lines.
    bool logEnabled(LogLevel level) {
        static const bool verbose = [] {
            const char* value = std::getenv("NGOSEN_DEBUG");
            return value != nullptr && *value != '\0' && std::strcmp(value, "0") != 0;
        }();
        return verbose || level == LogLevel::Warn || level == LogLevel::Error;
    }

    // ibus-daemon sends the engine's stdout and stderr to /dev/null, so the lines go to the journal.
    void writeLog(LogLevel level, const char* file, int line, const std::string& message) {
        const char* slash = std::strrchr(file, '/');
        const char* name  = slash != nullptr ? slash + 1 : file;
        if (FILE* out = logFile()) {
            std::fprintf(out, "%s:%d %s\n", name, line, message.c_str());
            std::fflush(out);
            return;
        }
        int priority = LOG_DEBUG;
        if (level == LogLevel::Info)
            priority = LOG_INFO;
        else if (level == LogLevel::Warn)
            priority = LOG_WARNING;
        else if (level == LogLevel::Error)
            priority = LOG_ERR;
        syslog(LOG_USER | priority, "%s:%d %s", name, line, message.c_str());
    }

} // namespace ngosen
