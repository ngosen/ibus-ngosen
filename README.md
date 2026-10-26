# Ngó Sen cho GNOME

Bộ gõ tiếng Việt Ngó Sen chạy trên IBus, bộ gõ có sẵn của GNOME. Gõ gạch chân như mọi bộ gõ IBus, đổi
Anh/Việt bằng Super+Space như các nguồn nhập khác của GNOME.

Đang làm, chưa có bản phát hành. Cần gõ ngay thì dùng
[Ngó Sen đầy đủ](https://github.com/ngosen/ngosen) cho fcitx5.

## Dựng từ mã nguồn

Cần IBus ≥ 1.5.27 (gói `libibus-1.0-dev` hoặc `ibus-devel`), CMake, trình dịch C++17 và Rust ≥ 1.88.
Test engine chạy một ibus-daemon riêng, cần thêm `ibus`, `dbus-run-session` và `python3-gi` có IBus; bỏ
test này bằng `-DNGOSEN_IBUS_DAEMON_TESTS=OFF`.

```
git clone --recurse-submodules https://github.com/ngosen/ibus-ngosen.git
cd ibus-ngosen
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
ctest --test-dir build
sudo cmake --install build
ibus restart
```

Sau đó thêm "Tiếng Việt (Ngó Sen)" trong Cài đặt › Bàn phím › Nguồn nhập.

Cài đặt nằm trong `~/.config/ngosen/`, cùng định dạng và tên khoá với `ngosen.conf` của Ngó Sen đầy đủ.
Lần chạy đầu, nếu máy đã có Ngó Sen cho fcitx5 thì kiểu gõ, gõ tắt, bảng phím riêng và từ điển riêng được
chép sang (từ điển vào `~/.local/share/ngosen/`); file của fcitx5 giữ nguyên. Sửa `ngosen.conf`, bảng gõ
tắt hay bảng phím thì có hiệu lực từ chữ gõ tiếp theo. Xoá `ngosen.conf` là về cài đặt mặc định.

Log của engine nằm trong journal (`journalctl -t ibus-engine-ngosen`). Muốn có cả log gỡ lỗi thì
chạy ibus-daemon với `NGOSEN_DEBUG=1`; chữ gõ trong ô mật khẩu không bao giờ được ghi.

## Nguồn gốc

Logic gõ là lõi của [Ngó Sen](https://github.com/ngosen/ngosen), gắn vào repo này làm submodule `ngosen`.
Ngó Sen dựa trên mã của [fcitx5-lotus](https://github.com/LotusInputMethod/fcitx5-lotus) và
[VMK](https://github.com/thanhpy2009/VMK). Giấy phép GPL-3.0-or-later.
