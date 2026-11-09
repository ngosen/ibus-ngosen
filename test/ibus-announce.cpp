/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
// Runs under dbus-run-session, with a stand-in for the desktop's notification service.
#include "ngosen-ibus-announce.h"

#include <gio/gio.h>

#include <functional>
#include <iostream>
#include <string>
#include <vector>

namespace {
    int  failures = 0;

    void check(bool ok, const std::string& what) {
        if (!ok) {
            std::cerr << "FAIL: " << what << '\n';
            ++failures;
        }
    }

    const char* const Path      = "/org/freedesktop/Notifications";
    const char* const Interface = "org.freedesktop.Notifications";
    const char* const Xml       = "<node><interface name='org.freedesktop.Notifications'><method name='Notify'>"
                                  "<arg type='s' direction='in'/><arg type='u' direction='in'/><arg type='s' direction='in'/>"
                                  "<arg type='s' direction='in'/><arg type='s' direction='in'/><arg type='as' direction='in'/>"
                                  "<arg type='a{sv}' direction='in'/><arg type='i' direction='in'/><arg type='u' direction='out'/>"
                                  "</method></interface></node>";
    const guint32     NoticeId  = 7;

    struct Sent {
        int                      count = 0;
        std::string              title;
        std::vector<std::string> actions;
        gint32                   expire = -1;
    };

    void onCall(GDBusConnection*, const gchar*, const gchar*, const gchar*, const gchar*, GVariant* parameters, GDBusMethodInvocation* invocation, gpointer data) {
        auto*        sent    = static_cast<Sent*>(data);
        const gchar* title   = nullptr;
        GVariant*    actions = nullptr;
        g_variant_get(parameters, "(&su&s&s&s@asa{sv}i)", nullptr, nullptr, nullptr, &title, nullptr, &actions, nullptr, &sent->expire);
        sent->title = title;
        sent->actions.clear();
        GVariantIter iter;
        const gchar* action = nullptr;
        g_variant_iter_init(&iter, actions);
        while (g_variant_iter_next(&iter, "&s", &action))
            sent->actions.emplace_back(action);
        g_variant_unref(actions);
        ++sent->count;
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(u)", NoticeId));
    }

    void spin(const std::function<bool()>& done) {
        const gint64 until = g_get_monotonic_time() + 5 * G_USEC_PER_SEC;
        while (!done() && g_get_monotonic_time() < until)
            g_main_context_iteration(nullptr, FALSE);
    }

    void settle() {
        const gint64 until = g_get_monotonic_time() + G_USEC_PER_SEC / 5;
        while (g_get_monotonic_time() < until)
            g_main_context_iteration(nullptr, FALSE);
    }

    void emit(GDBusConnection* server, const char* signal, GVariant* parameters) {
        g_dbus_connection_emit_signal(server, nullptr, Path, Interface, signal, parameters, nullptr);
        g_dbus_connection_flush_sync(server, nullptr, nullptr);
        settle();
    }
} // namespace

int main() {
    GError*          error  = nullptr;
    GDBusConnection* server = g_dbus_connection_new_for_address_sync(
        g_getenv("DBUS_SESSION_BUS_ADDRESS"), static_cast<GDBusConnectionFlags>(G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT | G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION),
        nullptr, nullptr, &error);
    if (server == nullptr) {
        std::cerr << "no session bus: " << error->message << '\n';
        return 1;
    }
    Sent                 sent;
    GDBusNodeInfo*       node   = g_dbus_node_info_new_for_xml(Xml, nullptr);
    GDBusInterfaceVTable vtable = {onCall, nullptr, nullptr, {}};
    g_dbus_connection_register_object(server, Path, node->interfaces[0], &vtable, &sent, nullptr, nullptr);
    GVariant* owned = g_dbus_connection_call_sync(server, "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "RequestName",
                                                  g_variant_new("(su)", Interface, 0U), nullptr, G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr);
    check(owned != nullptr, "the stand-in takes the service name");

    int opened = 0;
    ngosen::announceRelease("", 0, [&] { ++opened; });
    settle();
    check(sent.count == 0, "nothing is announced without a release");

    ngosen::announceRelease("1.3", 0, [&] { ++opened; });
    spin([&] { return sent.count == 1; });
    check(sent.count == 1, "the release is announced once");
    check(!sent.title.empty(), "the notice has a title");
    check(sent.expire == 0, "the notice waits for the user");
    bool show = false;
    for (size_t i = 0; i + 1 < sent.actions.size(); i += 2)
        show = show || sent.actions[i] == "show";
    check(show, "the notice has a Show button");
    settle();

    emit(server, "ActionInvoked", g_variant_new("(us)", NoticeId + 1, "show"));
    check(opened == 0, "another app's notice opens nothing");
    emit(server, "ActionInvoked", g_variant_new("(us)", NoticeId, "show"));
    check(opened == 1, "Show opens the What's new page");
    emit(server, "NotificationClosed", g_variant_new("(uu)", NoticeId, 2U));
    emit(server, "ActionInvoked", g_variant_new("(us)", NoticeId, "show"));
    check(opened == 1, "a closed notice is forgotten");

    if (owned != nullptr)
        g_variant_unref(owned);
    g_dbus_node_info_unref(node);
    g_object_unref(server);
    if (failures == 0)
        std::cout << "all announce checks passed\n";
    return failures == 0 ? 0 : 1;
}
