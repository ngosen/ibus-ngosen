# Nhật ký thay đổi

Mọi thay đổi đáng kể của Ngó Sen cho GNOME (`ibus-ngosen`) được ghi ở đây. Cách ghi theo
[Keep a Changelog](https://keepachangelog.com/vi/1.1.0/). Mỗi dòng nói người dùng thấy gì thay đổi.

Số version của `ibus-ngosen` riêng, không theo số của Ngó Sen đầy đủ (`fcitx5-ngosen`). Mỗi release có
tag `ibus-ngosen-<version>` và ghi tag lõi Ngó Sen đang dùng.

## [Chưa phát hành]

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
