find_package(PkgConfig REQUIRED)
pkg_check_modules(IBus REQUIRED IMPORTED_TARGET ibus-1.0>=1.5.27)

add_library(ngosen_ibus STATIC
    ngosen-ibus-engine.cpp
    ngosen-ibus-host.cpp
    ngosen-ibus-log.cpp
    ngosen-ibus-resources.cpp
)
target_include_directories(ngosen_ibus PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_definitions(ngosen_ibus PRIVATE NGOSEN_IBUS_DICTIONARY="${NGOSEN_IBUS_DATADIR}/vietnamese.cm.dict")
target_link_libraries(ngosen_ibus PUBLIC ngosen_core PkgConfig::IBus)

add_executable(ibus-engine-ngosen main.cpp)
target_compile_definitions(ibus-engine-ngosen PRIVATE NGOSEN_IBUS_VERSION="${PROJECT_VERSION}")
target_link_libraries(ibus-engine-ngosen PRIVATE ngosen_ibus)

install(TARGETS ibus-engine-ngosen DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})
