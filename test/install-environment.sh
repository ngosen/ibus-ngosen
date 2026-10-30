#!/bin/sh
# install-environment.sh <build dir>: the install sets the session variables kitty needs on X11.
set -eu
dest=$(mktemp -d)
trap 'rm -rf "$dest"' EXIT
DESTDIR="$dest" cmake --install "$1" --prefix /usr >/dev/null
fail() {
    echo "FAIL: $1" >&2
    exit 1
}
file="$dest/usr/lib/environment.d/60-ibus-ngosen.conf"
grep -qx 'GLFW_IM_MODULE=ibus' "$file" 2>/dev/null || fail "$file does not set GLFW_IM_MODULE=ibus"
# Sessions that do not take the systemd user environment (LightDM: Cinnamon, Xfce, MATE) read profile.d.
# Under /etc for a /usr prefix, under the prefix otherwise.
profile=$(find "$dest" -path '*/etc/profile.d/ibus-ngosen.sh')
[ -n "$profile" ] || fail "profile.d/ibus-ngosen.sh is not installed"
[ "$(env -i sh -c ". '$profile'; sh -c 'echo \$GLFW_IM_MODULE'")" = ibus ] || fail "$profile does not export GLFW_IM_MODULE=ibus"
[ "$(env -i GLFW_IM_MODULE=other sh -c ". '$profile'; echo \$GLFW_IM_MODULE")" = other ] || fail "$profile overrides a value the user set"
