---
name: Ngó Sen for GNOME settings
description: A plain libadwaita window with the three Ngó Sen marks.
typography:
  wordmark:
    fontFamily: "'Xanh Mono', monospace"
    fontSize: "26px"
  typed:
    fontFamily: "'Xanh Mono', monospace"
    fontSize: "17px"
  everything-else: "system font (libadwaita default)"
---

# Design: Ngó Sen for GNOME settings window

The window is a GNOME app first: stock libadwaita widgets, the system accent colour, light and dark
from the system. Ngó Sen shows itself in three places only, the same marks as the fcitx5 edition's
settings window (its `DESIGN.md`): the icon, the wordmark "Ngó Sen" in Xanh Mono, and typed text in
Xanh Mono.

## Rules

1. **Stock widgets.** `AdwPreferencesPage` with `AdwSwitchRow`, `AdwComboRow` and `AdwEntryRow`. The
   only CSS is the Xanh Mono font on `.wordmark` and on the text of `.typed` entries
   (`settings/ngosen_settings/brand.py`). No custom colours.
2. **Changes save at once.** No OK or Apply. Each change writes the file and shows an `AdwToast`
   "Đã lưu “<setting>”." with "Hoàn tác", which puts back the file as it was before that change.
   One toast at a time.
3. **One name per setting in both editions.** Labels and hints use the fcitx5 edition's English
   strings, and their Vietnamese must match its `po/vi.po` (`misc/check-translations.py`). The file
   keeps the key names of `ngosen.conf`, and keys the window does not know stay in the file.
4. **The engine is the source of truth.** The window asks `ibus-engine-ngosen --print-settings` for the
   values it types with, and `--list-input-methods`/`--list-charsets` for the names it accepts, so
   defaults are not written down twice.
5. **Vietnamese UI**, whatever the desktop language is, as in the fcitx5 edition.
6. **Ship one font.** Xanh Mono (OFL) comes from the `ngosen` submodule. If it is missing, the system
   monospace font stands in.

## Layout

- Header bar: icon and wordmark on the left, the page switcher in the middle. Below 550sp wide the
  switcher moves to a bar at the bottom.
- Gõ chữ: Kiểu gõ (with a keys-to-result example such as `vieetj → việt`), Phím chuyển Anh/Việt, Bảng mã, Keymap tuỳ chỉnh,
  the Gõ thử field; then the "Cách bỏ dấu" and "Gõ nhanh" groups; last "Có ở bản fcitx5": what the
  GNOME edition does not have, a row that shows the fcitx5 install command to copy (the window never
  runs it), and a link to Ngó Sen đầy đủ.
- Gõ tắt: the switches and $TIME/$DATE formats; two entries and a Thêm button (Cập nhật when the
  abbreviation exists); a searchable list, click a row to edit it, the bin to remove it.
- Giới thiệu: icon, wordmark, version; bug report and source links; the credit line.

## Opening the window

GNOME Settings › Keyboard › "Tiếng Việt (Ngó Sen)" › Preferences opens `ibus-setup-ngosen.desktop`
(gnome-control-center looks it up by the engine name). Its `StartupWMClass` is the app id
`io.github.ngosen.IBusNgoSen`, so GNOME Shell shows the window with the right icon. Other IBus panels
use `<setup>` in `ngosen.xml`.
