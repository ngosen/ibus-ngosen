Name:           ibus-ngosen
Version:        1.6.3
Release:        1
Summary:        Ngó Sen, a Vietnamese input method for IBus
License:        GPL-3.0-or-later AND LGPL-2.1-or-later AND MIT AND GPL-2.0-or-later
URL:            https://github.com/ngosen/ibus-ngosen
# Release tarballs carry the ngosen submodule, which GitHub's own archives leave out.
Source0:        %{url}/releases/download/%{name}-%{version}-1/%{name}-%{version}.tar.gz

BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  cargo
BuildRequires:  rust >= 1.88
BuildRequires:  pkgconfig(ibus-1.0) >= 1.5.27
BuildRequires:  python3
BuildRequires:  gettext-tools

Requires:       ibus >= 1.5.27
# Both install the forward-keys extension of the same name.
Conflicts:      fcitx5-ngosen
# Loaded with dlopen on X11 to watch clicks and press keys, which the automatic requires miss.
Requires:       libxcb1
Requires:       libxcb-xtest0
Requires:       libxcb-xinput0
# Loaded with dlopen on Wayland to read the primary selection.
Requires:       libwayland-client0
Requires:       python3-gobject
# The settings window loads these through GObject introspection, which the automatic requires miss.
Requires:       typelib(Gtk) = 4.0
Requires:       typelib(Adw) = 1
Requires:       typelib(PangoCairo) = 1.0
Requires:       libadwaita-1-0 >= 1.5

%description
Ngó Sen types Vietnamese through IBus, the input method GNOME comes
with. It types straight into apps that report the text around the cursor and
underlines the word being typed elsewhere; the typing mode can be picked for
each app. A tap of Ctrl+Shift switches between English and Vietnamese.

%prep
%setup -q

%build
# The daemon tests need a session bus and ibus-daemon; CI runs them on every pull request.
%cmake -DNGOSEN_IBUS_DAEMON_TESTS:BOOL=OFF
%cmake_build

%install
%cmake_install
%find_lang %{name}

%check
%ctest

%files -f %{name}.lang
%license LICENSE
%{_libexecdir}/ibus-engine-ngosen
%{_libexecdir}/ibus-setup-ngosen
%{_bindir}/ngosen-check
%{_bindir}/ngosen-save-log
%{_bindir}/ngosen-toggle
%{_datadir}/ibus/component/ngosen.xml
%{_datadir}/ibus-ngosen/
%{_datadir}/gnome-shell/extensions/forward-keys@ngosen.github.io/
%{_datadir}/applications/ibus-setup-ngosen.desktop
%{_datadir}/metainfo/io.github.ngosen.IBusNgoSen.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/ibus-ngosen.svg
%{_datadir}/icons/hicolor/scalable/apps/io.github.ngosen.IBusNgoSen.svg
%{_prefix}/lib/environment.d/60-ibus-ngosen.conf
%config(noreplace) %{_sysconfdir}/profile.d/ibus-ngosen.sh

%changelog
* Thu Nov 26 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.6.3-1
- In Chrome's rich text editors on GNOME, such as a forum reply box, a corrected word
  is no longer lost now and then when the editor comes back to focus only briefly. In
  WPS Office 12, adding a mark no longer keeps the old letters, and spreadsheet cells
  keep it.
- Core ngosen-1.14.3-1.

* Thu Nov 26 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.6.2-1
- In Chrome's rich text editors on GNOME, such as a forum reply box, a finished word
  keeps its tone mark after a Backspace, and fast typing no longer loses letters while
  the editor drops and retakes focus.
