#!/bin/bash
# Fails unless every packaging file carries the given version, e.g. 1.0.0-1. A release tag that
# disagrees with them would publish packages under the wrong version.
#
#   packaging/check-version.sh <version>-<release>
set -euo pipefail

want=${1:?usage: check-version.sh <version>-<release>}
cd "$(dirname "$0")"
fail=0

check() {
    if [ "$2" = "$3" ]; then
        echo "ok        $1: $2"
    else
        echo "MISMATCH  $1: $2 (want $3)"
        fail=1
    fi
}

pkgbuild_version() {
    echo "$(sed -n 's/^pkgver=//p' "$1")-$(sed -n 's/^pkgrel=//p' "$1")"
}

check debian/changelog "$(sed -n '1s/^[^(]*(\([^)]*\)).*/\1/p' debian/changelog)" "$want"
check rpm "$(sed -n 's/^Version: *//p' rpm/ibus-ngosen.spec)-$(sed -n 's/^Release: *\([0-9]*\).*/\1/p' rpm/ibus-ngosen.spec)" "$want"
check arch/PKGBUILD "$(pkgbuild_version arch/PKGBUILD)" "$want"
check aur/PKGBUILD "$(pkgbuild_version aur/PKGBUILD)" "$want"
check CMakeLists.txt "$(sed -n 's/^project(ibus-ngosen VERSION \([0-9.]*\).*/\1/p' ../CMakeLists.txt)" "${want%-*}"
exit "$fail"
