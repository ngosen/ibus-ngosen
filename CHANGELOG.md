# Nhật ký thay đổi

Mọi thay đổi đáng kể của Ngó Sen cho GNOME (`ibus-ngosen`) được ghi ở đây. Cách ghi theo
[Keep a Changelog](https://keepachangelog.com/vi/1.1.0/). Mỗi dòng nói người dùng thấy gì thay đổi.

Số version của `ibus-ngosen` riêng, không theo số của Ngó Sen đầy đủ (`fcitx5-ngosen`). Mỗi release có
tag `ibus-ngosen-<version>` và ghi tag lõi Ngó Sen đang dùng.

## [Chưa phát hành]

### Thêm

- Cuối trang Gõ chữ có nhóm "Có ở bản fcitx5": những gì chỉ bản fcitx5 có, và dòng "Chuyển sang bản
  fcitx5" mở hộp thoại có lệnh cài cùng nút "Chép lệnh". Cửa sổ không tự chạy lệnh (#25).
- Fedora: mỗi version phát hành được dựng trên kho COPR `nguyenphi/ngosen`, cài bằng
  `sudo dnf copr enable nguyenphi/ngosen` rồi `sudo dnf install ibus-ngosen`, và `dnf upgrade` tự lên version mới (#26).
- Có package cho openSUSE Tumbleweed (x86_64), cài từ repo zypper chung với bản fcitx5 (#27).

### Thay đổi

- Biểu tượng mới: chữ V ngó sen có gạch chân, dễ phân biệt với bản fcitx5 trong menu nguồn nhập và
  lưới ứng dụng.

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
