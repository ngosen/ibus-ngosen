find_package(PkgConfig REQUIRED)
pkg_check_modules(IBus REQUIRED IMPORTED_TARGET ibus-1.0>=1.5.27)

add_library(ngosen_ibus STATIC
    ngosen-ibus-config.cpp
    ngosen-ibus-engine.cpp
    ngosen-ibus-host.cpp
    ngosen-ibus-log.cpp
    ngosen-ibus-menu.cpp
    ngosen-ibus-resources.cpp
    ngosen-ibus-typing-log.cpp
)
target_include_directories(ngosen_ibus PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_definitions(ngosen_ibus PUBLIC GETTEXT_PACKAGE="ibus-ngosen" NGOSEN_IBUS_VERSION="${PROJECT_VERSION}")
target_compile_definitions(ngosen_ibus PRIVATE NGOSEN_IBUS_DICTIONARY="${NGOSEN_IBUS_DATADIR}/vietnamese.cm.dict"
                                               NGOSEN_SETUP_EXEC="${NGOSEN_SETUP_EXEC}")
target_link_libraries(ngosen_ibus PUBLIC ngosen_core PkgConfig::IBus)

add_executable(ibus-engine-ngosen main.cpp)
target_compile_definitions(ibus-engine-ngosen PRIVATE NGOSEN_LOCALEDIR="${CMAKE_INSTALL_FULL_LOCALEDIR}")
target_link_libraries(ibus-engine-ngosen PRIVATE ngosen_ibus)

install(TARGETS ibus-engine-ngosen DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})
