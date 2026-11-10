Name:           ibus-ngosen
Version:        1.2.2
Release:        1
Summary:        Ngó Sen for GNOME, a Vietnamese input method for IBus
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
Requires:       python3-gobject
# The settings window loads these through GObject introspection, which the automatic requires miss.
Requires:       typelib(Gtk) = 4.0
Requires:       typelib(Adw) = 1
Requires:       typelib(PangoCairo) = 1.0
Requires:       libadwaita-1-0 >= 1.5

%description
Ngó Sen for GNOME types Vietnamese through IBus, the input method GNOME comes
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
