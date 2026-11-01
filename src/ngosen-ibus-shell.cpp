/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-shell.h"

#include "ngosen-globals.h"
#include "ngosen-ibus-config.h"
#include "ngosen-log.h"

#include <gio/gio.h>
#include <regex>

namespace ngosen {

    namespace {
        constexpr const char* ShellService        = "org.gnome.Shell";
        constexpr const char* ShellPath           = "/org/gnome/Shell";
        constexpr const char* ExtensionsInterface = "org.gnome.Shell.Extensions";
        constexpr const char* ExtensionUuid       = "forward-keys@ngosen.github.io";
        constexpr double      ExtensionActive     = 1; // ExtensionState.ACTIVE
        constexpr int         ReplyTimeoutMs      = 2000;

        // mutter#4853: these drop forwarded keys unless the extension delivers them.
        bool dropsForwardedKeys(const std::string& version) {
            static const std::regex dropping("50\\.[0-3]");
            return std::regex_match(version, dropping);
        }

        struct ShellState {
            std::string      enabledMark;
            GDBusConnection* bus         = nullptr;
            GCancellable*    calls       = nullptr;
            guint            stateSignal = 0;
            std::string      version;
            bool             extensionRead   = false;
            bool             extensionKnown  = false;
            bool             extensionActive = false;
            bool             enabling        = false;
            bool             delivers        = false;
        };

        ShellState& shell() {
            static ShellState state;
            return state;
        }

        void markEnabled() {
            const std::string& mark = shell().enabledMark;
            if (!g_file_test(mark.c_str(), G_FILE_TEST_EXISTS) && !writeFileAtomically(mark, ""))
                NGOSEN_WARN("Cannot write " + mark);
        }

        void onEnabled(GObject* source, GAsyncResult* result, gpointer /*data*/) {
            GError*   error  = nullptr;
            GVariant* reply  = g_dbus_connection_call_finish(G_DBUS_CONNECTION(source), result, &error);
            shell().enabling = false;
            if (reply == nullptr) {
                NGOSEN_WARN(std::string("Cannot enable the forward-keys extension: ") + error->message);
                g_error_free(error);
                return;
            }
            gboolean enabled = FALSE;
            g_variant_get(reply, "(b)", &enabled);
            g_variant_unref(reply);
            if (enabled)
                markEnabled();
        }

        void enableExtensionOnce() {
            ShellState& s = shell();
            if (realMode != Mode::Sen || s.bus == nullptr || s.enabling || !s.extensionRead || !dropsForwardedKeys(s.version))
                return;
            if (s.extensionActive) {
                markEnabled();
                return;
            }
            // The Shell finds a newly installed extension only at the next login.
            if (!s.extensionKnown || g_file_test(s.enabledMark.c_str(), G_FILE_TEST_EXISTS))
                return;
            s.enabling = true;
            // Not cancellable: the state change this causes refreshes the other calls.
            g_dbus_connection_call(s.bus, ShellService, ShellPath, ExtensionsInterface, "EnableExtension", g_variant_new("(s)", ExtensionUuid), G_VARIANT_TYPE("(b)"),
                                   G_DBUS_CALL_FLAGS_NONE, ReplyTimeoutMs, nullptr, onEnabled, nullptr);
        }

        void update() {
            ShellState& s        = shell();
            const bool  delivers = !s.version.empty() && (!dropsForwardedKeys(s.version) || s.extensionActive);
            if (delivers != s.delivers) {
                s.delivers = delivers;
                NGOSEN_INFO("GNOME Shell " + s.version + (delivers ? " delivers forwarded keys" : " loses forwarded keys; typing in the preedit in apps it relays"));
            }
            enableExtensionOnce();
        }

        // A cancelled reply belongs to an older state of the Shell and changes nothing.
        GVariant* finishCall(GObject* source, GAsyncResult* result, bool& cancelled) {
            GError*   error = nullptr;
            GVariant* reply = g_dbus_connection_call_finish(G_DBUS_CONNECTION(source), result, &error);
            if (reply != nullptr)
                return reply;
            cancelled = g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED);
            if (!cancelled)
                NGOSEN_WARN(std::string("GNOME Shell did not answer: ") + error->message);
            g_error_free(error);
            return nullptr;
        }

