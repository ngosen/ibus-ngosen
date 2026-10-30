#!/bin/sh
# install-environment.sh <build dir>: the install sets the session variables kitty needs on X11.
set -eu
dest=$(mktemp -d)
trap 'rm -rf "$dest"' EXIT
DESTDIR="$dest" cmake --install "$1" --prefix /usr >/dev/null
file="$dest/usr/lib/environment.d/60-ibus-ngosen.conf"
if ! grep -qx 'GLFW_IM_MODULE=ibus' "$file" 2>/dev/null; then
    echo "FAIL: $file does not set GLFW_IM_MODULE=ibus" >&2
    exit 1
fi
