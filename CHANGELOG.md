# Nhật ký thay đổi

Mọi thay đổi đáng kể của Ngó Sen cho GNOME (`ibus-ngosen`) được ghi ở đây. Cách ghi theo
[Keep a Changelog](https://keepachangelog.com/vi/1.1.0/). Mỗi dòng nói người dùng thấy gì thay đổi.

Số version của `ibus-ngosen` riêng, không theo số của Ngó Sen đầy đủ (`fcitx5-ngosen`). Mỗi release có
tag `ibus-ngosen-<version>` và ghi tag lõi Ngó Sen đang dùng.

## [Chưa phát hành]

### Thay đổi

- "Gõ Sen ở app cho phép" giờ chạy bằng lõi Ngó Sen như bản fcitx5: mỗi chữ tự chọn gõ thẳng hay gạch chân,
  chữ đầu tiên trong ô còn trống của app chưa báo chữ trong ô vẫn gạch chân; lõi `ngosen-1.7.2-1` (#41).
- "Gõ Sen ở app cho phép" giờ gõ thẳng cả ở app X11 (GTK, Qt, Firefox, LibreOffice, terminal của GNOME, KDE,
  Xfce) và vẫn tự viết hoa đầu dòng ở đó, thay vì gạch chân mọi chữ; bấm chuột giữa chữ không xoá chữ khác.
  Chrome, app Electron, xterm, Alacritty và kitty vẫn gạch chân. Bấm chuột trong Alacritty và app XIM không còn làm mất chữ đang gạch chân (#44).
- Báo lỗi, báo lỗi cài đặt và đề xuất tính năng qua form có sẵn như kho fcitx5; nút "Báo lỗi" trong cửa sổ cài
  đặt mở trang chọn form (#45).

### Sửa

- kitty trên X11 gõ được tiếng Việt, không còn ra chữ thô như `vieejt`: gói đặt `GLFW_IM_MODULE=ibus` cho phiên
  đăng nhập (đã thử GNOME, Cinnamon và Xfce), có hiệu lực sau khi đăng nhập lại (#47).
- Gõ Sen trên GNOME: gõ hai phím dấu sát nhau (như w và f trong "nguowfi") không còn làm mất lần thêm dấu
  đầu và ra "ngời"; Ngó Sen chờ app hiện xong lần sửa trước, tối đa 20 ms (#56).
- Gõ Sen trên GNOME: chữ đầu tiên trong ô còn trống của app GTK, Firefox và LibreOffice không còn bị gạch chân
  mà gõ thẳng vào ô như các chữ sau (#56).
- Menu nguồn nhập trên GNOME: các tuỳ chọn bật/tắt là dòng có ✔ hoặc ✖ như menu khay của bản fcitx5, bấm vào là
  đổi và menu đóng lại lần nào cũng như nhau, thay vì công tắc lúc giữ menu lúc đóng (#57).

## [1.1.2-1] — 30/10/2026

Sửa màn hình giật khi đổi cửa sổ hay bấm phím Windows trên GNOME X11. Dùng lõi Ngó Sen `ngosen-1.7.0-1`. Tải
gói ở [release ibus-ngosen-1.1.2-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.1.2-1).

### Sửa

- Màn hình không còn giật 1–2 giây mỗi lần bấm phím Windows hay chuyển tab khi đang bật Ngó Sen: đổi ô
  không còn gửi lại menu nguồn nhập cho GNOME Shell khi menu không đổi (#28, #39).

## [1.1.1-1] — 29/10/2026

Sửa chữ lặp ở ô địa chỉ Chrome khi bật Gõ Sen, thêm mục "Lưu nhật ký gõ" để gửi kèm báo lỗi. Dùng lõi Ngó Sen
`ngosen-1.7.0-1`. Tải gói ở
[release ibus-ngosen-1.1.1-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.1.1-1).

### Thêm

- Mục "Lưu nhật ký gõ" trong menu nguồn nhập: lưu những gì vừa gõ vào `~/.local/state/ngosen/` để gửi kèm
  báo lỗi, chỉ tài khoản của mình đọc được; thông báo cho biết file nằm ở đâu (#35).

### Sửa

- Bật "Gõ Sen ở app cho phép", ô địa chỉ Chrome không còn ra chữ lặp như `vềề`: ô địa chỉ web gõ gạch chân
  (#35).

## [1.1.0-1] — 29/10/2026

Biểu tượng mới, Super+Space chạy đúng trên GNOME 46, Backspace mở lại chữ vừa gõ để sửa dấu; có gói
COPR và openSUSE. Dùng lõi Ngó Sen `ngosen-1.7.0-1`. Tải gói ở
[release ibus-ngosen-1.1.0-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.1.0-1).

### Thêm

- Bấm Backspace ngay sau chữ vừa gõ thì chữ đó mở lại dưới gạch chân để sửa: `việt`, Backspace, `s` ra
  `viết`. Cần app báo chữ quanh con trỏ (ngosen/ngosen#344).
- Cuối trang Gõ chữ có nhóm "Có ở bản fcitx5": những gì chỉ bản fcitx5 có, và dòng "Chuyển sang bản
  fcitx5" mở hộp thoại có lệnh cài cùng nút "Chép lệnh". Cửa sổ không tự chạy lệnh (#25).
- Fedora: mỗi version phát hành được dựng trên kho COPR `nguyenphi/ngosen`, cài bằng
  `sudo dnf copr enable nguyenphi/ngosen` rồi `sudo dnf install ibus-ngosen`, và `dnf upgrade` tự lên version mới (#26).
- Có package cho openSUSE Tumbleweed (x86_64), cài từ repo zypper chung với bản fcitx5 (#27).

### Thay đổi

- Tuỳ chọn "Gõ Sen ở app cho phép" nay ghi "(thử nghiệm)" trong menu và cửa sổ cài đặt, vì chữ có thể sai ở vài
  app; tuỳ chọn vẫn mặc định tắt (#31).
- Biểu tượng mới: chữ V ngó sen có gạch chân, dễ phân biệt với bản fcitx5 trong menu nguồn nhập và
  lưới ứng dụng (#29).

### Sửa

- Super+Space trên GNOME 46 chuyển được sang nguồn nhập khác, không còn gõ ra dấu cách (#30).

## [1.0.0-1] — 27/10/2026

Bản đầu tiên của Ngó Sen cho GNOME, dùng lõi Ngó Sen `ngosen-1.6.1-1`. Tải gói ở
[release ibus-ngosen-1.0.0-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.0.0-1).

### Thêm

- Bộ gõ IBus "Tiếng Việt (Ngó Sen)": gõ gạch chân, chữ được chốt khi gõ cách, dấu câu, Enter, nhấp Ctrl hay
  bấm chuột ra chỗ khác; ô mật khẩu nhận đúng phím đã gõ, và chữ gõ trong ô riêng tư không bị ghi vào
  log (#2).
- Cài đặt trong `~/.config/ngosen/`: kiểu gõ, bảng mã, gõ tắt, bảng phím riêng, từ điển riêng. Lần chạy
  đầu chép cài đặt từ Ngó Sen cho fcitx5 nếu có; sửa file thì có hiệu lực từ chữ gõ tiếp theo, chữ đang
  gõ không mất (#3).
- Cửa sổ cài đặt, mở từ Cài đặt › Bàn phím › "Tiếng Việt (Ngó Sen)" hoặc từ danh sách app: kiểu gõ, cách
  bỏ dấu, gõ tắt, ô gõ thử; lưu ngay khi đổi, có nút Hoàn tác (#5).
- Gói cài cho Debian 13, Ubuntu 24.04 trở lên, Fedora 43 và 44, Arch Linux (cả máy ARM trừ Arch), và mã
  nguồn kèm sẵn lõi Ngó Sen. Gói Debian tự kéo theo mô-đun IBus cho app GTK, kể cả trên MX Linux vốn không
  cài gói khuyên dùng (#6, #8).
- Menu nhanh trong menu nguồn nhập của GNOME (thanh trên cùng), giống menu khay của bản fcitx5: đổi Telex/VNI,
  bảng mã, bật tắt kiểm tra chính tả, gõ tắt, tự viết hoa, tự khôi phục từ gõ sai, từ điển tuỳ chỉnh, và mở cửa
  sổ cài đặt (#9).
- Tuỳ chọn "Gõ Sen ở app cho phép" (mặc định tắt): chữ hiện thẳng vào ô, không gạch chân, khi app trên GNOME
  Wayland báo được chữ quanh con trỏ (app GTK, Qt, Firefox, Chrome, LibreOffice). Terminal, game và app chạy
  qua X11 hoặc XWayland (kể cả trên Cinnamon, Xfce) vẫn gạch chân (#10, #19).
- Trang "Từ điển" trong cửa sổ cài đặt: thêm, tìm và xoá từ trong từ điển riêng, lưu ngay, có Hoàn tác; sửa
  từ điển thì bộ gõ dùng ngay từ chữ tiếp theo (#11).
