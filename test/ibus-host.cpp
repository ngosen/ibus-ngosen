/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-host.h"
#include "ngosen-xtest.h"

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using namespace ngosen;

namespace {

    int  failures = 0;

    void check(bool ok, const std::string& what) {
        if (!ok) {
            ++failures;
            std::cout << "FAIL " << what << '\n';
        }
    }

    // On an X11 session the core asks for real key presses, as fcitx5 gives it.
    void testXTest() {
        IBusEngine       engine{};
        IBusHost         host(&engine);
        std::vector<int> sent;
        setXTestSenderForTest([&sent](int count) {
            sent.push_back(count);
            return true;
        });
        check(host.pressSystemKeys(3) && sent == std::vector<int>{3}, "XTEST presses the backspaces");
        check(host.pressSystemKeys(-2) && sent == std::vector<int>{3, -2}, "XTEST selects with Shift+Left");
        setXTestSenderForTest({});
    }

    // Under Xwayland only apps the core marks as taking sent key events get them.
    void testXSend() {
        IBusEngine       engine{};
        IBusHost         host(&engine);
        std::vector<int> sent;
        setXSendSenderForTest([&sent](int count) {
            sent.push_back(count);
            return true;
        });
        host.setClient("qt5-im:wps");
        check(host.pressSystemKeys(3) && sent == std::vector<int>{3}, "an app that takes sent keys gets them under Xwayland");
        sent.clear();
        host.setClient("gtk3-im:gedit");
        check(!host.pressSystemKeys(3) && sent.empty(), "other apps under Xwayland get no sent keys");
        setXSendSenderForTest({});
    }

    // GNOME 50.0 to 50.3 drop forwarded keys whatever the typing mode, so deletions go through the text.
    void testShellFields() {
        IBusEngine engine{};
        engine.client_capabilities = IBUS_CAP_PREEDIT_TEXT | IBUS_CAP_SURROUNDING_TEXT;
        IBusHost host(&engine);
        host.setDirectTyping(false);
        host.setClient("gnome-shell");
        check(host.field().sendsNoKeys && host.field().surroundingText, "preedit mode through GNOME Shell sends no keys");
        host.setClient("gtk3-im:gedit");
        check(!host.field().sendsNoKeys, "an X11 app in preedit mode still forwards");
    }
} // namespace

int main() {
    // The real X senders stay unused, so only the recorders above take keys.
    unsetenv("DISPLAY");
    unsetenv("WAYLAND_DISPLAY");
    testXTest();
    testXSend();
    testShellFields();
    if (failures == 0)
        std::cout << "all host checks passed\n";
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