        void onVersion(GObject* source, GAsyncResult* result, gpointer /*data*/) {
            bool      cancelled = false;
            GVariant* reply     = finishCall(source, result, cancelled);
            if (reply == nullptr)
                return;
            GVariant* value = nullptr;
            g_variant_get(reply, "(v)", &value);
            if (g_variant_is_of_type(value, G_VARIANT_TYPE_STRING))
                shell().version = g_variant_get_string(value, nullptr);
            g_variant_unref(value);
            g_variant_unref(reply);
            update();
        }

        void onExtension(GObject* source, GAsyncResult* result, gpointer /*data*/) {
            bool        cancelled = false;
            GVariant*   reply     = finishCall(source, result, cancelled);
            ShellState& s         = shell();
            if (reply == nullptr) {
                // An extension whose state cannot be read may have stopped, and keys would be lost.
                if (!cancelled) {
                    s.extensionRead = s.extensionKnown = s.extensionActive = false;
                    update();
                }
                return;
            }
            GVariant* info    = g_variant_get_child_value(reply, 0);
            gdouble   state   = 0;
            s.extensionRead   = true;
            s.extensionKnown  = g_variant_lookup(info, "state", "d", &state);
            s.extensionActive = s.extensionKnown && state == ExtensionActive;
            g_variant_unref(info);
            g_variant_unref(reply);
            update();
        }

        void cancelCalls() {
            ShellState& s = shell();
            if (s.calls == nullptr)
                return;
            g_cancellable_cancel(s.calls);
            g_clear_object(&s.calls);
        }

        void refresh() {
            ShellState& s = shell();
            cancelCalls();
            s.calls = g_cancellable_new();
            g_dbus_connection_call(s.bus, ShellService, ShellPath, "org.freedesktop.DBus.Properties", "Get", g_variant_new("(ss)", ShellService, "ShellVersion"),
                                   G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, ReplyTimeoutMs, s.calls, onVersion, nullptr);
            g_dbus_connection_call(s.bus, ShellService, ShellPath, ExtensionsInterface, "GetExtensionInfo", g_variant_new("(s)", ExtensionUuid), G_VARIANT_TYPE("(a{sv})"),
                                   G_DBUS_CALL_FLAGS_NONE, ReplyTimeoutMs, s.calls, onExtension, nullptr);
        }

        void onStateChanged(GDBusConnection* /*bus*/, const gchar* /*sender*/, const gchar* /*path*/, const gchar* /*interface*/, const gchar* /*signal*/, GVariant* parameters,
                            gpointer /*data*/) {
            const gchar* uuid = nullptr;
            g_variant_get_child(parameters, 0, "&s", &uuid);
            if (g_strcmp0(uuid, ExtensionUuid) == 0)
                refresh();
        }

        void onShellAppeared(GDBusConnection* bus, const gchar* /*name*/, const gchar* /*owner*/, gpointer /*data*/) {
            ShellState& s = shell();
            s.bus         = G_DBUS_CONNECTION(g_object_ref(bus));
            s.stateSignal = g_dbus_connection_signal_subscribe(bus, ShellService, ExtensionsInterface, "ExtensionStateChanged", ShellPath, nullptr, G_DBUS_SIGNAL_FLAGS_NONE,
                                                               onStateChanged, nullptr, nullptr);
            refresh();
        }

        void onShellVanished(GDBusConnection* /*bus*/, const gchar* /*name*/, gpointer /*data*/) {
            ShellState& s = shell();
            cancelCalls();
            if (s.bus != nullptr) {
                g_dbus_connection_signal_unsubscribe(s.bus, s.stateSignal);
                g_clear_object(&s.bus);
            }
            s.version.clear();
            s.extensionRead = s.extensionKnown = s.extensionActive = false;
            update();
        }
    } // namespace

    void watchShell(const std::string& enabledMark) {
        ShellState& s = shell();
        // Gõ Sen may have just been turned on again, with the Shell's state already read.
        if (!s.enabledMark.empty()) {
            update();
            return;
        }
        s.enabledMark = enabledMark;
        g_bus_watch_name(G_BUS_TYPE_SESSION, ShellService, G_BUS_NAME_WATCHER_FLAGS_NONE, onShellAppeared, onShellVanished, nullptr, nullptr);
    }

    bool shellDeliversKeys() {
        return shell().delivers;
    }

} // namespace ngosen
