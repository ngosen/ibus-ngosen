# Ngó Sen cho GNOME

Bộ gõ tiếng Việt Ngó Sen chạy trên IBus, bộ gõ có sẵn của GNOME. Gõ gạch chân như mọi bộ gõ IBus, đổi
Anh/Việt bằng Super+Space như các nguồn nhập khác của GNOME.

Đang làm, chưa có bản phát hành. Cần gõ ngay thì dùng
[Ngó Sen đầy đủ](https://github.com/ngosen/ngosen) cho fcitx5.

## Dựng từ mã nguồn

Cần IBus ≥ 1.5.27 (gói `libibus-1.0-dev` hoặc `ibus-devel`), CMake, trình dịch C++17 và Rust ≥ 1.88.

```
git clone --recurse-submodules https://github.com/ngosen/ibus-ngosen.git
cd ibus-ngosen
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
ctest --test-dir build
```

## Nguồn gốc

Logic gõ là lõi của [Ngó Sen](https://github.com/ngosen/ngosen), gắn vào repo này làm submodule `ngosen`.
Ngó Sen dựa trên mã của [fcitx5-lotus](https://github.com/LotusInputMethod/fcitx5-lotus) và
[VMK](https://github.com/thanhpy2009/VMK). Giấy phép GPL-3.0-or-later.
