/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-shell.h"

#include "ngosen-globals.h"
#include "ngosen-gnome-apps.h"
#include "ngosen-ibus-config.h"
#include "ngosen-ibus-program-name.h"
#include "ngosen-log.h"

#include <cstdlib>
#include <gio/gio.h>
#include <regex>
#include <vector>

namespace ngosen {

    namespace {
        constexpr const char* ShellService        = "org.gnome.Shell";
        constexpr const char* ShellPath           = "/org/gnome/Shell";
        constexpr const char* ExtensionsInterface = "org.gnome.Shell.Extensions";
        constexpr const char* ExtensionUuid       = "forward-keys@ngosen.github.io";
        constexpr double      ExtensionActive     = 1; // ExtensionState.ACTIVE
        constexpr int         ReplyTimeoutMs      = 2000;
        constexpr const char* PropertiesInterface = "org.freedesktop.DBus.Properties";
        constexpr const char* PortalService       = "org.freedesktop.impl.portal.desktop.gnome";

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
            guint            overviewSignal  = 0;
            // The portal's GetRunningApplications traffic, seen from a monitor connection. Only on
            // Wayland, where the window with the focus is the one typed into.
            bool                   watchPortal = false;
            GDBusConnection*       monitor     = nullptr;
            unsigned               monitorRun  = 0;
            std::string            shellOwner;
            std::string            portalOwner;
            IntrospectReplyMatcher matcher;
            GnomeAppNames          names;
            std::string            published;
            std::string            program;
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

        void publish() {
            ShellState& s = shell();
            if (s.names.name() == s.published)
                return;
            s.published = s.names.name();
            s.program   = s.published.empty() ? std::string() : gnomeProgramName(s.published);
            NGOSEN_INFO("GNOME focused app: " + (s.program.empty() ? std::string("unknown") : s.program) + ", from " + s.names.source());
        }

        std::vector<IntrospectEntry> readIntrospectReply(GVariant* body) {
            std::vector<IntrospectEntry> entries;
            if (body == nullptr || !g_variant_is_of_type(body, G_VARIANT_TYPE("(a{sa{sv}})")))
                return entries;
            GVariantIter* apps       = nullptr;
            const gchar*  id         = nullptr;
            GVariant*     properties = nullptr;
            g_variant_get(body, "(a{sa{sv}})", &apps);
            while (g_variant_iter_loop(apps, "{&s@a{sv}}", &id, &properties)) {
                IntrospectEntry entry{id, {}};
                if (GVariant* seats = g_variant_lookup_value(properties, "active-on-seats", G_VARIANT_TYPE_STRING_ARRAY)) {
                    gsize         count = 0;
                    const gchar** list  = g_variant_get_strv(seats, &count);
                    entry.activeOnSeats.assign(list, list + count);
                    g_free(list);
                    g_variant_unref(seats);
                }
                entries.push_back(std::move(entry));
            }
            g_variant_iter_free(apps);
            return entries;
        }

        struct Monitored {
            unsigned      run;
            GDBusMessage* message;
        };

        std::string header(const gchar* value) {
            return value != nullptr ? value : "";
        }

        gboolean readMonitored(gpointer data) {
            auto*         monitored = static_cast<Monitored*>(data);
            GDBusMessage* message   = monitored->message;
            ShellState&   s         = shell();
            if (monitored->run == s.monitorRun) {
                const std::string sender      = header(g_dbus_message_get_sender(message));
                const std::string destination = header(g_dbus_message_get_destination(message));
                const auto        type        = g_dbus_message_get_message_type(message);
                if (type == G_DBUS_MESSAGE_TYPE_METHOD_CALL && g_strcmp0(g_dbus_message_get_member(message), "GetRunningApplications") == 0) {
                    s.matcher.call(sender, destination, g_dbus_message_get_serial(message));
                } else if (type == G_DBUS_MESSAGE_TYPE_METHOD_RETURN &&
                           s.matcher.answers(sender, destination, g_dbus_message_get_reply_serial(message), header(g_dbus_message_get_signature(message)))) {
                    s.names.setPortalApps(runningApps(readIntrospectReply(g_dbus_message_get_body(message))));
                    publish();
                }
            }
            g_object_unref(message);
            delete monitored;
            return G_SOURCE_REMOVE;
        }

        // Runs in GDBus's own thread, so what it sees is read in the main loop. The messages monitored
        // stop here: the bus drops a monitor that answers one.
        GDBusMessage* filterMonitored(GDBusConnection* connection, GDBusMessage* message, gboolean incoming, gpointer data) {
            if (!incoming || g_strcmp0(g_dbus_message_get_destination(message), g_dbus_connection_get_unique_name(connection)) == 0)
                return message;
            g_main_context_invoke_full(nullptr, G_PRIORITY_DEFAULT, readMonitored, new Monitored{GPOINTER_TO_UINT(data), message}, nullptr);
            return nullptr;
        }

