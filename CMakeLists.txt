cmake_minimum_required(VERSION 3.16)

project(ibus-ngosen VERSION 1.0.0 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if (NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/ngosen/src/core/CMakeLists.txt")
    message(FATAL_ERROR "The typing logic is missing; run: git submodule update --init")
endif()

# The submodule's own option() predates CMP0077, so only a cache entry reaches it.
set(NGOSEN_CORE_ONLY ON CACHE BOOL "Build the typing logic without fcitx5" FORCE)
enable_testing()
add_subdirectory(ngosen)
