# Miniclaw

**Miniclaw** là trợ lý cá nhân nhẹ, kết nối các mô hình AI (mặc định là GPT) với các nền tảng nhắn tin như Telegram và Web, tích hợp thêm công cụ như Gmail, Google Calendar.

---

## Cách 1 — Cài đặt thủ công (Git Clone)

> Yêu cầu: Python 3.10+, đã cài Git

Mở cmd từ máy tính, gõ các lệnh sau:

```cmd
git clone https://github.com/tringv8/miniclaw.git
cd miniclaw
pip install -r requirements.txt
miniclaw-launcher
```

Sau khi chạy, mở trình duyệt tại: **http://localhost:18801**


### Các lệnh CLI

| Lệnh | Chức năng |
|------|-----------|
| `miniclaw-launcher` | Mở giao diện web quản lý Miniclaw |
| `miniclaw onboard` | Thiết lập cấu hình ban đầu (chạy lần đầu) |
| `miniclaw status` | Xem trạng thái các dịch vụ đang chạy |
| `miniclaw start` | Khởi động Gateway |
| `miniclaw stop` | Dừng Gateway |
| `miniclaw restart` | Khởi động lại Gateway |
| `miniclaw logs` | Xem log hệ thống |
| `miniclaw -h` | Xem toàn bộ lệnh và trợ giúp |

---

## Cách 2 — Chạy bằng Docker

> Yêu cầu: [Docker Desktop](https://docs.docker.com/get-docker/) đã cài và đang chạy. Không cần clone toàn bộ dự án.

### Bước 1 — Tải 3 file cấu hình docker

Tải thư mục `docker/` từ link sau (dùng [DownGit](https://downgit.github.io/#/home)):

```
https://github.com/tringv8/miniclaw/tree/main/docker
```

Dán link trên vào DownGit → nhấn **Download** → giải nén ra một thư mục.

### Bước 2 — Đổi tên file `.env.example` thành `.env`


### Bước 3 — Build và chạy

Mở cmd từ thư mục chứa 3 file docker trên, gõ các lệnh sau:

```cmd
docker build -t miniclaw .
docker compose up -d
```

Sau đó mở Docker Desktop và xem **miniclaw-launcher** trong tab Containers.

### Một số lệnh Docker hữu ích

| Lệnh | Chức năng |
|------|-----------|
| `docker compose up -d` | Khởi động Miniclaw |
| `docker compose down` | Dừng Miniclaw |
| `docker compose logs -f` | Xem log realtime |
| `docker build -t miniclaw --no-cache .` | Cập nhật lên phiên bản mới |

---

## Thiết lập Telegram Bot

1. Mở Telegram, tìm **@BotFather**
2. Gửi lệnh `/newbot` → đặt tên và username cho bot
3. Sao chép **token** nhận được → dán vào `Bot Token` trên trang web


### Cấu hình bot trên giao diện web

Sau khi chạy Miniclaw, vào **Channels → Telegram**:

- **HTTP Proxy**: để **trống**
- **Allow from**: điền `*` — cho phép bất kỳ ai nhắn tin với bot

---


## Lần đầu chat với bot

Khi mở bot lần đầu, hãy giới thiệu bản thân để bot hiểu cách làm việc với bạn. Dưới đây là mẫu tham khảo:

> Bạn là **[tên bạn muốn đặt cho Miniclaw]**, còn mình là **[tên bạn muốn bot gọi]**. Bạn là nữ trợ lý thông minh của mình. Bạn gọi mình là **[ ]**, xưng hô là **[em/anh/cô/chú]**.
>
> Sử dụng múi giờ: Việt Nam
> Giao tiếp bằng: Tiếng Việt
>
> **Phong cách:** Sắc sảo, trực tiếp và khô khan. Không dùng từ ngữ sáo rỗng kiểu công ty, không dùng câu nói thừa thãi. Nếu có điều gì không ổn hoặc tôi đang làm phức tạp hóa vấn đề, hãy nói thẳng. Hãy có ý kiến riêng, đừng chỉ đồng ý với tôi. Giữ cho câu nói ngắn gọn trừ khi tôi yêu cầu bạn đi sâu hơn. Hãy nghĩ đến "đồng nghiệp đáng tin cậy đã làm việc với tôi nhiều năm" chứ không phải "trợ lý nhiệt tình". Hài hước nhẹ nhàng thì được, nhưng đừng gượng ép.
>
> **Emoji:** ⚡️
>
> **Tôi thích được hỗ trợ như thế nào:**
> Mặc định là ngắn gọn. Tôi sẽ yêu cầu bạn bổ sung thêm nếu tôi cần.
> Khi tôi giao cho bạn một nhiệm vụ, hãy làm ngay – đừng hỏi tôi 5 câu hỏi làm rõ trước trừ khi bạn thực sự không thể tiếp tục nếu không có câu trả lời.
> Khi tôi đưa cho bạn một tài liệu hoặc dàn ý, hãy giả định rằng tôi muốn bạn làm việc với nó, chứ không phải tóm tắt lại cho tôi.
> Hãy chủ động báo cáo các vấn đề. Nếu bạn thấy lỗi, sự không nhất quán hoặc điều gì đó mà tôi có thể đã bỏ sót, hãy cho tôi biết.

---

## Xác thực Google (Gmail, Calendar)

Miniclaw hỗ trợ tích hợp Gmail và Google Calendar. Trước tiên tải file `.json` từ [Google Console](https://console.cloud.google.com/).

**1. Đặt file vào thư mục `secrets/`** (cùng chỗ với 3 file Docker):

Đổi tên file thành `gog-credentials.json` rồi bỏ vào thư mục `secrets/`.

**2. Mở terminal trong container** (Docker Desktop → miniclaw-launcher → **Open in terminal**) và chạy:

```bash
gog-setup your@gmail.com
```

Script sẽ tự hướng dẫn từng bước — bạn chỉ cần mở URL trong trình duyệt, đăng nhập Google, rồi dán URL redirect trở lại terminal khi được hỏi.

Kiểm tra thành công:
```bash
gog calendar calendars
```