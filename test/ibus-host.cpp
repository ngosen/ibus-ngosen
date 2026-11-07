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
} // namespace

int main() {
    // The real X senders stay unused, so only the recorders above take keys.
    unsetenv("DISPLAY");
    unsetenv("WAYLAND_DISPLAY");
    testXTest();
    testXSend();
    testCandidates();
    if (failures == 0)
        std::cout << "all host checks passed\n";
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
