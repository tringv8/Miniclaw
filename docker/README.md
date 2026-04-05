# Chạy Miniclaw bằng Docker

> **Bạn không cần clone cả dự án về máy.**
> Chỉ cần 3 file dưới đây là đủ để cài và chạy Miniclaw hoàn toàn trong Docker:
>
> | File | Mục đích |
> |------|----------|
> | `Dockerfile` | Công thức build image — tự động `git clone` code từ GitHub trong lúc build |
> | `docker-compose.yml` | Định nghĩa các dịch vụ sẽ chạy |
> | `.env` | Cấu hình API key và các biến môi trường |
>
> Tải 3 file này về cùng 1 thư mục, làm theo các bước bên dưới là xong.

---

## Yêu cầu

- [Docker Desktop](https://docs.docker.com/get-docker/) (Windows / macOS) hoặc Docker Engine (Linux) đã được cài và đang chạy.
- Kết nối internet để build (Docker sẽ tự `git clone` từ GitHub).

---

## 1. Chuẩn bị

### 1.1 Vào thư mục `docker/`

```powershell
# Windows PowerShell
cd path\to\miniclaw\docker
```

```bash
# macOS / Linux
cd path/to/miniclaw/docker
```

### 1.2 Tạo file `.env` từ mẫu

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

### 1.3 Chỉnh file `.env`

Mở file `.env` bằng bất kỳ trình soạn thảo nào và điền các giá trị cần thiết:

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `ANTHROPIC_API_KEY` | ✅ | API key của Claude (lấy tại [console.anthropic.com](https://console.anthropic.com)) |
| `MINICLAW_REPO` | ❌ | URL repo để build. Mặc định: `https://github.com/tringv8/Miniclaw.git` |
| `MINICLAW_REF` | ❌ | Branch, tag hoặc commit cần build. Mặc định: `main` |
| `MINICLAW_LAUNCHER_TOKEN` | ❌ | Token bảo vệ Launcher UI. Để trống thì hệ thống tự sinh. |
| `TELEGRAM_BOT_TOKEN` | ❌ | Bot token nếu dùng tích hợp Telegram |

---

## 2. Build image

Lệnh sau sẽ build image Docker tên `miniclaw`. Trong quá trình build, Docker tự động `git clone` mã nguồn từ GitHub — **không cần** có source trên máy local.

```powershell
docker build -t miniclaw .
```

> **Lưu ý:** Lần đầu build sẽ mất vài phút do tải dependencies (Python packages + Node.js). Các lần sau sẽ nhanh hơn nhờ Docker layer cache.

### Tùy chọn: build từ branch / tag / commit khác

```powershell
docker build -t miniclaw --build-arg MINICLAW_REF=v0.1.4 --no-cache .
```

---

## 3. Chạy các dịch vụ

```powershell
docker compose up -d
```

Lệnh này khởi động 2 container:

| Container | Cổng | Mô tả |
|-----------|------|-------|
| `miniclaw-gateway` | `18790` | Gateway xử lý kết nối tới các bot / bridge |
| `miniclaw-launcher` | `18801` | Giao diện web quản lý Miniclaw |

Sau khi chạy, truy cập Launcher tại: **http://localhost:18801**

---

## 4. Chạy lệnh trong container (exec)

### Xem trạng thái

```powershell
docker exec miniclaw-gateway miniclaw status
```

### Chạy Miniclaw Launcher thủ công

```powershell
docker exec -it miniclaw-launcher miniclaw-launcher
```

### Mở shell tương tác

```powershell
docker exec -it miniclaw-gateway bash
```

### Chạy CLI tạm thời (không restart)

```powershell
docker compose run --rm miniclaw-cli status
```

---

## 5. Xem log

```powershell
# Xem log Gateway
docker compose logs -f miniclaw-gateway

# Xem log Launcher
docker compose logs -f miniclaw-launcher

# Xem log tất cả dịch vụ
docker compose logs -f
```

---

## 6. Dừng và xóa container

```powershell
# Dừng các container (giữ lại dữ liệu)
docker compose down

# Dừng và xóa luôn volume dữ liệu
docker compose down -v
```

---

## 7. Cập nhật lên phiên bản mới

Build lại image từ mã nguồn mới nhất rồi restart:

```powershell
docker build -t miniclaw --no-cache .
docker compose up -d
```

---

## Lưu ý về dữ liệu

Cấu hình và dữ liệu của Miniclaw được lưu trong **named volume**:

```
miniclaw-data  →  /root/.miniclaw  (bên trong container)
```

Volume này được giữ lại giữa các lần restart và update, đảm bảo không mất cấu hình khi rebuild image.

---

## Gặp vấn đề?

| Vấn đề | Cách xử lý |
|--------|------------|
| Cổng `18790` / `18801` bị chiếm | Đổi port trong `docker-compose.yml` phần `ports` |
| Build thất bại do lỗi mạng | Thử lại; hoặc kiểm tra `MINICLAW_REPO` trong `.env` |
| Container không start | Chạy `docker compose logs` để xem lỗi chi tiết |
| Muốn reset toàn bộ | `docker compose down -v` rồi build lại từ đầu |
