#!/bin/sh
# run-with-daemon.sh <python> <component dir> <dictionary> <test script>: runs the test against a
# private ibus-daemon that starts the engine from the build tree. Run it under dbus-run-session.
set -e
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# The test switches to the English keyboard engine that ibus ships.
mkdir "$tmp/component"
cp "$2"/*.xml "$tmp/component/"
cp "${NGOSEN_IBUS_SIMPLE_COMPONENT:-/usr/share/ibus/component/simple.xml}" "$tmp/component/"
export HOME="$tmp" XDG_CONFIG_HOME="$tmp/config" XDG_CACHE_HOME="$tmp/cache" XDG_DATA_HOME="$tmp/data"
export IBUS_ADDRESS="unix:path=$tmp/ibus" IBUS_COMPONENT_PATH="$tmp/component" NGOSEN_IBUS_DICTIONARY="$3"
export NGOSEN_DEBUG=1 NGOSEN_IBUS_LOG_FILE="$tmp/engine.log"
# A private X server, so the engine watches the clicks the test makes and never the desktop's.
# NGOSEN_TEST_NO_X runs with none, where the engine cannot watch clicks.
unset WAYLAND_DISPLAY DISPLAY
export XDG_SESSION_TYPE=x11
xvfb=
if [ -z "$NGOSEN_TEST_NO_X" ]; then
    Xvfb -displayfd 3 -nolisten tcp 3>"$tmp/display" >/dev/null 2>&1 &
    xvfb=$!
    trap 'kill $xvfb 2>/dev/null; rm -rf "$tmp"' EXIT
    while [ ! -s "$tmp/display" ]; do
        kill -0 $xvfb 2>/dev/null || { echo "Xvfb did not start" >&2; exit 1; }
        sleep 0.1
    done
    export DISPLAY=":$(cat "$tmp/display")"
fi
ibus-daemon --address="$IBUS_ADDRESS" --panel=disable --emoji-extension=disable --xim=false --config=disable --cache=none &
daemon=$!
trap 'kill $daemon $xvfb 2>/dev/null; rm -rf "$tmp"' EXIT
"$1" "$4"