        void onMonitoring(GObject* source, GAsyncResult* result, gpointer /*data*/) {
            GError*   error = nullptr;
            GVariant* reply = g_dbus_connection_call_finish(G_DBUS_CONNECTION(source), result, &error);
            if (reply == nullptr) {
                NGOSEN_WARN(std::string("Cannot watch GNOME's portal for the focused app: ") + error->message);
                g_error_free(error);
                return;
            }
            g_variant_unref(reply);
            NGOSEN_INFO("Watching GNOME's portal for the focused app");
        }

        void stopMonitor() {
            ShellState& s = shell();
            ++s.monitorRun;
            if (s.monitor == nullptr)
                return;
            g_dbus_connection_close(s.monitor, nullptr, nullptr, nullptr);
            g_clear_object(&s.monitor);
        }

        // A monitor connection may send nothing after this call, so it is a connection of its own.
        void startMonitor() {
            ShellState& s = shell();
            stopMonitor();
            if (!s.watchPortal || s.shellOwner.empty() || s.portalOwner.empty())
                return;
            GError* error   = nullptr;
            gchar*  address = g_dbus_address_get_for_bus_sync(G_BUS_TYPE_SESSION, nullptr, &error);
            if (address != nullptr) {
                const auto flags = static_cast<GDBusConnectionFlags>(G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT | G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION);
                s.monitor        = g_dbus_connection_new_for_address_sync(address, flags, nullptr, nullptr, &error);
                g_free(address);
            }
            if (s.monitor == nullptr) {
                NGOSEN_WARN(std::string("Cannot connect to the session bus to watch GNOME's portal: ") + error->message);
                g_error_free(error);
                return;
            }
            g_dbus_connection_add_filter(s.monitor, filterMonitored, GUINT_TO_POINTER(s.monitorRun), nullptr);
            const std::string call =
                "type='method_call',sender='" + s.portalOwner + "',destination='" + s.shellOwner + "',interface='org.gnome.Shell.Introspect',member='GetRunningApplications'";
            const std::string reply   = "type='method_return',sender='" + s.shellOwner + "',destination='" + s.portalOwner + "'";
            const gchar*      rules[] = {call.c_str(), reply.c_str(), nullptr};
            g_dbus_connection_call(s.monitor, "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus.Monitoring", "BecomeMonitor",
                                   g_variant_new("(^asu)", rules, 0U), nullptr, G_DBUS_CALL_FLAGS_NONE, ReplyTimeoutMs, nullptr, onMonitoring, nullptr);
        }

        void setOwners(const std::string& shellOwner, const std::string& portalOwner) {
            ShellState& s = shell();
            if (shellOwner == s.shellOwner && portalOwner == s.portalOwner)
                return;
            // A restarted Shell or portal tells the app only at the next app change.
            s.names.dropPortalApp();
            s.shellOwner  = shellOwner;
            s.portalOwner = portalOwner;
            s.matcher.setOwners(shellOwner, portalOwner);
            startMonitor();
            publish();
        }

        void onPortalAppeared(GDBusConnection* /*bus*/, const gchar* /*name*/, const gchar* owner, gpointer /*data*/) {
            setOwners(shell().shellOwner, owner);
        }

        void onPortalVanished(GDBusConnection* /*bus*/, const gchar* /*name*/, gpointer /*data*/) {
            setOwners(shell().shellOwner, "");
        }

        void setOverview(GVariant* value) {
            if (value == nullptr || !g_variant_is_of_type(value, G_VARIANT_TYPE_BOOLEAN))
                return;
            shell().names.setOverviewActive(g_variant_get_boolean(value));
            publish();
        }

        void onOverview(GObject* source, GAsyncResult* result, gpointer /*data*/) {
            bool      cancelled = false;
            GVariant* reply     = finishCall(source, result, cancelled);
            if (reply == nullptr)
                return;
            GVariant* value = nullptr;
            g_variant_get(reply, "(v)", &value);
            setOverview(value);
            g_variant_unref(value);
            g_variant_unref(reply);
        }

        void askOverview() {
            ShellState& s = shell();
            g_dbus_connection_call(s.bus, ShellService, ShellPath, PropertiesInterface, "Get", g_variant_new("(ss)", ShellService, "OverviewActive"), G_VARIANT_TYPE("(v)"),
                                   G_DBUS_CALL_FLAGS_NONE, ReplyTimeoutMs, s.calls, onOverview, nullptr);
        }

