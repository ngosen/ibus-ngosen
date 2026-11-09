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
spec_version() {
    echo "$(sed -n 's/^Version: *//p' "$1")-$(sed -n 's/^Release: *\([0-9]*\).*/\1/p' "$1")"
}

check rpm "$(spec_version rpm/ibus-ngosen.spec)" "$want"
check rpm/opensuse "$(spec_version rpm/opensuse/ibus-ngosen.spec)" "$want"
check arch/PKGBUILD "$(pkgbuild_version arch/PKGBUILD)" "$want"
# rpmbuild warns about a changelog date whose weekday is wrong, and dpkg does not check at all.
weekday_of() {
    LC_ALL=C date -d "$1" +%a
}

deb_date=$(sed -n '/^ -- /{s/.*>  *//;p;q}' debian/changelog)
check "debian/changelog weekday" "${deb_date%%,*}" "$(weekday_of "$(echo "$deb_date" | cut -d' ' -f2-4)")"

spec_entry() {
    sed -n '/^\* /{p;q}' "$1"
}
for spec in rpm/ibus-ngosen.spec rpm/opensuse/ibus-ngosen.spec; do
    entry=$(spec_entry "$spec")
    check "$spec weekday" "$(echo "$entry" | cut -d' ' -f2)" "$(weekday_of "$(echo "$entry" | cut -d' ' -f3-5)")"
done

check CMakeLists.txt "$(sed -n 's/^project(ibus-ngosen VERSION \([0-9.]*\).*/\1/p' ../CMakeLists.txt)" "${want%-*}"
exit "$fail"
