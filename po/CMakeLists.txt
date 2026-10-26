find_program(MSGFMT msgfmt REQUIRED)

file(STRINGS LINGUAS languages REGEX "^[^#]")
foreach(language IN LISTS languages)
    set(mo ${CMAKE_CURRENT_BINARY_DIR}/${language}.mo)
    add_custom_command(OUTPUT ${mo} COMMAND ${MSGFMT} --check -o ${mo} ${CMAKE_CURRENT_SOURCE_DIR}/${language}.po
                       DEPENDS ${language}.po)
    list(APPEND catalogs ${mo})
    install(FILES ${mo} DESTINATION ${CMAKE_INSTALL_LOCALEDIR}/${language}/LC_MESSAGES RENAME ibus-ngosen.mo)
endforeach()
add_custom_target(translations ALL DEPENDS ${catalogs})

add_test(NAME translations COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/misc/check-translations.py)
