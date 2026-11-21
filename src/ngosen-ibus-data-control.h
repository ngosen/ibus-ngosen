/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

// The Wayland data-control protocols, in the layout libwayland reads (struct wl_message and struct
// wl_interface), so the engine needs neither the Wayland headers to build nor libwayland to run.

namespace ngosen::wayland {

    struct Interface;

    struct Message {
        const char*       name;
        const char*       signature;
        const Interface** types;
    };

    struct Interface {
        const char*    name;
        int            version;
        int            methodCount;
        const Message* methods;
        int            eventCount;
        const Message* events;
    };

    // One protocol: ext-data-control-v1 or the older wlr-data-control-unstable-v1.
    struct DataControl {
        const Interface* manager;
        const Interface* device;
        const Interface* offer;
        int              primaryVersion; // the first version with the primary selection
    };

    extern const DataControl extDataControl;
    extern const DataControl wlrDataControl;

    // Request and event numbers, the same in both protocols.
    namespace op {
        constexpr int ManagerGetDataDevice   = 1;
        constexpr int ManagerDestroy         = 2;
        constexpr int DeviceDestroy          = 1;
        constexpr int OfferReceive           = 0;
        constexpr int OfferDestroy           = 1;
        constexpr int DisplayGetRegistry     = 1;
        constexpr int RegistryBind           = 0;
        constexpr int DeviceDataOffer        = 0;
        constexpr int DeviceSelection        = 1;
        constexpr int DeviceFinished         = 2;
        constexpr int DevicePrimarySelection = 3;
        constexpr int OfferOffer             = 0;
    } // namespace op

} // namespace ngosen::wayland
