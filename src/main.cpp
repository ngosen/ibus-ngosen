/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "bamboo-core.h"
#include "ngosen-ibus-config.h"
#include "ngosen-ibus-engine.h"

#include <cstdio>
#include <cstring>
#include <ibus.h>
#include <syslog.h>

namespace {

    // The settings window asks the engine, so the defaults and the names live in one place.
    int runSettingsCommand(const char* command) {
        const bool methods = std::strcmp(command, "--list-input-methods") == 0;
        const bool print   = std::strcmp(command, "--print-settings") == 0;
        if (!methods && !print && std::strcmp(command, "--list-charsets") != 0)
            return -1;
        Init();
        if (print) {
            // What the engine types with, after the first-run import: missing or bad keys show
            // their defaults.
            const auto  paths = ngosen::SettingsPaths::fromEnvironment();
            std::string text;
            if (!ngosen::prepareSettings(paths) || !ngosen::readFile(paths.settingsFile(), text))
                return 1;
            std::fputs(ngosen::settingsText(ngosen::readSettings(ngosen::parseIni(text))).c_str(), stdout);
            return 0;
        }
        for (const auto& name : methods ? ngosen::inputMethodNames() : ngosen::charsetNames())
            std::printf("%s\n", name.c_str());
        return 0;
    }

} // namespace

int main(int argc, char** argv) {
    openlog("ibus-engine-ngosen", LOG_PID, LOG_USER);
    if (argc > 1) {
        if (const int status = runSettingsCommand(argv[1]); status >= 0)
            return status;
    }
    ibus_init();
    IBusBus* bus = ibus_bus_new();
    if (!ibus_bus_is_connected(bus)) {
        std::fprintf(stderr, "ibus-engine-ngosen: cannot connect to the IBus daemon\n");
        return 1;
    }
    g_signal_connect(bus, "disconnected", G_CALLBACK(+[](IBusBus*, gpointer) { ibus_quit(); }), nullptr);

    IBusFactory* factory = ibus_factory_new(ibus_bus_get_connection(bus));
    ngosen::addEngine(factory);

    // The daemon starts the engine with --ibus from the component file; without it the engine
    // registers itself, so it can be run by hand against a daemon that has no component file.
    if (argc > 1 && std::strcmp(argv[1], "--ibus") == 0) {
        ibus_bus_request_name(bus, "org.freedesktop.IBus.NgoSen", 0);
    } else {
        IBusComponent* component = ibus_component_new("org.freedesktop.IBus.NgoSen", "Ngó Sen", NGOSEN_IBUS_VERSION, "GPL-3.0-or-later", "Ngó Sen contributors",
                                                      "https://github.com/ngosen/ibus-ngosen", "", "ibus-ngosen");
        ibus_component_add_engine(component,
                                  ibus_engine_desc_new("ngosen", "Ngó Sen", "Vietnamese input method", "vi", "GPL-3.0-or-later", "Ngó Sen contributors", "ibus-ngosen", "default"));
        if (!ibus_bus_register_component(bus, component)) {
            std::fprintf(stderr, "ibus-engine-ngosen: the IBus daemon refused the engine\n");
            return 1;
        }
    }
    ibus_main();
    return 0;
}
