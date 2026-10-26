set(NGOSEN_IBUS_ICON "${CMAKE_INSTALL_FULL_DATADIR}/icons/hicolor/scalable/apps/ibus-ngosen.svg")
configure_file(ngosen.xml.in ${CMAKE_CURRENT_BINARY_DIR}/ngosen.xml @ONLY)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/ngosen.xml DESTINATION ${CMAKE_INSTALL_DATADIR}/ibus/component)
install(FILES icons/ibus-ngosen.svg DESTINATION ${CMAKE_INSTALL_DATADIR}/icons/hicolor/scalable/apps)
install(FILES icons/ibus-ngosen.svg DESTINATION ${CMAKE_INSTALL_DATADIR}/icons/hicolor/scalable/apps
        RENAME io.github.ngosen.IBusNgoSen.svg)
install(FILES ${PROJECT_SOURCE_DIR}/ngosen/data/dictionaries/vietnamese.cm.dict
              ${PROJECT_SOURCE_DIR}/ngosen/data/dictionaries/LICENSE.vietnamese.cm.dict
        DESTINATION ${CMAKE_INSTALL_DATADIR}/ibus-ngosen)
