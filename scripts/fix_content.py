# -*- coding: utf-8 -*-
# Script sửa Content.md:
# 1. Xóa block bị nhầm (dòng 571-600) trong mục 2.3.3
# 2. Đặt đúng nội dung DownGit vào mục 3.1 (sau "Không yêu cầu bất kỳ phần mềm nào khác...")

with open("Content.md", encoding="utf-8") as f:
    content = f.read()

# ---- Bước 1: Xóa block bị nhầm vào giữa mục 2.3.3 ----
bad_block = """[GỢI Ý CHỤP MÀN HÌNH: Mở Docker Desktop, chụp lại màn hình chính hiển thị trạng thái "Engine running" (biểu tượng Docker màu xanh ở góc dưới bên trái) để minh hoạ điều kiện tiên quyết đã được đáp ứng.]

#### c) Chuẩn bị ba file cấu hình

**Bước 1 — Tải ba file cấu hình Docker về máy:**

Truy cập **DownGit** ([downgit.github.io](https://downgit.github.io)) — một công cụ trực tuyến cho phép tải về một thư mục con bất kỳ từ GitHub mà không cần clone toàn bộ repository.

Dán đường dẫn sau vào ô nhập của DownGit rồi nhấn **Download**:

```
https://github.com/tringv8/miniclaw/tree/main/docker
```

DownGit sẽ đóng gói thư mục `docker/` thành một file `.zip`. Giải nén file đó ra — bên trong sẽ có đúng ba file cần thiết: `Dockerfile`, `docker-compose.yml`, `.env.example`. Đây là thư mục làm việc cho tất cả các bước tiếp theo.

[GỢI Ý CHỤP MÀN HÌNH: Mở trình duyệt vào downgit.github.io, dán link GitHub vào ô nhập, chụp lại giao diện trang web ngay trước khi nhấn Download — sau đó chụp tiếp cửa sổ Explorer hiển thị 3 file vừa giải nén để minh hoạ kết quả.]

**Bước 2 — Tạo file `.env` từ mẫu:**

Trên Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

Trên macOS/Linux (Terminal):
```bash
cp .env.example .env
```

Module giao tiếp"""

good_replace = "Module giao tiếp"

assert bad_block in content, "KHÔNG TÌM THẤY BLOCK XẤU!"
content = content.replace(bad_block, good_replace, 1)
print("Bước 1: Đã xóa block nhầm trong 2.3.3")

# ---- Bước 2: Tìm vị trí đúng trong mục 3.1 và chèn nội dung DownGit ----
OLD_31 = """**Bước 1 — Tải ba file về máy:**

Tạo một thư mục trống bất kỳ (ví dụ: `miniclaw-deploy/`) rồi đặt vào đó ba file: `Dockerfile`, `docker-compose.yml`, và `.env.example` (sao chép từ thư mục `docker/` trong mã nguồn)."""

NEW_31 = """**Bước 1 — Tải ba file cấu hình Docker về máy:**

Truy cập **DownGit** ([downgit.github.io](https://downgit.github.io)) — một công cụ trực tuyến cho phép tải về một thư mục con bất kỳ từ GitHub mà không cần clone toàn bộ repository.

Dán đường dẫn sau vào ô nhập của DownGit rồi nhấn **Download**:

```
https://github.com/tringv8/miniclaw/tree/main/docker
```

DownGit sẽ đóng gói thư mục `docker/` thành một file `.zip`. Giải nén file đó ra — bên trong sẽ có đúng ba file cần thiết: `Dockerfile`, `docker-compose.yml`, `.env.example`. Đây là thư mục làm việc cho tất cả các bước tiếp theo.

[GỢI Ý CHỤP MÀN HÌNH: Mở trình duyệt vào downgit.github.io, dán link GitHub vào ô nhập, chụp lại giao diện trang web ngay trước khi nhấn Download — sau đó chụp tiếp cửa sổ Explorer hiển thị 3 file vừa giải nén để minh hoạ kết quả.]"""

assert OLD_31 in content, "KHÔNG TÌM THẤY VỊ TRÍ ĐÚNG TRONG 3.1!"
content = content.replace(OLD_31, NEW_31, 1)
print("Bước 2: Đã chèn DownGit vào đúng vị trí mục 3.1")

with open("Content.md", "w", encoding="utf-8") as f:
    f.write(content)

print("Hoàn thành. Tổng dòng:", content.count("\n"))
