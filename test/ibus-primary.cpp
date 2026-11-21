/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-primary.h"

#include <arpa/inet.h>
#include <chrono>
#include <cstdlib>
#include <dirent.h>
#include <iostream>
#include <netinet/in.h>
#include <string>
#include <sys/socket.h>
#include <unistd.h>

namespace {

    // An X server that takes the connection and never answers, as a stalled Xwayland does.
    int silentServer(int& display) {
        const int   fd    = socket(AF_INET, SOCK_STREAM, 0);
        sockaddr_in a     = {};
        a.sin_family      = AF_INET;
        a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        for (display = 70; display < 200; ++display) {
            a.sin_port = htons(static_cast<uint16_t>(6000 + display));
            if (bind(fd, reinterpret_cast<sockaddr*>(&a), sizeof a) == 0 && listen(fd, 4) == 0)
                return fd;
        }
        return -1;
    }

    int countThreads() {
        int count = 0;
        if (DIR* tasks = opendir("/proc/self/task")) {
            while (const dirent* entry = readdir(tasks))
                count += entry->d_name[0] != '.';
            closedir(tasks);
        }
        return count;
    }

} // namespace

int main() {
    int       display = 0;
    const int server  = silentServer(display);
    if (server < 0) {
        std::cout << "SKIP no free port for a fake X server\n";
        return 0;
    }
    setenv("DISPLAY", ("127.0.0.1:" + std::to_string(display)).c_str(), 1);
    const auto        start  = std::chrono::steady_clock::now();
    const std::string text   = ngosen::readPrimarySelection(200);
    const auto        waited = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count();
    if (!text.empty() || waited > 1000) {
        std::cout << "FAIL an X server that never answers holds the engine for " << waited << " ms\n";
        _exit(1);
    }
    // Pressing the key again while that read is stuck must not start another one.
    for (int i = 0; i < 5; ++i)
        ngosen::readPrimarySelection(50);
    if (const int threads = countThreads(); threads > 2) {
        std::cout << "FAIL every read stuck on the server keeps a thread: " << threads << " threads\n";
        _exit(1);
    }
    // The reading thread is still stuck on the silent server; leave without waiting for it.
    _exit(0);
}
