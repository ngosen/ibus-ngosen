set(NGOSEN_IBUS_ICON "${CMAKE_INSTALL_FULL_DATADIR}/icons/hicolor/scalable/apps/ibus-ngosen.svg")
configure_file(ngosen.xml.in ${CMAKE_CURRENT_BINARY_DIR}/ngosen.xml @ONLY)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/ngosen.xml DESTINATION ${CMAKE_INSTALL_DATADIR}/ibus/component)
# The fcitx5 edition's icons, taken from the core so both editions keep one look.
set(core_icons ${PROJECT_SOURCE_DIR}/ngosen/data/icons/hicolor/scalable/apps)
install(FILES ${core_icons}/fcitx-ngosen.svg DESTINATION ${CMAKE_INSTALL_DATADIR}/icons/hicolor/scalable/apps
        RENAME ibus-ngosen.svg)
install(FILES ${core_icons}/io.github.ngosen.NgoSen.Settings.svg
        DESTINATION ${CMAKE_INSTALL_DATADIR}/icons/hicolor/scalable/apps RENAME io.github.ngosen.IBusNgoSen.svg)
install(FILES ${PROJECT_SOURCE_DIR}/ngosen/data/dictionaries/vietnamese.cm.dict
              ${PROJECT_SOURCE_DIR}/ngosen/data/dictionaries/LICENSE.vietnamese.cm.dict
              ${PROJECT_SOURCE_DIR}/ngosen/data/english-common.txt
              ${PROJECT_SOURCE_DIR}/ngosen/data/english-common.txt.license
        DESTINATION ${CMAKE_INSTALL_DATADIR}/ibus-ngosen)
# systemd reads environment.d from /usr/lib on every distro, whatever the libdir.
install(FILES 60-ibus-ngosen.conf DESTINATION lib/environment.d)
# LightDM sessions (Cinnamon, Xfce, MATE) do not take the systemd user environment.
install(FILES ibus-ngosen.sh DESTINATION ${CMAKE_INSTALL_FULL_SYSCONFDIR}/profile.d)
