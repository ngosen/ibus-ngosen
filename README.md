# Ngó Sen cho GNOME

Ngó Sen cho GNOME là bộ gõ tiếng Việt chạy trên IBus có sẵn của GNOME, không cần fcitx5. Đổi Anh/Việt bằng
Super+Space như các nguồn nhập khác của GNOME.

Bản này hướng đến sự đơn giản và ổn định, dùng những gì GNOME có sẵn. Trên GNOME, cài xong là gõ được ngay,
không phải thiết lập gì thêm. Tính năng nào cần lách giới hạn của GNOME/IBus thì không có.

Chữ đang gõ được gạch chân (preedit) cho tới khi chốt. Đây là cách gõ mà IBus và GNOME hỗ trợ chính, nên chạy
được ở hầu hết app trên Linux, kể cả terminal, game và app X11. Tuỳ chọn "Gõ Sen ở app cho phép (thử nghiệm)"
(mặc định tắt) cho chữ hiện thẳng vào ô, không gạch chân, ở những app trên GNOME Wayland báo được chữ quanh con
trỏ. Tuỳ chọn này chưa ổn định, chữ có thể sai ở vài app; gặp lỗi thì tắt đi và báo cho Ngó Sen.

Nếu cần Cứu chữ, Cứu dấu, phím chuyển Anh/Việt riêng, gõ tắt khi ở tiếng Anh, chế độ riêng theo từng app như Vim
mode, chèn emoji hay Gõ Sen trên X11, dùng [Ngó Sen đầy đủ cho fcitx5](https://github.com/ngosen/ngosen).

## Cài

```
curl -fsSL https://raw.githubusercontent.com/ngosen/ngosen/main/install.sh | bash -s -- --ibus
```

Lệnh tải package `ibus-ngosen` đúng distro từ [release mới nhất](https://github.com/ngosen/ibus-ngosen/releases/latest),
so hash SHA-256 và hỏi lại trước khi cài.

Có package cho Debian 13, Kali, Ubuntu 24.04 trở lên, Fedora 43 và 44, Arch, CachyOS và openSUSE Tumbleweed. Linux
Mint 22 dùng package của Ubuntu 24.04. Có package ARM 64-bit cho Debian, Ubuntu và Fedora; Arch và openSUSE chỉ có
x86_64. Không có package cho Debian 12 và Ubuntu 22.04.

Trên GNOME, lệnh thêm "Tiếng Việt (Ngó Sen)" vào nguồn nhập, đặt app dùng IBus rồi khởi động lại IBus. Nếu tài
khoản đang dùng fcitx5, lệnh hỏi có bỏ fcitx5 để chuyển sang bản cho GNOME không. Hai bản không chạy cùng lúc trong
một tài khoản; mỗi tài khoản chọn một.

Trên Xfce, Cinnamon, MATE (X11, Debian, Ubuntu, Linux Mint), lệnh dùng `im-config` đặt IBus làm bộ gõ và thêm
Ngó Sen; đăng xuất rồi đăng nhập lại, bấm Ctrl+Space để chuyển qua lại Ngó Sen và bàn phím thường. Desktop khác
không có `im-config` thì lệnh chỉ cài package rồi in các bước tự làm: mở IBus Preferences bằng `ibus-setup`, thêm
"Tiếng Việt (Ngó Sen)", rồi đăng xuất và đăng nhập lại.

Muốn quay lại bản fcitx5 thì chạy lệnh cài [bản fcitx5](https://github.com/ngosen/ngosen); lệnh hỏi lại rồi gỡ
bản cho GNOME.

Trên Fedora, có thể cài từ kho COPR, để `dnf upgrade` tự lên version mới. Sau đó thiết lập IBus và thêm nguồn nhập
như trên:

```
sudo dnf copr enable nguyenphi/ngosen
sudo dnf install ibus-ngosen
```

openSUSE Tumbleweed có repo zypper chung với bản fcitx5. zypper hỏi một lần có tin cậy key không; đối chiếu
fingerprint rồi chọn tin cậy:

```
sudo zypper addrepo https://ngosen.github.io/ngosen/opensuse/ngosen.repo
sudo zypper refresh
sudo zypper install ibus-ngosen
```

Muốn cài bằng tay, tải package đúng distro và kiến trúc từ trang
[Releases](https://github.com/ngosen/ibus-ngosen/releases), rồi cài bằng trình quản lý gói. Sau đó thiết lập IBus và
thêm nguồn nhập như trên.

## Gỡ

```
curl -fsSL https://raw.githubusercontent.com/ngosen/ngosen/main/install.sh | bash -s -- --uninstall
```

Lệnh tự nhận bản đang cài. Nếu có cả hai bản, lệnh hỏi gỡ bản nào; thêm `--ibus` để chọn bản cho GNOME.

Trên GNOME, lệnh trả lại nguồn nhập và thiết lập IBus mà lệnh cài đã đổi. Gỡ xong, đăng xuất rồi đăng nhập lại. Cài
đặt trong `~/.config/ngosen/` được giữ lại.

## Dựng từ mã nguồn

Cần IBus ≥ 1.5.27 (gói `libibus-1.0-dev` hoặc `ibus-devel`), CMake, trình dịch C++17, Rust ≥ 1.88,
Python 3 và `msgfmt` (gói `gettext`). Cửa sổ cài đặt chạy bằng Python với GTK 4 và libadwaita ≥ 1.5
(`python3-gi`, `gir1.2-adw-1` hoặc `libadwaita`).
Test engine chạy một ibus-daemon riêng, cần thêm `ibus`, `dbus-run-session` và `python3-gi` có IBus; bỏ
test này bằng `-DNGOSEN_IBUS_DAEMON_TESTS=OFF`. Test cửa sổ cài đặt cần `xvfb-run`, thiếu thì được bỏ
qua.

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

Mở cửa sổ cài đặt từ Cài đặt › Bàn phím › "Tiếng Việt (Ngó Sen)", hoặc tìm "Ngó Sen" trong danh sách
app. Đổi gì lưu ngay; nút Hoàn tác trên thông báo ở đáy đưa cài đặt về như trước lần đổi đó.

Cài đặt nằm trong `~/.config/ngosen/`, cùng định dạng và tên khoá với `ngosen.conf` của Ngó Sen đầy đủ.
Lần chạy đầu, nếu máy đã có Ngó Sen cho fcitx5 thì kiểu gõ, gõ tắt, bảng phím riêng và từ điển riêng được
chép sang (từ điển vào `~/.local/share/ngosen/`); file của fcitx5 giữ nguyên. Sửa `ngosen.conf`, bảng gõ
tắt hay bảng phím thì có hiệu lực từ chữ gõ tiếp theo. Xoá `ngosen.conf` là về cài đặt mặc định.

Gõ ra chữ sai thì chọn "Lưu nhật ký gõ" trong menu nguồn nhập ngay sau đó: những gì vừa gõ được lưu vào
`~/.local/state/ngosen/`, chỉ tài khoản của mình đọc được. Đọc lại file rồi gửi kèm báo lỗi.

Log của engine nằm trong journal (`journalctl -t ibus-engine-ngosen`). Muốn có cả log gỡ lỗi thì
chạy ibus-daemon với `NGOSEN_DEBUG=1`; chữ gõ trong ô mật khẩu không bao giờ được ghi.

## Nguồn gốc

Logic gõ là lõi của [Ngó Sen](https://github.com/ngosen/ngosen), gắn vào repo này làm submodule `ngosen`.
Ngó Sen dựa trên mã của [fcitx5-lotus](https://github.com/LotusInputMethod/fcitx5-lotus) và
[VMK](https://github.com/thanhpy2009/VMK). Giấy phép GPL-3.0-or-later.
