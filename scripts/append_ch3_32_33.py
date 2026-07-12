# -*- coding: utf-8 -*-
section = """

---

## 3.2 Cấu hình và khởi động hệ thống

Sau khi image Docker đã được build thành công (mục 3.1), bước tiếp theo là cấu hình các dịch vụ bên ngoài mà Miniclaw cần kết nối — bao gồm Google Workspace và OpenAI (ChatGPT) — rồi khởi động toàn bộ hệ thống. Trật tự khuyến nghị là: thiết lập Google Workspace trước (vì cần thao tác bên trong container khi đang chạy), sau đó mới điền API key ChatGPT và token Telegram qua giao diện Dashboard.

---

### 3.2.1 Thiết lập Google Workspace

Tích hợp Google Workspace (Gmail, Google Sheets, Google Calendar) cho phép Miniclaw gửi email, ghi dữ liệu bảng tính, và truy vấn lịch thay mặt người dùng. Quá trình thiết lập gồm hai giai đoạn: chuẩn bị file xác thực từ Google Cloud Console và đăng nhập tài khoản bên trong container.

#### a) Tạo OAuth2 Client trên Google Cloud Console

Truy cập [console.cloud.google.com](https://console.cloud.google.com) và thực hiện các bước sau:

**Bước 1 — Tạo dự án mới:**
Nếu chưa có dự án, chọn **Select a project → New Project**, đặt tên tùy ý (ví dụ: `miniclaw-bot`) và nhấn **Create**.

**Bước 2 — Bật các API cần thiết:**
Vào **APIs & Services → Library**, tìm kiếm và bật lần lượt các API sau:
- **Gmail API**
- **Google Sheets API**
- **Google Calendar API**
- **Google Drive API**
- **Google Docs API**

**Bước 3 — Tạo OAuth2 Client ID:**
Vào **APIs & Services → Credentials → Create Credentials → OAuth client ID**. Chọn loại ứng dụng là **Desktop app**, đặt tên và nhấn **Create**. Hệ thống sẽ hiển thị Client ID và Client Secret — nhấn **Download JSON** để tải file xác thực về máy.

**Bước 4 — Cấu hình màn hình đồng ý (OAuth Consent Screen):**
Vào **OAuth consent screen**, chọn chế độ **External** (hoặc **Internal** nếu dùng Google Workspace tổ chức), điền tên ứng dụng và email. Ở phần **Test users**, thêm địa chỉ Gmail sẽ dùng để đăng nhập — bước này bắt buộc ở chế độ External khi ứng dụng chưa được Google xác minh.

[GỢI Ý CHỤP MÀN HÌNH: (1) Chụp trang **APIs & Services → Library** sau khi đã bật Gmail API — thấy nút trạng thái "Enabled" màu xanh. (2) Chụp trang **Credentials** hiển thị mục OAuth 2.0 Client IDs vừa tạo với tên ứng dụng và nút Download. (3) Chụp trang **OAuth consent screen** phần Test users đã có email được thêm vào.]

#### b) Đặt file credentials vào thư mục secrets

Đổi tên file JSON vừa tải về thành `gog-credentials.json` và đặt vào thư mục `secrets/` cùng chỗ với ba file Docker (`Dockerfile`, `docker-compose.yml`, `.env`):

```
docker/
├── Dockerfile
├── docker-compose.yml
├── .env
└── secrets/
    └── gog-credentials.json   ← đặt file vào đây
```

Thư mục `secrets/` được khai báo trong `docker-compose.yml` để mount trực tiếp vào đường dẫn `/root/.miniclaw/workspace/secrets` bên trong container. Nhờ đó, công cụ `gog` có thể đọc file credentials này khi thực hiện xác thực.

[GỢI Ý CHỤP MÀN HÌNH: Mở File Explorer, chụp lại thư mục `docker/secrets/` hiển thị file `gog-credentials.json` đã được đặt đúng vị trí.]

#### c) Khởi động container và đăng nhập Google

Sau khi đã có file credentials, khởi động container (nếu chưa chạy):

```powershell
docker compose up -d
```

Sau đó mở terminal bên trong container đang chạy:

```powershell
docker exec -it miniclaw-launcher bash
```

Bên trong container, chạy script xác thực Google với địa chỉ Gmail của bạn:

```bash
gog-setup your@gmail.com
```

Script `gog-setup.sh` sẽ tự động thực hiện hai thao tác tuần tự:
1. Đăng ký file `gog-credentials.json` với công cụ `gog` bằng lệnh `gog auth credentials`.
2. Kích hoạt luồng đăng nhập OAuth2 bằng lệnh `gog auth add --manual` và in ra một URL đăng nhập.

Sao chép URL đó, mở trên trình duyệt máy tính, đăng nhập bằng tài khoản Gmail đã đăng ký ở bước Test users, và cấp quyền truy cập cho các dịch vụ được liệt kê (Gmail, Calendar, Drive, Docs, Sheets). Sau khi đồng ý, trình duyệt sẽ chuyển đến một trang báo lỗi kết nối — đây là bình thường vì không có server cục bộ nhận callback trong môi trường Docker. Sao chép toàn bộ URL trên thanh địa chỉ lúc đó và dán vào terminal khi được hỏi.

Nếu thành công, terminal sẽ hiển thị thông báo xác thực hoàn tất. Kiểm tra kết nối bằng lệnh:

```bash
gog calendar calendars
```

Lệnh này trả về danh sách lịch trong tài khoản Google — nếu hiển thị được là tích hợp đã hoạt động.

[GỢI Ý CHỤP MÀN HÌNH: (1) Chụp cửa sổ terminal bên trong container đang hiển thị URL đăng nhập Google do `gog-setup` sinh ra. (2) Chụp trang đồng ý quyền truy cập của Google trên trình duyệt, thấy danh sách các quyền (Gmail, Calendar, Sheets...) đang được yêu cầu. (3) Chụp terminal sau khi chạy `gog calendar calendars` — thấy tên lịch (thường là địa chỉ Gmail) trả về — xác nhận kết nối thành công.]

---

### 3.2.2 Cấu hình ChatGPT và kênh Telegram

Khác với Google Workspace cần thao tác trong terminal, cấu hình API key ChatGPT và token Telegram được thực hiện trực tiếp qua giao diện Web Dashboard — không cần chỉnh sửa file thủ công.

#### a) Truy cập Web Dashboard

Mở trình duyệt và vào địa chỉ:

```
http://localhost:18801
```

Trang đăng nhập Dashboard sẽ hiện ra và yêu cầu nhập **Dashboard Token**. Token này được sinh tự động khi container khởi động lần đầu và in ra trong log của container. Để xem token, chạy lệnh sau ở terminal máy chủ:

```powershell
docker logs miniclaw-launcher | findstr "token"
```

Hoặc có thể đặt token cố định bằng cách thêm vào file `.env` trước khi khởi động:

```
MINICLAW_LAUNCHER_TOKEN=your_token_here
```

Sau khi đăng nhập, Dashboard hiển thị giao diện quản trị đầy đủ với trạng thái hệ thống, log, và các mục cấu hình.

[GỢI Ý CHỤP MÀN HÌNH: (1) Chụp trang đăng nhập Dashboard tại `http://localhost:18801` với ô nhập token. (2) Chụp giao diện Dashboard chính sau khi đăng nhập — thấy trạng thái Gateway (chưa chạy hoặc đã chạy) và các mục điều hướng.]

#### b) Nhập API key OpenAI (ChatGPT)

Trong Dashboard, truy cập mục **Settings** hoặc **Config** và tìm phần cấu hình nhà cung cấp AI (Providers). Điền **OpenAI API Key** vào trường tương ứng. API key có định dạng bắt đầu bằng `sk-...` và được tạo tại [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

Về mô hình AI, hệ thống mặc định dùng `openai-codex/gpt-5.4` với các thông số đã trình bày ở mục 2.2.1.d. Nếu muốn thay đổi mô hình, chỉnh trường `model` trong phần cấu hình Agent — ví dụ `openai/gpt-4o` cho mô hình GPT-4o tiêu chuẩn.

Tương đương với việc chỉnh thủ công trường `providers.openai.apiKey` và `agents.defaults.model` trong file `~/.miniclaw/config.json` bên trong container (hoặc trong named volume `miniclaw-data`).

[GỢI Ý CHỤP MÀN HÌNH: Chụp màn hình phần cấu hình Providers trong Dashboard, thấy trường OpenAI API Key đã được điền (che bớt phần giữa key để bảo mật, chỉ để lộ `sk-...` ở đầu và vài ký tự cuối).]

#### c) Cấu hình kênh Telegram

Để bot có thể nhận và gửi tin nhắn qua Telegram, cần có **Bot Token** do Telegram cấp. Token này được tạo thông qua **BotFather** — một bot quản lý chính thức của Telegram:

1. Mở Telegram, tìm kiếm `@BotFather` và bắt đầu chat.
2. Gửi lệnh `/newbot`, đặt tên hiển thị và username cho bot (username phải kết thúc bằng `bot`, ví dụ: `miniclaw_bot`).
3. BotFather trả về một **Bot Token** có dạng `123456789:AAF...`. Sao chép toàn bộ chuỗi này.

Trong Dashboard, tìm phần cấu hình kênh Telegram (Channels → Telegram) và điền token vào trường `token`. Ngoài ra, cần điền **Telegram User ID** của bản thân vào trường `allowFrom` để chỉ cho phép tài khoản của mình điều khiển bot. Để biết User ID của mình, nhắn tin cho bot `@userinfobot` trên Telegram — nó sẽ trả về ID số.

Cấu hình Telegram trong `config.json` tương đương như sau:

```json
"telegram": {
  "enabled": true,
  "token": "123456789:AAF...",
  "allowFrom": ["987654321"],
  "reactEmoji": "👀",
  "groupPolicy": "mention",
  "streaming": true
}
```

Trường `reactEmoji` là biểu tượng cảm xúc bot dùng để phản ứng vào tin nhắn nhận được (báo hiệu đang xử lý). Trường `groupPolicy: "mention"` quy định bot chỉ phản hồi trong nhóm khi được @mention.

[GỢI Ý CHỤP MÀN HÌNH: (1) Chụp màn hình cuộc trò chuyện với @BotFather — thấy tin nhắn trả về chứa Bot Token (che bớt phần giữa). (2) Chụp phần cấu hình Telegram trong Dashboard với trường token và allowFrom đã được điền.]

#### d) Lưu cấu hình và khởi động Gateway

Sau khi điền đầy đủ API key và token, nhấn **Save** trong Dashboard để ghi các thay đổi vào file `config.json`. Tiếp theo, bấm nút **Start** trong phần Gateway để khởi động nhân xử lý chính của hệ thống.

Dashboard sẽ hiển thị trạng thái chuyển từ `stopped` → `starting` → `running` và log khởi động xuất hiện theo thời gian thực. Khi thấy dòng thông báo Telegram bot đã kết nối (ví dụ: `Telegram bot @miniclaw_bot connected`), hệ thống đã sẵn sàng hoạt động.

[GỢI Ý CHỤP MÀN HÌNH: Chụp Dashboard lúc Gateway đang ở trạng thái `running` — thấy đèn xanh hoặc chữ "running", cùng với các dòng log xác nhận bot Telegram đã kết nối thành công.]

---

## 3.3 Đóng gói và vận hành hệ thống

Sau khi hoàn tất cấu hình, hệ thống Miniclaw chạy hoàn toàn tự động bên trong container Docker. Phần này mô tả cách vận hành thường ngày: khởi động, dừng, cập nhật và theo dõi trạng thái.

#### a) Khởi động và dừng hệ thống

**Khởi động toàn bộ hệ thống:**

```powershell
docker compose up -d
```

Tham số `-d` (detached) cho container chạy nền — terminal trả về ngay lập tức, hệ thống tiếp tục hoạt động độc lập. Container được cấu hình với `restart: unless-stopped`, nghĩa là sẽ tự khởi động lại sau khi máy chủ reboot hoặc khi container bị crash — trừ khi người dùng chủ động dừng bằng lệnh dưới đây.

**Dừng hệ thống:**

```powershell
docker compose down
```

Lệnh này dừng và xóa container, nhưng **không xóa** named volume `miniclaw-data` — toàn bộ cấu hình và lịch sử hội thoại được giữ nguyên cho lần khởi động tiếp theo.

**Xem trạng thái container:**

```powershell
docker compose ps
```

**Xem log theo thời gian thực:**

```powershell
docker compose logs -f miniclaw-launcher
```

[GỢI Ý CHỤP MÀN HÌNH: Chụp terminal sau lệnh `docker compose ps` — thấy container `miniclaw-launcher` ở trạng thái `Up` với thời gian hoạt động và cổng được mở (`18801`, `18790`, `1455`).]

#### b) Kiểm tra hệ thống hoạt động qua Telegram

Sau khi Gateway đang chạy, mở Telegram và gửi tin nhắn đến bot vừa tạo. Bot sẽ phản ứng bằng emoji 👀 ngay khi nhận được tin (xác nhận tin nhắn đã được nhận), sau đó trả lời sau vài giây. Một số lệnh kiểm tra nhanh:

- `/status` — Bot trả về trạng thái hoạt động hiện tại.
- `/help` — Liệt kê các lệnh có sẵn.
- `Tìm bài báo về perovskite solar cell` — Kiểm tra tích hợp ArXiv.
- `Đọc email mới nhất của tôi` — Kiểm tra tích hợp Gmail (chỉ hoạt động sau bước 3.2.1).

[GỢI Ý CHỤP MÀN HÌNH: (1) Chụp màn hình Telegram — thấy bot đã phản ứng emoji 👀 vào tin nhắn gửi đến và trả lời nội dung. (2) Chụp kết quả lệnh `/status` trả về thông tin trạng thái hệ thống (model đang dùng, workspace path, thời gian chạy).]

#### c) Cập nhật hệ thống lên phiên bản mới

Khi có cập nhật mã nguồn trên GitHub, quy trình cập nhật gồm các bước:

```powershell
# Dừng container hiện tại
docker compose down

# Build lại image (tự động pull code mới từ GitHub)
docker build -t miniclaw . --no-cache

# Khởi động lại với image mới
docker compose up -d
```

Tham số `--no-cache` buộc Docker build lại từ đầu, đảm bảo lấy code mới nhất từ nhánh `main` của GitHub. Toàn bộ cấu hình và dữ liệu trong named volume `miniclaw-data` được giữ nguyên qua quá trình cập nhật.

#### d) Giám sát qua Web Dashboard

Dashboard tại `http://localhost:18801` cung cấp giao diện theo dõi trực quan thường xuyên hơn so với terminal:

- **Tab Gateway**: Trạng thái running/stopped, nút Start/Stop/Restart, log 400 dòng gần nhất theo thời gian thực.
- **Tab Sessions**: Lịch sử toàn bộ phiên hội thoại, có thể xem lại nội dung từng cuộc trò chuyện.
- **Tab Skills**: Danh sách các skill đã cài (arxiv-watcher, goggoogleworkspace...) và trạng thái khả dụng.
- **Tab Config**: Xem và chỉnh sửa `config.json` trực tiếp trên giao diện web mà không cần vào terminal.

Đây là cách vận hành thường ngày được khuyến nghị: Gateway chạy nền liên tục, người dùng tương tác qua Telegram, và Dashboard dùng để kiểm tra khi cần theo dõi hoặc điều chỉnh cấu hình.

[GỢI Ý CHỤP MÀN HÌNH: Chụp toàn màn hình Dashboard khi hệ thống đang chạy bình thường — thấy rõ trạng thái Gateway "running", khu vực log với các dòng hoạt động gần nhất, và thanh điều hướng các tab (Sessions, Skills, Config...). Đây là ảnh minh hoạ tổng quan giao diện vận hành của hệ thống.]
"""

with open("Content.md", "a", encoding="utf-8") as f:
    f.write(section)

print("done, lines added:", section.count("\\n"))
