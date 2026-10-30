cmake_minimum_required(VERSION 3.16)

project(ibus-ngosen VERSION 1.1.2 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
include(GNUInstallDirs)

if (NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/ngosen/src/core/CMakeLists.txt")
    message(FATAL_ERROR "The typing logic is missing; run: git submodule update --init")
endif()

# The submodule's own option() predates CMP0077, so only a cache entry reaches it.
set(NGOSEN_CORE_ONLY ON CACHE BOOL "Build the typing logic without fcitx5" FORCE)
enable_testing()
add_subdirectory(ngosen)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(NGOSEN_IBUS_DATADIR "${CMAKE_INSTALL_FULL_DATADIR}/ibus-ngosen")
set(NGOSEN_IBUS_EXEC "${CMAKE_INSTALL_FULL_LIBEXECDIR}/ibus-engine-ngosen")
set(NGOSEN_SETUP_EXEC "${CMAKE_INSTALL_FULL_LIBEXECDIR}/ibus-setup-ngosen")
add_subdirectory(src)
add_subdirectory(data)
add_subdirectory(settings)
add_subdirectory(po)
add_subdirectory(test)
