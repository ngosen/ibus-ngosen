---
name: Ngó Sen for GNOME settings
description: A plain libadwaita window with the Ngó Sen marks.
typography:
  typed:
    fontSize: "17px"
  everything: "system font (libadwaita default)"
---

# Design: Ngó Sen for GNOME settings window

The window is a GNOME app first: stock libadwaita widgets, the system accent colour, light and dark
from the system. Ngó Sen shows itself in two places only: the icon, and typed text in larger text, as
in the fcitx5 edition's settings window (its `DESIGN.md`). The header bar has no wordmark, so the page
names fit at the default width.

## Rules

1. **Stock widgets.** `AdwPreferencesPage` with `AdwSwitchRow`, `AdwComboRow` and `AdwEntryRow`. The
   only CSS is a larger font size on the text of `.typed` entries
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
6. **No bundled font.** Everything uses the system font, as the fcitx5 edition does; some monospace
   fonts misplace stacked tone marks.

## Layout

- Header bar: the page switcher in the middle, the menu on the right (Sao lưu, Khôi phục, Giới thiệu
  Ngó Sen). Below 550sp wide the switcher moves to a bar at the bottom.
- Gõ chữ: Kiểu gõ (with a keys-to-result example such as `vieetj → việt`), Phím chuyển Anh/Việt, Bảng mã, Keymap tuỳ chỉnh,
  the Gõ thử field; then the "Cách bỏ dấu" and "Gõ nhanh" groups; last "Có ở bản fcitx5": what the
  GNOME edition does not have, a row that shows the fcitx5 install command to copy (the window never
  runs it), and a link to Ngó Sen đầy đủ.
- Gõ tắt: the switches and $TIME/$DATE formats; two entries and a Thêm button (Cập nhật when the
  abbreviation exists); a searchable list, click a row to edit it, the bin to remove it.
- Kiểm tra: the setup steps, each with a fix where the window can do it, and the report to copy.
- Giới thiệu Ngó Sen (from the menu): an `AdwAboutDialog` with the icon, version, bug report and
  source links, the licence and the credit line.

## Opening the window

GNOME Settings › Keyboard › "Tiếng Việt (Ngó Sen)" › Preferences opens `ibus-setup-ngosen.desktop`
(gnome-control-center looks it up by the engine name). Its `StartupWMClass` is the app id
`io.github.ngosen.IBusNgoSen`, so GNOME Shell shows the window with the right icon. Other IBus panels
use `<setup>` in `ngosen.xml`.