        void onPropertiesChanged(GDBusConnection* /*bus*/, const gchar* /*sender*/, const gchar* /*path*/, const gchar* /*interface*/, const gchar* /*signal*/,
                                 GVariant* parameters, gpointer /*data*/) {
            if (!g_variant_is_of_type(parameters, G_VARIANT_TYPE("(sa{sv}as)")))
                return;
            GVariant*     changed     = g_variant_get_child_value(parameters, 1);
            const gchar** invalidated = nullptr;
            g_variant_get_child(parameters, 2, "^a&s", &invalidated);
            if (GVariant* value = g_variant_lookup_value(changed, "OverviewActive", G_VARIANT_TYPE_BOOLEAN)) {
                setOverview(value);
                g_variant_unref(value);
            }
            if (invalidated != nullptr && g_strv_contains(invalidated, "OverviewActive"))
                askOverview();
            g_free(invalidated);
            g_variant_unref(changed);
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
            g_dbus_connection_call(s.bus, ShellService, ShellPath, PropertiesInterface, "Get", g_variant_new("(ss)", ShellService, "ShellVersion"), G_VARIANT_TYPE("(v)"),
                                   G_DBUS_CALL_FLAGS_NONE, ReplyTimeoutMs, s.calls, onVersion, nullptr);
            g_dbus_connection_call(s.bus, ShellService, ShellPath, ExtensionsInterface, "GetExtensionInfo", g_variant_new("(s)", ExtensionUuid), G_VARIANT_TYPE("(a{sv})"),
                                   G_DBUS_CALL_FLAGS_NONE, ReplyTimeoutMs, s.calls, onExtension, nullptr);
            // Asked again with the others, since a refresh cancels a question still open.
            askOverview();
        }

        void onStateChanged(GDBusConnection* /*bus*/, const gchar* /*sender*/, const gchar* /*path*/, const gchar* /*interface*/, const gchar* /*signal*/, GVariant* parameters,
                            gpointer /*data*/) {
            const gchar* uuid = nullptr;
            g_variant_get_child(parameters, 0, "&s", &uuid);
            if (g_strcmp0(uuid, ExtensionUuid) == 0)
                refresh();
        }

        void onShellAppeared(GDBusConnection* bus, const gchar* /*name*/, const gchar* owner, gpointer /*data*/) {
            ShellState& s    = shell();
            s.bus            = G_DBUS_CONNECTION(g_object_ref(bus));
            s.stateSignal    = g_dbus_connection_signal_subscribe(bus, ShellService, ExtensionsInterface, "ExtensionStateChanged", ShellPath, nullptr, G_DBUS_SIGNAL_FLAGS_NONE,
                                                                  onStateChanged, nullptr, nullptr);
            s.overviewSignal = g_dbus_connection_signal_subscribe(bus, ShellService, PropertiesInterface, "PropertiesChanged", ShellPath, ShellService, G_DBUS_SIGNAL_FLAGS_NONE,
                                                                  onPropertiesChanged, nullptr, nullptr);
            setOwners(owner, s.portalOwner);
            refresh();
        }

        void onShellVanished(GDBusConnection* /*bus*/, const gchar* /*name*/, gpointer /*data*/) {
            ShellState& s = shell();
            cancelCalls();
            if (s.bus != nullptr) {
                g_dbus_connection_signal_unsubscribe(s.bus, s.stateSignal);
                g_dbus_connection_signal_unsubscribe(s.bus, s.overviewSignal);
                g_clear_object(&s.bus);
            }
            s.version.clear();
            s.extensionRead = s.extensionKnown = s.extensionActive = false;
            update();
            s.names.setOverviewActive(false);
            setOwners("", s.portalOwner);
            publish();
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
        // On X11 apps reach IBus themselves; the Shell is the client only for its own fields, and the
        // portal would name the window behind them.
        const char* session = std::getenv("XDG_SESSION_TYPE");
        s.watchPortal       = session != nullptr && std::string(session) == "wayland";
        g_bus_watch_name(G_BUS_TYPE_SESSION, ShellService, G_BUS_NAME_WATCHER_FLAGS_NONE, onShellAppeared, onShellVanished, nullptr, nullptr);
        if (s.watchPortal)
            g_bus_watch_name(G_BUS_TYPE_SESSION, PortalService, G_BUS_NAME_WATCHER_FLAGS_NONE, onPortalAppeared, onPortalVanished, nullptr, nullptr);
    }

    const std::string& shellFocusedApp() {
        return shell().program;
    }

    bool shellDeliversKeys() {
        return shell().delivers;
    }

    void setShellDeliversKeysForTest(bool delivers) {
        shell().delivers = delivers;
    }

} // namespace ngosen
