# Nhật ký thay đổi

Mọi thay đổi đáng kể của Ngó Sen cho GNOME (`ibus-ngosen`) được ghi ở đây. Cách ghi theo
[Keep a Changelog](https://keepachangelog.com/vi/1.1.0/). Mỗi dòng nói người dùng thấy gì thay đổi.

Số version của `ibus-ngosen` riêng, không theo số của Ngó Sen đầy đủ (`fcitx5-ngosen`). Mỗi release có
tag `ibus-ngosen-<version>` và ghi tag lõi Ngó Sen đang dùng.

## [Chưa phát hành]

### Thêm

- Đổi thứ tự hay ẩn bớt Gõ Sen, Gạch chân và Tắt trong menu phím `, và đặt phím chuyển nhanh (như Ctrl+`) đưa
  app đang dùng sang chế độ kế tiếp rồi nhớ cho app đó, như bản fcitx5. Menu mở ra trỏ sẵn vào chế độ app đang gõ
  (#100).
- Ẩn bớt mục trong menu trên thanh trên cùng (Kiểu gõ, Bảng mã, Kiểm tra chính tả, Gõ tắt, Tự viết hoa…) ở nhóm
  "Hiện trong menu thanh trên cùng" của cửa sổ cài đặt, như bản fcitx5 ẩn mục trong menu khay (#101).
- Chọn giao diện tiếng Anh ở "Ngôn ngữ giao diện" trong cửa sổ cài đặt như bản fcitx5: menu trên thanh trên cùng, menu
  phím ` và thông báo đổi ngay, cửa sổ cài đặt đổi ở lần mở sau (#104).
- Ô "Tìm cài đặt" trên thanh bên của cửa sổ cài đặt như bản fcitx5: gõ không dấu cũng tìm được, Enter hay bấm vào
  kết quả thì mở đúng mục đó; Ctrl+F đưa về ô tìm (#111).
- Trang "Có gì mới & mẹo" trong cửa sổ cài đặt như bản fcitx5: tính năng mới của từng bản và mẹo gõ, mỗi mục có
  nút mở thẳng tới cài đặt liên quan; đầu trang Gõ hiện một mẹo ngẫu nhiên. Nhãn nút không còn bị gãy thành
  nhiều dòng như lỗi vừa sửa ở bản fcitx5 (#112, #118).
- Sau khi cập nhật lên bản có tính năng mới, Ngó Sen báo một lần "Ngó Sen có gì mới?" như bản fcitx5, nút "Xem"
  mở thẳng trang "Có gì mới & mẹo"; cài mới thì không báo (#113).
- Như bản fcitx5, khi terminal hỏi password ẩn chữ (sudo, passwd…) Ngó Sen tự ngừng gõ tiếng Việt: phím đi
  nguyên vẹn, không ghi vào nhật ký gõ; xong tự bật lại. Gõ `vim` hay `nvim` ở terminal rồi Enter thì Ngó Sen
  cho lệnh Vim đi qua nguyên vẹn, từ đầu tiên gõ trong file có dấu ngay; thoát bằng `:q`, `:wq`, `ZZ` (#120).
- Mục Vim mode trong menu phím ` (phím `v`) như bản fcitx5: bật cho app đang dùng thì Ngó Sen theo phím lệnh của
  Vim ở chế độ normal, nhớ riêng cho từng app trong `ngosen-vim-apps.conf`, chép sang từ bản fcitx5 lúc chạy lần
  đầu. Ẩn mục hay đổi phím của nó trong nhóm "Menu chế độ gõ" của cửa sổ cài đặt (#121).
- Như bản fcitx5, một từ bắt đầu bằng / ở đầu dòng hay sau dấu cách được giữ nguyên như đã gõ, nên lệnh chat
  (/cost) và đường dẫn (/usr/share) không bị thêm dấu; và/hoặc, @tên vẫn có dấu. Tắt ở "Gõ thô sau dấu / đầu từ"
  trong nhóm "Gõ nhanh" của cửa sổ cài đặt (#129).
- Mẹo Steam trong trang "Có gì mới & mẹo": Steam chỉ nhận bộ gõ khi chạy bằng `LC_CTYPE=zh_CN.UTF-8 steam`, giao
  diện vẫn giữ ngôn ngữ cũ (#131).

### Thay đổi

- Ctrl+Shift đổi Anh/Việt riêng cho app đang dùng như bản fcitx5: mỗi app nhớ lựa chọn của nó, app chưa đổi lần
  nào thì theo lần đổi gần nhất. Mục "Tiếng Anh" trong menu phím ` thành "Tắt" và cũng chỉ tắt cho app đang dùng.
  Sao lưu và khôi phục mang theo lựa chọn Anh/Việt của từng app, cùng tệp với bản fcitx5 (#94).
- Cứu chữ chạy cả trên phiên Wayland như bản fcitx5, không chỉ X11: lỡ gõ vieetj lúc tiếng Anh rồi nhấp Ctrl+Shift
  là thành việt. Bấm chuột sang chỗ khác trước khi chuyển thì chữ giữ nguyên (#117).
- Menu phím ` bỏ mục "Chế độ gõ mặc định" như bản fcitx5: chọn lại chế độ app vẫn dùng là app đó lại theo cài đặt
  chung, chọn chế độ khác thì nhớ riêng cho app. Phím chuyển nhanh cũng bỏ bước này (#122).
- Công tắc "Gõ Sen" trong cửa sổ cài đặt thành mục "Chế độ gõ" với hai nút Gõ Sen và Gạch chân như bản fcitx5, nhìn
  là biết app chưa chọn riêng đang gõ kiểu nào (#127).
- Dùng lõi Ngó Sen mới hơn `ngosen-1.9.2-1` (nhánh next): gõ Telex quên mũ ở vần luôn có mũ như `tienf`, `viecj`
  nay ra tiền, việc khi chốt chữ (ngosen/ngosen#696); chữ liền chữ số như "tôi2" giữ đúng dấu khi BackSpace, và
  BackSpace vào chữ đang hiện nguyên phím không còn làm rối chữ gõ tiếp (ngosen/ngosen#646, ngosen/ngosen#651,
  ngosen/ngosen#661); từ điển có thêm âm tiết của tên xã, phường và dân tộc như Đakrông, Mnông, kmăl
  (ngosen/ngosen#708) (#135).
- Như bản fcitx5, bản IBus nạp danh sách từ tiếng Anh thông dụng. Nhờ vậy tên riêng mở đầu bằng phụ âm ghép như
  plông, drăng, Hrê, Brâu gõ được mà `draw` vẫn là draw (ngosen/ngosen#706), và BackSpace trong một từ tiếng Anh
  đang hiện nguyên phím chỉ xoá một chữ như app thấy (#135).

## [1.2.2-1] — 10/11/2026

Gõ Sen ở mọi app như bản fcitx5, kể cả app Electron, Chrome và terminal trên X11; biểu tượng và logo giống bản fcitx5;
cửa sổ cài đặt không còn cắt chữ. Dùng lõi Ngó Sen `ngosen-1.9.0-1`. Tải gói ở
[release ibus-ngosen-1.2.2-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.2.2-1).

### Thay đổi

- Biểu tượng bộ gõ và logo cửa sổ cài đặt giống bản fcitx5, bỏ chữ V gạch chân (#115).
- Gõ Sen ở mọi app như bản fcitx5, kể cả app Electron (VS Code, Discord…), Chrome và terminal trên X11: Ngó Sen không
  còn tự gạch chân ở những app này. App nào gõ sai thì bấm phím ` chọn Gạch chân cho riêng app đó. Tuỳ chọn trong cửa
  sổ cài đặt đổi tên thành "Gõ Sen" (#116).

### Sửa

- Cửa sổ cài đặt hiện đủ giá trị đang chọn, không còn cắt "Ctrl+Shift" thành "C…" hay "Unicode" thành
  "U…" ở một số cỡ cửa sổ (#114).

## [1.2.1-1] — 09/11/2026

Trên GNOME chỉ còn một nguồn nhập: Ngó Sen tự bỏ "Tiếng Anh (Mỹ)" trùng một lần và luôn gõ trên bàn phím kiểu Mỹ.
Ô địa chỉ Chrome và Chromium gõ thẳng khi Gõ Sen như bản fcitx5; cửa sổ cài đặt xếp các mục ở thanh bên trái; tab
Kiểm tra báo đúng hơn và dọn được những gì lệnh cài fcitx5 để lại; bản sao lưu ghi rõ bản nào tạo ra. Dùng lõi Ngó
Sen `ngosen-1.9.0-1`. Tải gói ở
[release ibus-ngosen-1.2.1-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.2.1-1).

### Thêm

- Trên GNOME, Ngó Sen tự bỏ nguồn nhập "Tiếng Anh (Mỹ)" một lần khi vừa được thêm, vì Ctrl+Shift đã chuyển sang
  tiếng Anh; mục "Kiểm tra" có nút "Chỉ dùng Ngó Sen" làm việc này sau đó (#106).

### Thay đổi

- Ngó Sen luôn gõ trên bàn phím kiểu Mỹ, như Telex và VNI cần; trước đây nó giữ bàn phím của nguồn nhập dùng
  ngay trước, có thể là bàn phím Đức hay Pháp (#106).

### Sửa

- Hướng dẫn cài bảo đăng xuất rồi đăng nhập lại thay cho `ibus restart`: sau lệnh đó GNOME không báo loại ô
  cho bộ gõ tới lần đăng nhập sau, nên ô địa chỉ và terminal có thể gõ sai (#107).
- Bản sao lưu ghi rõ do bản IBus tạo, để bản fcitx5 (từ lõi có ngosen/ngosen#648) khôi phục nó mà không xoá các
  app đã chọn riêng tiếng Việt hay tiếng Anh trong máy (#98).
- Khi Gõ Sen, ô địa chỉ của Chrome và Chromium gõ thẳng như bản fcitx5, không còn gạch chân; lõi vẫn kiểm
  phần trình duyệt tự điền trước khi xoá (#103).
- Tên các tab trong cửa sổ cài đặt không còn bị cắt ở cỡ cửa sổ mặc định: thanh tiêu đề bỏ chữ "Ngó Sen", tab
  "Kiểm tra máy" thành "Kiểm tra", và Giới thiệu chuyển vào menu ☰ thành hộp thoại "Giới thiệu Ngó Sen" (#95).
- Cửa sổ cài đặt xếp các mục ở thanh bên trái như Cài đặt của GNOME, tên mục không còn bị cắt khi thu hẹp
  cửa sổ; cửa sổ hẹp thì chỉ hiện một bên, có nút quay lại (#102).
- Tab Kiểm tra báo đúng hơn: fcitx5 đang giữ bộ gõ thì nói thẳng thế thay vì bảo chạy IBus; extension sửa
  lỗi GNOME 50.0–50.3 được kiểm cả khi chỉ vài app chọn Gõ Sen; nguồn nhập đang dùng không phải Ngó Sen thì nhắc
  phím đổi nguồn mà không tính là bước phải sửa; app X11 đi qua fcitx5 được gọi đúng tên; kết quả chép ra ghi số
  app chọn cách gõ riêng (#96).
- Chuyển từ bản fcitx5 sang: tab Kiểm tra tìm biến môi trường, mục tự chạy, biểu tượng ẩn và lựa chọn im-config mà
  lệnh cài fcitx5 để lại, kể cả khi fcitx5 đang giữ bộ gõ, và có nút xoá những tệp còn y nguyên (có Hoàn tác); tệp
  đã sửa tay thì chỉ ra đường dẫn. Hộp thoại "Chuyển sang bản fcitx5" bỏ câu hứa sai, nói rõ cách làm trên từng
  distro và có nút sao lưu trước; README thêm mục chuyển qua lại hai bản (#99).
- Mục 1.2.0-1 trong lịch sử gói deb và rpm ghi đúng thứ Hai 09/11/2026; rpmbuild hết cảnh báo ngày sai, và
  bộ kiểm phiên bản trước khi phát hành giờ bắt lỗi thứ sai (#93).
- Chữ cũ từ trước 1.2.0 được sửa: mô tả gói và trang AppStream nói Gõ Sen là mặc định và Ctrl+Shift đổi Anh/Việt,
  mẫu báo lỗi hỏi Gõ Sen hay gạch chân, Cứu chữ ghi rõ chỉ chạy ở phiên X11, từ điển trống ghi "Chưa có từ nào."
  thay vì "0 từ" (#97).

## [1.2.0-1] — 09/11/2026

Gõ Sen là mặc định và nhớ cách gõ chọn riêng cho từng app; nhấp Ctrl+Shift đổi Anh/Việt; thêm Cứu chữ, Cứu dấu,
gõ tắt khi tiếng Anh, sao lưu và khôi phục, tab Keymap, menu phím ` và tab "Kiểm tra máy" như bản fcitx5; trên
Wayland biết app đang gõ qua portal của GNOME. Dùng lõi Ngó Sen `ngosen-1.9.0-1`. Tải gói ở
[release ibus-ngosen-1.2.0-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.2.0-1).

### Thêm

- Nhấp Ctrl+Shift để đổi Anh/Việt như UniKey, ngay trong Ngó Sen: đổi cho mọi app cùng lúc, nhớ cả khi khởi động
  lại; thanh trên cùng hiện V hoặc E và menu có dòng "Tiếng Việt" có ✔ hoặc ✖ như các tuỳ chọn khác để bấm. Cửa
  sổ cài đặt cho đổi sang Shift+Alt hoặc tắt phím này; Super+Space vẫn đổi nguồn nhập như cũ. Ô mật khẩu luôn gõ
  tiếng Anh (#50, #61).
- Chọn "Phím khác…" trong cửa sổ cài đặt để tự bấm tổ hợp phím chuyển Anh/Việt; phím tắt GNOME đã dùng, phím
  đơn và Shift kèm một phím bị từ chối (#51).
- Sao lưu và khôi phục cài đặt, gõ tắt, bảng phím, từ điển và trạng thái Anh/Việt từ menu của cửa sổ cài đặt, cùng
  tệp JSON với bản fcitx5 nên chuyển qua lại được giữa hai bản. Khôi phục kiểm cả tệp trước khi ghi, báo trước những
  gì bản IBus không giữ được (chế độ emoji, tắt tiếng Việt theo app, phím chuyển chỉ một phím) và có nút Hoàn tác trả lại
  đúng như cũ; Ngó Sen đang chạy đổi Anh/Việt theo bản sao lưu ngay (#54).
- Cứu dấu: khi bật "Gõ Sen ở app cho phép", bấm chuột ngay sau một chữ rồi gõ phím dấu để sửa dấu chữ đó (chao,
  f → chào); Tab hay Esc trả lại phím vừa gõ. Bôi đen chữ rồi gõ phím dấu cũng được, nhưng chỉ ở app X11: app đi
  qua GNOME Shell gõ chữ trên vùng bôi đen bằng gạch chân (#52).
- Cứu chữ, bật sẵn như bản fcitx5: lỡ gõ tiếng Anh rồi bấm phím chuyển về tiếng Việt thì Ngó Sen gõ lại chữ vừa
  gõ có dấu (vieetj → việt); Tab hay Esc trả lại như cũ. Chữ không chắc là tiếng Việt thì chỉ hiện gợi ý, Enter
  hoặc bấm vào gợi ý để nhận. Hiện chỉ chạy trên phiên X11, nơi Ngó Sen thấy được cú bấm chuột dời con trỏ; trên
  Wayland và ở ô địa chỉ của trình duyệt thì chưa. Ai đã cài sẽ thấy tính năng này bật sau khi cập nhật; tắt được
  trong cửa sổ cài đặt (#76, #78).
- Menu phím ` nhớ Gõ Sen hay gạch chân riêng cho từng app như bản fcitx5, thay vì đổi cho mọi app cùng lúc; mục
  mới "Chế độ gõ mặc định" (phím r) bỏ lựa chọn riêng của app đó. App chưa nhận ra tên thì vẫn đổi cách gõ chung
  (#87).
- Sao lưu và khôi phục mang theo cả cách gõ chọn riêng cho từng app, cùng tệp với bản fcitx5; luật tắt tiếng Việt
  hay chọn emoji theo app vẫn được giữ lại cho bản fcitx5 (#88).
- Hai dấu cách thành ". " và -- thành "—", như bản fcitx5: bật trong cửa sổ cài đặt, mục "Gõ nhanh"; mặc định
  tắt (#77).
- Gõ tắt cả khi đang gõ tiếng Anh, như bản fcitx5: gõ "ko" rồi dấu cách vẫn ra "không"; bật trong cửa sổ cài đặt,
  mục gõ tắt; mặc định tắt. Ai đã cài bản trước cũng nhận lựa chọn của bản fcitx5 cho tuỳ chọn này và cho hai dấu
  cách, -- (#79).
- Cửa sổ cài đặt có tab "Kiểm tra máy": kiểm IBus, nguồn nhập và biến môi trường, sửa vài bước bằng một
  nút (chạy hay khởi động lại IBus, thêm Ngó Sen vào nguồn nhập), chép kết quả để gửi báo lỗi (#46).
- Tab "Kiểm tra máy" báo thêm hai bước trên GNOME: khi dùng Gõ Sen trên GNOME 50.0–50.3, extension sửa lỗi có đang
  chạy không, kèm nút bật; trên Wayland, máy có thiếu xdg-desktop-portal-gnome không, vì thiếu nó thì Ngó Sen không
  biết đang gõ trong app nào (#86).
- Cửa sổ cài đặt có tab "Keymap" để thêm, sửa, xoá phím của keymap tuỳ chỉnh (dùng với kiểu gõ Custom) và
  nạp sẵn bảng phím Telex, VNI, VIQR… như bản fcitx5; không cần sang bản fcitx5 để soạn nữa (#53).
- Bấm ` để mở menu chế độ gõ như bản fcitx5: 1 chọn Gõ Sen, q chọn gạch chân cho app đang dùng, e chọn tiếng Anh
  cho mọi app. Bấm ` hai lần để gõ ra `; lúc gõ tiếng Anh ` gõ như thường, kiểu gõ VIQR hay keymap tuỳ chỉnh dùng phím
  nào để bỏ dấu thì phím đó vẫn bỏ dấu. Cửa sổ cài đặt cho đổi phím mở menu sang Shift+~ như ibus-unikey hoặc
  tắt, và đổi phím của từng chế độ (#55).
- Bấm chuột vào một mục của menu ` để chọn chế độ, hoặc dùng mũi tên trên bảng menu; bản IBus cũng hiện được
  bảng chọn của Ngó Sen, để dành cho các tính năng sắp bật (#74).
- Trên Wayland, Ngó Sen biết app đang gõ qua GNOME Shell là app nào, đọc từ portal của GNOME như fcitx5 5.1.22,
  không cần extension; app Flatpak mang tên như khi cài thường. Nhờ vậy các luật riêng từng app của lõi chạy cả ở
  bản IBus: Alacritty không bị gửi ký tự DEL mà nó sẽ dán ra thành rác, ô tìm kiếm của GNOME không sửa dấu hay gõ
  lại chữ (#81).

### Thay đổi

- Ngó Sen gõ thẳng (Gõ Sen) theo mặc định như bản fcitx5, thay cho gạch chân, và tuỳ chọn hết ghi "thử nghiệm".
  Người dùng bản cũ được chuyển sang Gõ Sen một lần khi cập nhật; muốn gạch chân thì bấm ` rồi chọn gạch chân cho
  app đang dùng, hoặc tắt Gõ Sen trong cửa sổ cài đặt cho mọi app chưa chọn riêng (#89).
- Dùng lõi Ngó Sen `ngosen-1.9.0-1`: Cứu chữ hết xoá nhầm chữ khi bấm chuột sang chỗ khác ngay sau phím chuyển
  Anh/Việt (ngosen/ngosen#605), gõ tắt khi đang tiếng Anh hết chèn cụm chữ sau chữ tắt (ngosen/ngosen#604); #69.
- Lõi `ngosen-1.9.0-1`: trong terminal như Ptyxis và GNOME Terminal, Ngó Sen sửa chữ đã
  gõ bằng ký tự DEL gửi kèm chữ mới, terminal xoá bằng nó như khi bấm BackSpace (ngosen/ngosen#620; #80).
- Ở game SDL trong phiên X11, Ngó Sen xoá chữ bằng phím BackSpace bấm qua XTEST như bản fcitx5, thay vì commit
  chữ mới khi chưa xoá được chữ cũ; gói Debian và openSUSE thêm `libxcb-xtest` (#69).
- Ở ô đi qua GNOME Shell, khi gõ gạch chân hay đang tiếng Anh mà GNOME 50.0–50.3 chưa chạy extension, Ngó Sen
  xoá chữ đã gõ qua chữ quanh con trỏ thay vì chuyển phím BackSpace mà GNOME bỏ đi; cần cho Cứu chữ, hai lần
  cách thành ". " và gõ tắt khi tiếng Anh sắp có (#72).

### Sửa

- Gõ -- trong terminal hay ô địa chỉ vẫn giữ nguyên khi bật "Hai gạch nối thành gạch dài", nên "git push --force"
  không còn thành "git push —force" (ngosen/ngosen#625, #83).
- Gõ Sen hiện chữ ngay khi thêm dấu trong Ptyxis, GNOME Console và GNOME Terminal (ngosen/ngosen#630, #83).
- Đổi cài đặt khi đang gõ dở một chữ, từ menu hay cửa sổ cài đặt, không còn làm mất chữ đó: cài đặt mới áp dụng
  khi gõ xong chữ (#83).
- Nhận ra Firefox cài từ gói Fedora, Mullvad Browser và các bản Flatpak của Firefox trên GNOME, để chữ gõ trong
  ô địa chỉ không lẫn với autofill (ngosen/ngosen#634, lõi `ngosen-1.9.0-1`).

## [1.1.4-1] — 08/11/2026

Gõ Sen trên GNOME xoá chữ bằng phím BackSpace khi app báo chữ cũ, kèm extension cho GNOME 50.0–50.3; Gõ Sen
hết nuốt phím mũi tên, Home, End bấm ngay sau một chữ. Dùng lõi Ngó Sen `ngosen-1.8.1-1`. Tải gói ở
[release ibus-ngosen-1.1.4-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.1.4-1).

### Thay đổi

- Dùng lõi Ngó Sen `ngosen-1.8.1-1`: Gõ Sen hết nuốt hoặc đảo thứ tự phím mũi tên, Home, End bấm ngay sau một chữ
  (ngosen/ngosen#591), cùng các sửa của lõi cho Firefox và Chrome trên GNOME; cửa sổ cài đặt dùng font của hệ thống
  thay cho Xanh Mono; tuỳ chọn "Không phải đầu từ" đổi tên thành "Trong từ" như bản fcitx5 (#67).

### Sửa

- Gõ Sen trên GNOME: Firefox và các app báo được chữ quanh con trỏ nay gõ thẳng chính xác hơn, vì Ngó Sen xoá được bằng phím BackSpace khi bản chữ app báo đã cũ. GNOME 50.0–50.3 (như Ubuntu 26.04) làm mất phím này nên gói kèm một extension sửa lỗi, và Ngó Sen tự bật extension một lần sau khi đăng nhập lại; chưa chạy thì chữ gạch chân. Gói này nay không cài chung được với `fcitx5-ngosen` vì cả hai cài cùng extension (#64).

### Tài liệu

- Cài và gỡ nay bằng trình quản lý gói, từ release của repo này. `install.sh` của `ngosen/ngosen` không còn tuỳ chọn `--ibus`.
- Kho APT, pacman, zypper của Ngó Sen phát lại gói này từ lõi `ngosen-1.8.2-1` (ngosen/ngosen#598); README chỉ cách thêm kho để `apt upgrade`, `pacman -Syu`, `zypper up` tự lên version mới (#65).

## [1.1.3-1] — 01/11/2026

Gõ Sen chạy bằng lõi Ngó Sen và gõ thẳng cả ở app X11, kitty trên X11 gõ được tiếng Việt, menu nguồn nhập đóng
đều đặn sau mỗi lần bấm. Dùng lõi Ngó Sen `ngosen-1.7.5-1`. Tải gói ở
[release ibus-ngosen-1.1.3-1](https://github.com/ngosen/ibus-ngosen/releases/tag/ibus-ngosen-1.1.3-1).

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
