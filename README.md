# Ngó Sen cho GNOME

Ngó Sen cho GNOME là bộ gõ tiếng Việt chạy trên IBus có sẵn của GNOME, không cần fcitx5. Nhấp Ctrl+Shift để đổi
Anh/Việt như UniKey; thanh trên cùng hiện V hoặc E. Như bản fcitx5, mỗi app nhớ Anh hay Việt của riêng nó, app chưa
đổi lần nào thì theo lần đổi gần nhất. Cửa sổ cài đặt cho đổi sang Shift+Alt, hoặc tắt phím này nếu
không cần. Super+Space vẫn đổi nguồn nhập như các nguồn nhập khác của GNOME. Lỡ gõ chữ lúc đang tiếng Anh thì
chuyển sang tiếng Việt, Cứu chữ gõ lại chữ đó có dấu (vieetj → việt), Tab hoặc Esc trả lại.

Bản này hướng đến sự đơn giản và ổn định, dùng những gì GNOME có sẵn. Trên GNOME, cài xong là gõ được ngay,
không phải thiết lập gì thêm. Tính năng nào cần lách giới hạn của GNOME/IBus thì không có.

Mặc định Ngó Sen dùng Gõ Sen như bản fcitx5: chữ hiện thẳng vào ô, không gạch chân, ở những app báo được chữ
quanh con trỏ. Ô nào không báo được thì chữ đang gõ được gạch chân (preedit) cho tới khi chốt; trên X11 đó là
Chrome, app Electron, xterm, Alacritty và kitty. Bấm phím ` rồi chọn Gõ Sen, Gạch chân hay Tắt để đổi riêng cho
app đang dùng, Ngó Sen nhớ lựa chọn đó cho app ấy. Cửa sổ cài đặt cho đổi thứ tự hay ẩn bớt các chế độ trong
menu, và đặt một phím chuyển thẳng app sang chế độ kế tiếp không cần mở menu. Muốn gạch chân ở mọi app chưa chọn riêng thì tắt tuỳ chọn "Gõ Sen ở app cho phép"
trong cửa sổ cài đặt. GNOME 50.0–50.3 (như Ubuntu 26.04) làm mất phím Ngó Sen gửi tới app, nên gói kèm một
extension sửa lỗi này: đăng nhập lại một lần là Ngó Sen tự bật extension, chưa chạy thì chữ vẫn gạch chân. Gặp
app gõ sai thì chuyển app đó sang Gạch chân và báo cho Ngó Sen.

Nếu cần Cứu dấu ở mọi app, chế độ riêng theo từng app như Vim mode hay chèn emoji, dùng
[Ngó Sen đầy đủ cho fcitx5](https://github.com/ngosen/ngosen).

## Cài

Tải package đúng distro và kiến trúc từ [release mới nhất](https://github.com/ngosen/ibus-ngosen/releases/latest),
rồi cài bằng trình quản lý gói, trong thư mục vừa tải về:

```
sudo apt install ./ibus-ngosen_*.deb         # Debian, Kali, Ubuntu, Linux Mint
sudo dnf install ./ibus-ngosen-*.rpm         # Fedora
sudo pacman -U ./ibus-ngosen-*.pkg.tar.zst   # Arch, CachyOS
sudo zypper install ./ibus-ngosen-*.rpm      # openSUSE Tumbleweed
```

Có package cho Debian 13, Kali, Ubuntu 24.04 trở lên, Fedora 43 và 44, Arch, CachyOS và openSUSE Tumbleweed. Linux
Mint 22 dùng package của Ubuntu 24.04. Có package ARM 64-bit cho Debian, Ubuntu và Fedora; Arch và openSUSE chỉ có
x86_64. Không có package cho Debian 12 và Ubuntu 22.04.

Hai bản không chạy cùng lúc trong một tài khoản; nếu đang dùng [bản fcitx5](https://github.com/ngosen/ngosen), xem
[Chuyển qua lại với bản fcitx5](#chuyển-qua-lại-với-bản-fcitx5).

Cài xong, trên GNOME:

1. Đăng xuất rồi đăng nhập lại, để IBus thấy bộ gõ vừa cài.
2. Mở Settings → Keyboard → Input Sources, thêm "Tiếng Việt (Ngó Sen)".

Lần đầu gõ bằng Ngó Sen, nó tự bỏ nguồn nhập "Tiếng Anh (Mỹ)" vì Ctrl+Shift đã chuyển sang tiếng Anh, nên chỉ
còn một nguồn nhập. Việc này chỉ làm một lần: thêm lại "Tiếng Anh (Mỹ)" thì nó được giữ, và bàn phím của ngôn ngữ
khác không bị đụng tới. Nếu lúc đó phím Ctrl+Shift đang tắt thì Ngó Sen không bỏ nguồn nào, kể cả khi bật
phím lại sau này. Mục "Kiểm tra" trong cửa sổ cài đặt có nút "Chỉ dùng Ngó Sen" để bỏ nó sau. Ngó Sen
luôn gõ trên bàn phím kiểu Mỹ, kể cả khi đang ở tiếng Anh bằng Ctrl+Shift.

Trên desktop khác GNOME như Cinnamon, Xfce:

1. Chạy `im-config -n ibus` nếu máy có `im-config`.
2. Mở IBus Preferences bằng `ibus-setup`, thêm "Tiếng Việt (Ngó Sen)". Cinnamon giữ phím Super cho menu nên Super+Space
   không tới được IBus; đặt phím chuyển khác như Ctrl+Space ở tab General.
3. Đăng xuất rồi đăng nhập lại.

Trên Fedora, có thể cài từ kho COPR, để `dnf upgrade` tự lên version mới. Sau đó thêm nguồn nhập như trên:

```
sudo dnf copr enable nguyenphi/ngosen
sudo dnf install ibus-ngosen
```

Trên Debian, Ubuntu, Arch và openSUSE, có thể cài từ kho APT, pacman, zypper của Ngó Sen, để `apt upgrade`,
`pacman -Syu`, `zypper up` tự lên version mới: thêm kho theo
[hướng dẫn của bản fcitx5](https://github.com/ngosen/ngosen#cập-nhật-bằng-trình-quản-lý-gói), rồi cài `ibus-ngosen`
thay cho `fcitx5-ngosen`.

## Chuyển qua lại với bản fcitx5

Từ bản fcitx5 sang bản này: gỡ bản fcitx5 bằng `install.sh --uninstall` như hướng dẫn của nó, rồi cài bản này. Nếu
đã gỡ bằng trình quản lý gói, lệnh cài fcitx5 có thể còn để lại biến môi trường hay mục tự chạy làm app vẫn đi qua
fcitx5: mở tab "Kiểm tra" trong cửa sổ cài đặt, bấm "Xoá" ở bước "Tài khoản này còn cài đặt của bản fcitx5" rồi
đăng xuất và đăng nhập lại. Nút chỉ xoá những tệp còn y nguyên như lệnh cài đã ghi; tệp đã sửa tay thì bước kế bên
chỉ ra đường dẫn để tự sửa.

Từ bản này sang bản fcitx5: trong cửa sổ cài đặt, mục "Có ở bản fcitx5" có lệnh cài để chép. Trên Debian và Ubuntu
lệnh tự thay bản này; trên Fedora, openSUSE và Arch, chép lệnh, gỡ `ibus-ngosen` rồi mới chạy.

Cài đặt chỉ được chép một lần, lúc bản này chạy lần đầu trên máy đã có bản fcitx5. Sau đó hai bản không đồng bộ
với nhau; muốn mang thay đổi sang bản kia thì sao lưu ở bản này rồi khôi phục ở bản kia. Trước khi khôi phục một
bản sao lưu của bản này vào bản fcitx5, hãy sao lưu cài đặt của bản fcitx5: bản fcitx5 cũ hơn
[ngosen/ngosen#648](https://github.com/ngosen/ngosen/pull/648) xoá các app đã chọn riêng tiếng Việt hay tiếng Anh.

## Gỡ

Bỏ "Tiếng Việt (Ngó Sen)" khỏi nguồn nhập hoặc khỏi IBus Preferences, rồi gỡ bằng trình quản lý gói:

```
sudo apt remove ibus-ngosen      # Debian, Kali, Ubuntu, Linux Mint
sudo dnf remove ibus-ngosen      # Fedora
sudo pacman -R ibus-ngosen       # Arch, CachyOS
sudo zypper remove ibus-ngosen   # openSUSE Tumbleweed
```

Gỡ xong, đăng xuất rồi đăng nhập lại. Cài đặt trong `~/.config/ngosen/` được giữ lại.

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
```

