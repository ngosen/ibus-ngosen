/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-sources.h"

#include "ngosen-log.h"

#include <algorithm>
#include <gio/gio.h>

namespace ngosen {

    namespace {
        const InputSource Engine{"ibus", "ngosen"};
        const InputSource UsLayout{"xkb", "us"};
        const char* const SourcesSchema = "org.gnome.desktop.input-sources";

        bool              has(const std::vector<InputSource>& sources, const InputSource& source) {
            return std::find(sources.begin(), sources.end(), source) != sources.end();
        }

        GSettings* sourcesSettings() {
            GSettingsSchemaSource* schemas = g_settings_schema_source_get_default();
            GSettingsSchema*       schema  = schemas != nullptr ? g_settings_schema_source_lookup(schemas, SourcesSchema, TRUE) : nullptr;
            if (schema == nullptr)
                return nullptr;
            g_settings_schema_unref(schema);
            return g_settings_new(SourcesSchema);
        }

        std::optional<std::vector<InputSource>> readSources() {
            GSettings* settings = sourcesSettings();
            if (settings == nullptr)
                return std::nullopt;
            std::vector<InputSource> sources;
            GVariant*                value = g_settings_get_value(settings, "sources");
            GVariantIter             iter;
            const gchar*             type = nullptr;
            const gchar*             id   = nullptr;
            g_variant_iter_init(&iter, value);
            while (g_variant_iter_next(&iter, "(&s&s)", &type, &id))
                sources.emplace_back(type, id);
            g_variant_unref(value);
            g_object_unref(settings);
            return sources;
        }

        bool writeSources(const std::vector<InputSource>& sources) {
            GSettings* settings = sourcesSettings();
            if (settings == nullptr)
                return false;
            GVariantBuilder builder;
            g_variant_builder_init(&builder, G_VARIANT_TYPE("a(ss)"));
            for (const auto& [type, id] : sources)
                g_variant_builder_add(&builder, "(ss)", type.c_str(), id.c_str());
            const bool ok = g_settings_set_value(settings, "sources", g_variant_builder_end(&builder));
            g_settings_sync();
            g_object_unref(settings);
            return ok;
        }
    } // namespace

    std::vector<InputSource> withoutDuplicateLayout(const std::vector<InputSource>& sources) {
        if (!has(sources, Engine))
            return sources;
        std::vector<InputSource> kept;
        std::copy_if(sources.begin(), sources.end(), std::back_inserter(kept), [](const InputSource& s) { return s != UsLayout; });
        return kept;
    }

    bool dropDuplicateLayoutOnce(const SettingsPaths& paths, bool hasToggleKey, const InputSourceStore& store, const FileWriter& write) {
        const std::string mark = paths.duplicateLayoutMark();
        if (g_file_test(mark.c_str(), G_FILE_TEST_EXISTS))
            return true;
        const auto sources = store.get();
        // Started from IBus Preferences or before the source was added: not yet the time.
        if (!sources || !has(*sources, Engine))
            return true;
        // Decided once, on the first run as a source: a toggle key turned on later removes nothing.
        // The mark goes first, so a failed change leaves the source rather than removing it later.
        if (!write(mark, ""))
            return false;
        // Without a toggle key the US layout is the way to English.
        if (!hasToggleKey)
            return true;
        const auto kept = withoutDuplicateLayout(*sources);
        if (kept == *sources)
            return true;
        NGOSEN_INFO("Removing the US layout input source; the toggle key switches to English");
        return store.set(kept);
    }

    InputSourceStore gnomeInputSources() {
        return {readSources, writeSources};
    }

} // namespace ngosen
