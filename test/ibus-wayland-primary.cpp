/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-data-control.h"
#include "ngosen-ibus-primary.h"

#include <wayland-server-core.h>
#include <wayland-server-protocol.h>

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>
#include <unistd.h>
#include <vector>

namespace {

    int  failures = 0;

    void check(bool ok, const std::string& what, const std::string& got) {
        if (!ok) {
            std::cout << "FAIL " << what << ": got \"" << got << "\"\n";
            ++failures;
        }
    }

    const wl_interface* wl(const ngosen::wayland::Interface* interface) {
        return reinterpret_cast<const wl_interface*>(interface);
    }

    // A compositor with a seat and, unless told otherwise, a data-control manager whose primary
    // selection is `text`, as KDE offers it while an app has text selected.
    struct FakeCompositor {
        const ngosen::wayland::DataControl* protocol = nullptr;
        std::string                         text;
        bool                                answers = true;
        wl_display*                         display = wl_display_create();
        std::vector<int>                    heldFds;
        std::atomic<bool>                   stop = false;
        std::thread                         loop;

        FakeCompositor(const ngosen::wayland::DataControl* p, std::string t, bool a, const std::string& socket) : protocol(p), text(std::move(t)), answers(a) {
            wl_display_add_socket(display, socket.c_str());
            wl_global_create(display, &wl_seat_interface, 1, nullptr,
                             [](wl_client* c, void*, uint32_t v, uint32_t id) { wl_resource_create(c, &wl_seat_interface, static_cast<int>(v), id); });
            if (protocol)
                wl_global_create(display, wl(protocol->manager), protocol->manager->version, this, bindManager);
            loop = std::thread([this] {
                wl_event_loop* events = wl_display_get_event_loop(display);
                while (!stop) {
                    wl_event_loop_dispatch(events, 20);
                    wl_display_flush_clients(display);
                }
            });
        }

        ~FakeCompositor() {
            stop = true;
            loop.join();
            for (int fd : heldFds)
                close(fd);
            wl_display_destroy_clients(display);
            wl_display_destroy(display);
        }

        static void bindManager(wl_client* client, void* data, uint32_t version, uint32_t id) {
            static const void* const requests[] = {
                reinterpret_cast<const void*>(+[](wl_client*, wl_resource*, uint32_t) {}),
                reinterpret_cast<const void*>(+[](wl_client* c, wl_resource* manager, uint32_t id, wl_resource*) {
                    auto* self = static_cast<FakeCompositor*>(wl_resource_get_user_data(manager));
                    self->offerPrimary(c, wl_resource_get_version(manager), id);
                }),
                reinterpret_cast<const void*>(+[](wl_client*, wl_resource* r) { wl_resource_destroy(r); }),
            };
            wl_resource* manager = wl_resource_create(client, wl(static_cast<FakeCompositor*>(data)->protocol->manager), static_cast<int>(version), id);
            wl_resource_set_implementation(manager, requests, data, nullptr);
        }

        void offerPrimary(wl_client* client, int version, uint32_t id) {
            static const void* const deviceRequests[] = {
                reinterpret_cast<const void*>(+[](wl_client*, wl_resource*, wl_resource*) {}),
                reinterpret_cast<const void*>(+[](wl_client*, wl_resource* r) { wl_resource_destroy(r); }),
                reinterpret_cast<const void*>(+[](wl_client*, wl_resource*, wl_resource*) {}),
            };
            static const void* const offerRequests[] = {
                reinterpret_cast<const void*>(+[](wl_client*, wl_resource* offer, const char*, int32_t fd) {
                    auto* self = static_cast<FakeCompositor*>(wl_resource_get_user_data(offer));
                    if (!self->answers) {
                        self->heldFds.push_back(fd);
                        return;
                    }
                    (void)!write(fd, self->text.data(), self->text.size());
                    close(fd);
                }),
                reinterpret_cast<const void*>(+[](wl_client*, wl_resource* r) { wl_resource_destroy(r); }),
            };
            wl_resource* device = wl_resource_create(client, wl(protocol->device), version, id);
            wl_resource_set_implementation(device, deviceRequests, this, nullptr);
            wl_resource* offer = wl_resource_create(client, wl(protocol->offer), version, 0);
            wl_resource_set_implementation(offer, offerRequests, this, nullptr);
            wl_resource_post_event(device, ngosen::wayland::op::DeviceDataOffer, offer);
            wl_resource_post_event(offer, ngosen::wayland::op::OfferOffer, "text/plain;charset=utf-8");
            wl_resource_post_event(device, ngosen::wayland::op::DeviceSelection, nullptr);
            wl_resource_post_event(device, ngosen::wayland::op::DevicePrimarySelection, offer);
        }
    };

    std::string read(int timeoutMs) {
        return ngosen::readPrimarySelection(timeoutMs);
    }

} // namespace

int main() {
    char folder[] = "/tmp/ngosen-wayland-XXXXXX";
    if (!mkdtemp(folder)) {
        std::cout << "SKIP no folder for a fake compositor\n";
        return 0;
    }
    setenv("XDG_RUNTIME_DIR", folder, 1);
    unsetenv("DISPLAY");

    {
        FakeCompositor kde(&ngosen::wayland::extDataControl, "việt", true, "wayland-ext");
        setenv("WAYLAND_DISPLAY", "wayland-ext", 1);
        const std::string got = read(500);
        check(got == "việt", "reads the primary selection over ext-data-control", got);
    }
    {
        FakeCompositor sway(&ngosen::wayland::wlrDataControl, "việt", true, "wayland-wlr");
        setenv("WAYLAND_DISPLAY", "wayland-wlr", 1);
        const std::string got = read(500);
        check(got == "việt", "reads the primary selection over wlr-data-control", got);
    }
    {
        FakeCompositor gnome(nullptr, "", true, "wayland-none");
        setenv("WAYLAND_DISPLAY", "wayland-none", 1);
        const auto got = ngosen::readWaylandPrimarySelection(500);
        check(!got.has_value(), "a compositor without data-control leaves the reading to X11", got.value_or("(none)"));
    }
    {
        FakeCompositor stuck(&ngosen::wayland::extDataControl, "việt", false, "wayland-stuck");
        setenv("WAYLAND_DISPLAY", "wayland-stuck", 1);
        const auto        start  = std::chrono::steady_clock::now();
        const std::string got    = read(200);
        const auto        waited = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count();
        check(got.empty() && waited < 1000, "an app that never sends its selection holds the engine " + std::to_string(waited) + " ms", got);
    }
    rmdir(folder);
    if (failures == 0)
        std::cout << "PASS\n";
    return failures == 0 ? 0 : 1;
}