- Core ngosen-1.14.2-1.
* Wed Nov 25 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.6.1-1
- Emoji suggestions are off by default; turn them on per app with w in the ` menu;
  a slow Ctrl+Shift tap, held up to a second, still switches the mode; packages for
  Fedora 45.
- Core ngosen-1.14.1-1.

* Sun Nov 22 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.6.0-1
- In the underline mode, a selected word takes a new tone mark in GTK 4 apps and Chrome;
  no emoji suggestions for single letters, digits and chat shorthand; the convert key
  changes selected text on KDE, Sway and Hyprland; KDE Plasma shows the emoji row's
  numbers once; ngosen-check and ngosen-save-log commands; Spell Check is gone.
- Core ngosen-1.14.0-1.

* Sun Nov 22 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.5.1-1
- xterm types right with Backspace on Wayland and X11; learned xterm.js terminals are
  remembered across restarts; fields of apps without a name keep
  their per-field choices; the convert key points to the Convert page when an app gives no
  selected text; the edition is named Ngó Sen for IBus; core ngosen-1.13.2-1.

* Sat Nov 21 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.5.0-1
- Emoji while typing, with an Emoji page to edit, export and import keywords; convert
  selected text from TCVN3, VNI and other charsets in place; the switch key changes every
  app at once, and a new ngosen-toggle command switches from a desktop shortcut; teencode
  for chosen apps and drawn-out letters; core ngosen-1.13.1-1.

* Wed Nov 18 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.4.1-1
- Fast typing with Backspace right after Firefox opens on GNOME no longer loses a Backspace
  or mixes up letters; a tone retyped after a final consonant gives the right word; Brave
  on GNOME keeps its tones; the mode menu closes as in the fcitx5 edition; three settings
  labels drop "(experimental)"; core ngosen-1.12.2-1.

* Mon Nov 16 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.4.0-1
- Extra keys after a Vietnamese word no longer undo its marks; Space drops them, splits off
  a word or reads g as ng; Space keeps stretched words; core fixes for Firefox, web sheets
  and busy apps on GNOME; the Check tab reads the session's input method and the IBus
  engine list outside GNOME; words such as rose show as typed and the lock key swaps them;
  Backspace while a slow GNOME app reports keeps the marks; the IBus tray shows V or E and
  the menu's language item switches the app typed in last; core ngosen-1.11.2-1.

* Thu Nov 12 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.3.0-1
- Ctrl+Shift and OFF switch English and Vietnamese for the app in use only; Vim mode for each
  app; words starting with / stay as typed; Telex words with a forgotten circumflex or horn
  come out right; the mode menu can be set up; settings search and What's new; retype on
  Wayland; core ngosen-1.10.0-1.

* Wed Nov 11 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.2.3-1
- Words that start with a capital typed with Shift keep their marks in Sen; Enter after an
  underlined word retones it and expands its macro, as a space does; core ngosen-1.9.3-1.

* Tue Nov 10 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.2.2-1
- Sen types straight into every app, as the fcitx5 edition does, Electron apps, Chrome and
  terminals on X11 included; the mode menu picks the underline for one app. The option is now
  "Type with Sen". The icon and logo match the fcitx5 edition; the settings window shows whole
  values; core ngosen-1.9.0-1.

* Mon Nov 09 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.2.1-1
- On GNOME the engine removes the duplicate English (US) input source once and always types on
  the US layout.
- Sen types straight into the Chrome and Chromium address bar, as the fcitx5 edition does.
- Settings window: pages in a sidebar, About moves to the main menu, and the Check page reports
  what holds the input method and the forward-keys extension correctly; it also finds and
  removes what the fcitx5 installer left unchanged; backups record their edition; core
  ngosen-1.9.0-1.

* Mon Nov 09 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.2.0-1
- Sen is the default and remembers the mode picked for each app; Ctrl+Shift switches Vietnamese
  and English; retype, retone, macros in English, backup and restore, the keymap editor, the mode
  menu and a Check my machine page, as in fcitx5-ngosen; core ngosen-1.9.0-1.

* Sun Nov 08 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.1.4-1
- Typing with Sen on GNOME erases with BackSpace when the app's copy is stale, with an extension
  for GNOME 50.0-50.3; conflicts with fcitx5-ngosen; core ngosen-1.8.1-1.

* Sun Nov 01 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.1.3-1
- Typing with Sen runs on the core and types into X11 apps, tone keys typed together kept on GNOME,
  kitty on X11, marked on/off items in the menu, core ngosen-1.7.5-1.

* Fri Oct 30 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.1.2-1
- Stop resending unchanged menu items on focus changes, which stalled GNOME Shell on X11.

* Thu Oct 29 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.1.1-1
- Address bars type with the preedit when typing with Sen is on, Save typing log in the menu.

* Thu Oct 29 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.1.0-1
- New icon, Super+Space fix on GNOME 46, Backspace reopens the last word, core ngosen-1.7.0-1.

* Tue Oct 27 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.0.0-1
- First release.
