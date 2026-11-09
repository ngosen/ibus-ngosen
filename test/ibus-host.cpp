/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-host.h"
#include "ngosen-ibus-shell.h"
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

    // GNOME 50.0 to 50.3 drop forwarded keys whatever the typing mode, so with the underline an edit of
    // committed text goes through the text the Shell reports, and a terminal erases with DEL.
    void testShellFields() {
        IBusEngine engine{};
        engine.client_capabilities = IBUS_CAP_PREEDIT_TEXT | IBUS_CAP_SURROUNDING_TEXT;
        IBusHost host(&engine);
        host.setDirectTyping(false);
        host.setClient("gnome-shell");
        host.setReportedText("xin chao", 8, 8);
        setShellDeliversKeysForTest(false);
        check(host.field().sendsNoKeys && host.field().surroundingText, "preedit mode through a GNOME Shell that drops keys deletes through the text");
        check(host.surrounding().text() == "xin chao", "preedit mode through GNOME Shell reads the text the Shell reported");
        host.setContentType(IBUS_INPUT_PURPOSE_TERMINAL, IBUS_INPUT_HINT_NONE);
        check(host.field().sendsNoKeys && !host.field().surroundingText, "a terminal through a GNOME Shell that drops keys erases with DEL");
        host.setContentType(IBUS_INPUT_PURPOSE_FREE_FORM, IBUS_INPUT_HINT_NONE);
        setShellDeliversKeysForTest(true);
        check(!host.field().sendsNoKeys && host.field().surroundingText, "preedit mode through a GNOME Shell that delivers keys forwards them");
        setShellDeliversKeysForTest(false);
        host.setClient("gtk3-im:gedit");
        check(!host.field().sendsNoKeys, "another client in preedit mode still forwards keys");
    }

    // As in the fcitx5 edition, an address bar types straight in and the core guards its completion.
    void testShellAddressBar() {
        IBusEngine engine{};
        engine.client_capabilities = IBUS_CAP_PREEDIT_TEXT | IBUS_CAP_SURROUNDING_TEXT;
        IBusHost host(&engine);
        host.setDirectTyping(true);
        host.setClient("gnome-shell");
        host.setReportedText("xin", 3, 3);
        host.setContentType(IBUS_INPUT_PURPOSE_URL, IBUS_INPUT_HINT_NONE);
        setShellDeliversKeysForTest(true);
        check(host.field().url && !host.field().sendsNoKeys && host.field().surroundingText, "Sen in an address bar through GNOME Shell forwards keys");
        setShellDeliversKeysForTest(false);
        check(host.field().sendsNoKeys && host.field().preeditFallback, "an address bar through a GNOME Shell that drops keys keeps the preedit");
    }

    bool samePage(const std::optional<CandidatePage>& page, int pageNumber, int cursor, bool hasPrev, bool hasNext) {
        return page && page->total == 10 && page->pageSize == 4 && page->page == pageNumber && page->cursor == cursor && page->hasPrev == hasPrev && page->hasNext == hasNext;
    }

    // The core pages and picks through the host, as with the fcitx5 candidate list.
    void testCandidates() {
        IBusEngine          engine{};
        IBusHost            host(&engine);
        std::vector<size_t> picked;
        host.showCandidates({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}, 4, [&picked](size_t index) { picked.push_back(index); });
        check(samePage(host.candidates(), 0, 0, false, true), "a shown list starts on its first page with the first highlighted");
        host.prevCandidatePage();
        check(samePage(host.candidates(), 0, 0, false, true), "the page before the first is the first");
        host.nextCandidatePage();
        check(samePage(host.candidates(), 1, 4, true, true), "the next page highlights its first candidate");
        host.highlightCandidate(9);
        check(samePage(host.candidates(), 2, 9, true, false), "the last candidate is on the last page");
        host.pickCandidate(7);
        check(picked == std::vector<size_t>{7}, "a pick calls back with the index picked");

        picked.clear();
        host.showCandidates({"a", "b"}, 1, [&](size_t index) {
            picked.push_back(index);
            host.hideCandidates();
        });
        host.pickCandidate(1);
        check(picked == std::vector<size_t>{1} && !host.candidates(), "a pick that hides the list calls back once");

        picked.clear();
        host.showCandidates({"a"}, 1, [&picked](size_t index) { picked.push_back(index); });
        host.resetPanel();
        check(!host.candidates(), "resetPanel hides the list");
        host.pickCandidate(0);
        check(picked.empty(), "a pick after resetPanel calls nothing");

        host.showCandidates(std::vector<std::string>(20, "a"), 20, {});
        check(host.candidates() && host.candidates()->pageSize == 16, "a page is at most the 16 IBus can show");
    }

    void testWaylandSession() {
        const auto session = [](const char* type, const char* display) {
            type != nullptr ? setenv("XDG_SESSION_TYPE", type, 1) : unsetenv("XDG_SESSION_TYPE");
            display != nullptr ? setenv("WAYLAND_DISPLAY", display, 1) : unsetenv("WAYLAND_DISPLAY");
            return isWaylandSession();
        };
        check(session("wayland", nullptr), "a Wayland session");
        check(session(nullptr, "wayland-0"), "a daemon started by hand on Wayland");
        check(session("", "wayland-0"), "an empty session type");
        check(!session("x11", "wayland-0"), "a leftover WAYLAND_DISPLAY on X11");
        check(!session(nullptr, nullptr), "no session");
        unsetenv("XDG_SESSION_TYPE");
        unsetenv("WAYLAND_DISPLAY");
    }
} // namespace

int main() {
    // The real X senders stay unused, so only the recorders above take keys.
    unsetenv("DISPLAY");
    unsetenv("WAYLAND_DISPLAY");
    testXTest();
    testXSend();
    testShellFields();
    testShellAddressBar();
    testCandidates();
    testWaylandSession();
    if (failures == 0)
        std::cout << "all host checks passed\n";
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