Sau đó đăng xuất rồi đăng nhập lại, và thêm "Tiếng Việt (Ngó Sen)" trong Cài đặt › Bàn phím › Nguồn nhập.

Mở cửa sổ cài đặt từ Cài đặt › Bàn phím › "Tiếng Việt (Ngó Sen)", hoặc tìm "Ngó Sen" trong danh sách
app. Đổi gì lưu ngay; nút Hoàn tác trên thông báo ở đáy đưa cài đặt về như trước lần đổi đó.

Cài đặt nằm trong `~/.config/ngosen/`, cùng định dạng và tên khoá với `ngosen.conf` của Ngó Sen đầy đủ.
Lần chạy đầu, nếu máy đã có Ngó Sen cho fcitx5 thì kiểu gõ, gõ tắt, bảng phím riêng và từ điển riêng được
chép sang (từ điển vào `~/.local/share/ngosen/`); file của fcitx5 giữ nguyên. Sửa `ngosen.conf`, bảng gõ
tắt hay bảng phím thì có hiệu lực từ chữ gõ tiếp theo. Xoá `ngosen.conf` là về cài đặt mặc định.

Không gõ được tiếng Việt thì mở mục "Kiểm tra" trong cửa sổ cài đặt: nó kiểm IBus, nguồn nhập và
biến môi trường, sửa được vài bước bằng một nút, và chép kết quả để gửi kèm báo lỗi.

Gõ ra chữ sai thì chọn "Lưu nhật ký gõ" trong menu nguồn nhập ngay sau đó: những gì vừa gõ được lưu vào
`~/.local/state/ngosen/`, chỉ tài khoản của mình đọc được. Đọc lại file rồi gửi kèm báo lỗi.

Log của engine nằm trong journal (`journalctl -t ibus-engine-ngosen`). Muốn có cả log gỡ lỗi thì
chạy ibus-daemon với `NGOSEN_DEBUG=1`; chữ gõ trong ô mật khẩu không bao giờ được ghi.

## Nguồn gốc

Logic gõ là lõi của [Ngó Sen](https://github.com/ngosen/ngosen), gắn vào repo này làm submodule `ngosen`.
Ngó Sen dựa trên mã của [fcitx5-lotus](https://github.com/LotusInputMethod/fcitx5-lotus) và
[VMK](https://github.com/thanhpy2009/VMK). Giấy phép GPL-3.0-or-later.
