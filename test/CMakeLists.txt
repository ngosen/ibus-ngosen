add_executable(ibus-config-test ibus-config.cpp)
target_link_libraries(ibus-config-test PRIVATE ngosen_ibus)
add_test(NAME ibus_config COMMAND ibus-config-test)
set_tests_properties(ibus_config PROPERTIES LABELS "unit;ibus")

add_test(NAME install_environment COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/install-environment.sh ${PROJECT_BINARY_DIR})
set_tests_properties(install_environment PROPERTIES LABELS "unit")

# The engine runs in its own process under ibus-daemon, so it is tested through a real daemon.
option(NGOSEN_IBUS_DAEMON_TESTS "Test the engine through ibus-daemon" ON)
if (NOT NGOSEN_IBUS_DAEMON_TESTS)
    return()
endif()

find_program(IBUS_DAEMON ibus-daemon)
find_program(DBUS_RUN_SESSION dbus-run-session)
find_program(XVFB Xvfb)
find_package(Python3 COMPONENTS Interpreter)
if (IBUS_DAEMON AND DBUS_RUN_SESSION AND XVFB AND Python3_FOUND)
    execute_process(COMMAND ${Python3_EXECUTABLE} -c "import ctypes, gi; ctypes.CDLL('libXtst.so.6'); gi.require_version('IBus', '1.0'); from gi.repository import IBus"
                    RESULT_VARIABLE NGOSEN_HAVE_PYTHON_IBUS OUTPUT_QUIET ERROR_QUIET)
endif()
if (NOT (IBUS_DAEMON AND DBUS_RUN_SESSION AND XVFB AND NGOSEN_HAVE_PYTHON_IBUS EQUAL 0))
    message(FATAL_ERROR "The engine tests need ibus-daemon, dbus-run-session, Xvfb, libXtst and python3-gi with IBus; "
                        "install them or pass -DNGOSEN_IBUS_DAEMON_TESTS=OFF")
endif()

set(NGOSEN_IBUS_EXEC $<TARGET_FILE:ibus-engine-ngosen>)
set(NGOSEN_IBUS_ICON "")
set(component_dir ${CMAKE_CURRENT_BINARY_DIR}/component)
configure_file(${PROJECT_SOURCE_DIR}/data/ngosen.xml.in ${CMAKE_CURRENT_BINARY_DIR}/ngosen.xml.in @ONLY)
file(GENERATE OUTPUT ${component_dir}/ngosen.xml INPUT ${CMAKE_CURRENT_BINARY_DIR}/ngosen.xml.in)

add_test(NAME ibus_daemon_typing
         COMMAND ${DBUS_RUN_SESSION} -- sh ${CMAKE_CURRENT_SOURCE_DIR}/run-with-daemon.sh ${Python3_EXECUTABLE} ${component_dir}
                 ${PROJECT_SOURCE_DIR}/ngosen/data/dictionaries/vietnamese.cm.dict ${CMAKE_CURRENT_SOURCE_DIR}/ibus-daemon-typing.py)
set_tests_properties(ibus_daemon_typing PROPERTIES LABELS "integration;ibus" TIMEOUT 120
                     ENVIRONMENT "NGOSEN_IBUS_LOCALEDIR=${PROJECT_BINARY_DIR}/po/locale;LC_ALL=en_US.UTF-8")

add_test(NAME ibus_daemon_typing_no_clicks
         COMMAND ${DBUS_RUN_SESSION} -- sh ${CMAKE_CURRENT_SOURCE_DIR}/run-with-daemon.sh ${Python3_EXECUTABLE} ${component_dir}
                 ${PROJECT_SOURCE_DIR}/ngosen/data/dictionaries/vietnamese.cm.dict ${CMAKE_CURRENT_SOURCE_DIR}/ibus-daemon-typing.py)
set_tests_properties(ibus_daemon_typing_no_clicks PROPERTIES LABELS "integration;ibus" TIMEOUT 120
                     ENVIRONMENT "NGOSEN_IBUS_LOCALEDIR=${PROJECT_BINARY_DIR}/po/locale;LC_ALL=en_US.UTF-8;NGOSEN_TEST_NO_X=1")
