find_program(MSGFMT msgfmt REQUIRED)

file(STRINGS LINGUAS languages REGEX "^[^#]")
foreach(language IN LISTS languages)
    # Laid out as installed, so the engine tests can read it from the build tree.
    set(dir ${CMAKE_CURRENT_BINARY_DIR}/locale/${language}/LC_MESSAGES)
    set(mo ${dir}/ibus-ngosen.mo)
    add_custom_command(OUTPUT ${mo} COMMAND ${CMAKE_COMMAND} -E make_directory ${dir}
                       COMMAND ${MSGFMT} --check -o ${mo} ${CMAKE_CURRENT_SOURCE_DIR}/${language}.po DEPENDS ${language}.po)
    list(APPEND catalogs ${mo})
    install(FILES ${mo} DESTINATION ${CMAKE_INSTALL_LOCALEDIR}/${language}/LC_MESSAGES)
endforeach()
add_custom_target(translations ALL DEPENDS ${catalogs})

add_test(NAME translations COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/misc/check-translations.py)
