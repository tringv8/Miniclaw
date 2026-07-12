# -*- coding: utf-8 -*-
section = """

---

## CHƯƠNG 3: TRIỂN KHAI THỰC NGHIỆM HỆ THỐNG MINICLAW

### 3.1 Cài đặt môi trường và công cụ

#### a) Triết lý triển khai — "Chỉ cần 3 file"

Một trong những ưu điểm thiết kế quan trọng của Miniclaw là cách tiếp cận triển khai cực kỳ gọn nhẹ. Người dùng **không cần clone toàn bộ mã nguồn về máy**, không cần cài Python, không cần cài đặt thư viện thủ công. Toàn bộ hệ thống được đóng gói trong một Docker image — người dùng chỉ cần ba file để đưa hệ thống vào hoạt động:

| File | Vai trò |
|---|---|
| `Dockerfile` | Công thức build image — tự động tải mã nguồn từ GitHub trong lúc build |
| `docker-compose.yml` | Định nghĩa cách chạy các dịch vụ, cổng mạng, và vị trí lưu dữ liệu |
| `.env` | Chứa các thông tin cấu hình nhạy cảm (API key, token) |

Cả ba file này đều nằm trong thư mục `docker/` của mã nguồn. Hình thức triển khai này đảm bảo tính nhất quán giữa các máy khác nhau — hệ thống sẽ hoạt động giống nhau dù chạy trên Windows, macOS hay Linux.

#### b) Yêu cầu tiên quyết

Trước khi bắt đầu, máy tính cần có:

1. **Docker Desktop** (với Windows hoặc macOS) hoặc **Docker Engine** (với Linux) đã được cài đặt và đang chạy. Docker Desktop có thể tải miễn phí tại [docs.docker.com/get-docker](https://docs.docker.com/get-docker/).
2. **Kết nối Internet** trong lần build đầu tiên — Docker sẽ tự tải mã nguồn Miniclaw từ GitHub và cài đặt tất cả thư viện Python cần thiết.

Không yêu cầu bất kỳ phần mềm nào khác. Cụ thể, người dùng **không cần** cài Python, Node.js, hay bất kỳ công cụ lập trình nào trên máy chủ — tất cả đã được đóng gói bên trong container.

[GỢI Ý CHỤP MÀN HÌNH: Mở Docker Desktop, chụp lại màn hình chính hiển thị trạng thái "Engine running" (biểu tượng Docker màu xanh ở góc dưới bên trái) để minh hoạ điều kiện tiên quyết đã được đáp ứng.]

#### c) Chuẩn bị ba file cấu hình

**Bước 1 — Tải ba file về máy:**

Tạo một thư mục trống bất kỳ (ví dụ: `miniclaw-deploy/`) rồi đặt vào đó ba file: `Dockerfile`, `docker-compose.yml`, và `.env.example` (sao chép từ thư mục `docker/` trong mã nguồn).

**Bước 2 — Tạo file `.env` từ mẫu:**

Trên Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

Trên macOS/Linux (Terminal):
```bash
cp .env.example .env
```

**Bước 3 — Điền thông tin vào file `.env`:**

Mở file `.env` bằng Notepad hoặc bất kỳ trình soạn thảo văn bản nào. File có cấu trúc như sau:

```
MINICLAW_REPO=https://github.com/tringv8/Miniclaw.git
MINICLAW_REF=main

MINICLAW_LAUNCHER_TOKEN=

TELEGRAM_BOT_TOKEN=

GOG_KEYRING_BACKEND=file
GOG_KEYRING_PASSWORD=password
```

Ở giai đoạn này, phần quan trọng nhất là để nguyên `GOG_KEYRING_BACKEND=file` — đây là chỉ thị bắt buộc khi chạy trong môi trường Docker, báo cho hệ thống lưu token Google vào file thay vì dùng cơ chế lưu khóa bí mật của hệ điều hành (vốn không tồn tại trong container). Các thông tin khác như `TELEGRAM_BOT_TOKEN` và `MINICLAW_LAUNCHER_TOKEN` có thể điền sau trong giao diện Web Dashboard.

[GỢI Ý CHỤP MÀN HÌNH: Mở file `.env` bằng Notepad hoặc VS Code, chụp lại nội dung đã điền (che đi phần giá trị nhạy cảm nếu cần) để minh hoạ bước chuẩn bị cấu hình.]

#### d) Build Docker Image

Mở terminal (PowerShell trên Windows, Terminal trên macOS/Linux), di chuyển vào thư mục chứa ba file vừa chuẩn bị, rồi chạy:

```powershell
docker build -t miniclaw .
```

Lệnh này kích hoạt quá trình build với các bước tuần tự được định nghĩa trong `Dockerfile`:

1. Lấy image nền `python3.12-bookworm-slim` (Debian Linux tối giản với Python 3.12 sẵn có).
2. Cài thêm các công cụ hệ thống cần thiết: `curl`, `git`, `tar`, `unzip`, và **Node.js 20** (dùng cho bridge WhatsApp).
3. Tự động `git clone` toàn bộ mã nguồn Miniclaw từ GitHub vào đường dẫn `/app` bên trong container.
4. Cài đặt tất cả thư viện Python (`uv pip install -r requirements.txt`).
5. Build bridge Node.js (`npm install && npm run build`).
6. Tải và cài đặt binary `gogcli` (công cụ dòng lệnh cho Google Workspace) phiên bản 0.12.0 vào `/usr/local/bin/gog`.
7. Sao chép script thiết lập Google (`gog-setup.sh`) vào container.

Lần build đầu tiên thường mất từ 5 đến 15 phút tùy tốc độ Internet, do cần tải nhiều gói phụ thuộc. Các lần build sau nhanh hơn đáng kể nhờ Docker lưu bộ nhớ đệm (cache) các lớp không thay đổi.

[GỢI Ý CHỤP MÀN HÌNH: Chụp lại cửa sổ terminal đang chạy lệnh `docker build`, đặc biệt là khi hiện các dòng log tải thư viện Python và cài gogcli. Chụp thêm dòng cuối cùng "Successfully built..." hoặc "Successfully tagged miniclaw:latest" để xác nhận build thành công.]

#### e) Kiểm tra image sau khi build

Sau khi build hoàn tất, kiểm tra image vừa tạo:

```powershell
docker images miniclaw
```

Đầu ra sẽ hiển thị tên image, tag (`latest`), ID, thời gian tạo, và kích thước. Kích thước image Miniclaw thường vào khoảng 1–1.5 GB do bao gồm Python, Node.js, tất cả thư viện và binary `gog`.

Ngoài ra, có thể kiểm tra image trong giao diện đồ họa của Docker Desktop tại tab **Images**.

[GỢI Ý CHỤP MÀN HÌNH: (1) Chụp lại terminal sau lệnh `docker images miniclaw` hiển thị image vừa build. (2) Mở Docker Desktop → tab Images, chụp lại dòng image `miniclaw` với kích thước và thời gian tạo.]

#### f) Cấu trúc dữ liệu bền vững — Named Volume

Trước khi khởi động hệ thống, cần hiểu cơ chế lưu dữ liệu của Miniclaw trong Docker. Toàn bộ cấu hình, lịch sử hội thoại, bộ nhớ Agent, và token đăng nhập được lưu trong một **named volume** (ổ đĩa ảo có tên) thay vì bên trong container:

```
miniclaw-data  →  ánh xạ tới  /root/.miniclaw  (bên trong container)
```

Khi container bị xóa hoặc image được cập nhật, dữ liệu trong named volume vẫn được giữ nguyên. Đây là cơ chế quan trọng đảm bảo người dùng không mất cấu hình hay lịch sử hội thoại khi cập nhật hệ thống lên phiên bản mới.

Ngoài ra, thư mục `secrets/` trên máy chủ được mount trực tiếp vào đường dẫn `/root/.miniclaw/workspace/secrets` bên trong container — đây là nơi đặt file `gog-credentials.json` để thiết lập tích hợp Google Workspace (trình bày chi tiết ở mục 3.2.1).

Tóm tắt quá trình cài đặt:

| Bước | Lệnh | Kết quả |
|---|---|---|
| Chuẩn bị cấu hình | Sao chép và chỉnh `.env` | File cấu hình sẵn sàng |
| Build image | `docker build -t miniclaw .` | Image `miniclaw:latest` được tạo |
| Kiểm tra | `docker images miniclaw` | Xác nhận image tồn tại |
| Khởi động | `docker compose up -d` | Hệ thống chạy nền (mục 3.2) |
"""

with open("Content.md", "a", encoding="utf-8") as f:
    f.write(section)
print("done")
