Name:           ibus-ngosen
Version:        1.1.2
Release:        1
Summary:        Ngó Sen for GNOME, a Vietnamese input method for IBus
License:        GPL-3.0-or-later AND LGPL-2.1-or-later AND MIT AND GPL-2.0-or-later AND OFL-1.1
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
# Loaded with dlopen to watch clicks on X11, which the automatic requires miss.
Requires:       libxcb1
Requires:       libxcb-xinput0
Requires:       python3-gobject
# The settings window loads these through GObject introspection, which the automatic requires miss.
Requires:       typelib(Gtk) = 4.0
Requires:       typelib(Adw) = 1
Requires:       typelib(PangoCairo) = 1.0
Requires:       libadwaita-1-0 >= 1.5

%description
Ngó Sen for GNOME types Vietnamese through IBus, the input method GNOME comes
with. The word being typed is underlined until it is done.

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
%{_datadir}/applications/ibus-setup-ngosen.desktop
%{_datadir}/metainfo/io.github.ngosen.IBusNgoSen.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/ibus-ngosen.svg
%{_datadir}/icons/hicolor/scalable/apps/io.github.ngosen.IBusNgoSen.svg

%changelog
* Fri Oct 30 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.1.2-1
- Stop resending unchanged menu items on focus changes, which stalled GNOME Shell on X11.

* Thu Oct 29 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.1.1-1
- Address bars type with the preedit when typing with Sen is on, Save typing log in the menu.

* Thu Oct 29 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.1.0-1
- New icon, Super+Space fix on GNOME 46, Backspace reopens the last word, core ngosen-1.7.0-1.

* Tue Oct 27 2026 Nguyen Phi <nguyenphidt@gmail.com> - 1.0.0-1
- First release.
