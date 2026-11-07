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
} // namespace

int main() {
    // The real X senders stay unused, so only the recorders above take keys.
    unsetenv("DISPLAY");
    unsetenv("WAYLAND_DISPLAY");
    testXTest();
    testXSend();
    if (failures == 0)
        std::cout << "all host checks passed\n";
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
