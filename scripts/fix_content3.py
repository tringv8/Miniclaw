# -*- coding: utf-8 -*-
content = open('Content.md', encoding='utf-8').read()

# Thay thế đoạn bị rác (sau phần b) và trước Bước 3)
OLD = (
    "Không yêu cầu bất kỳ phần mềm nào khác. Cụ thể, người dùng **không cần** cài Python, Node.js, "
    "hay bất kỳ công cụ lập trình nào trên máy chủ — tất cả đã được đóng gói bên trong container.\r\n"
    "```\r\n"
    "\r\n"
    "Trên macOS/Linux (Terminal):\r\n"
    "```bash\r\n"
    "cp .env.example .env\r\n"
    "```\r\n"
    "\r\n"
    "**Bước 3"
)

NEW = (
    "Không yêu cầu bất kỳ phần mềm nào khác. Cụ thể, người dùng **không cần** cài Python, Node.js, "
    "hay bất kỳ công cụ lập trình nào trên máy chủ — tất cả đã được đóng gói bên trong container.\n"
    "\n"
    "[GỢI Ý CHỤP MÀN HÌNH: Mở Docker Desktop, chụp lại màn hình chính hiển thị trạng thái "
    '"Engine running" (biểu tượng Docker màu xanh ở góc dưới bên trái) để minh hoạ điều kiện tiên quyết đã được đáp ứng.]\n'
    "\n"
    "#### c) Chuẩn bị ba file cấu hình\n"
    "\n"
    "**Bước 1 — Tải ba file cấu hình Docker về máy:**\n"
    "\n"
    "Truy cập **DownGit** ([downgit.github.io](https://downgit.github.io)) — một công cụ trực tuyến "
    "cho phép tải về một thư mục con bất kỳ từ GitHub mà không cần clone toàn bộ repository.\n"
    "\n"
    "Dán đường dẫn sau vào ô nhập của DownGit rồi nhấn **Download**:\n"
    "\n"
    "```\n"
    "https://github.com/tringv8/miniclaw/tree/main/docker\n"
    "```\n"
    "\n"
    "DownGit sẽ đóng gói thư mục `docker/` thành một file `.zip`. Giải nén file đó ra — bên trong sẽ "
    "có đúng ba file cần thiết: `Dockerfile`, `docker-compose.yml`, `.env.example`. "
    "Đây là thư mục làm việc cho tất cả các bước tiếp theo.\n"
    "\n"
    "[GỢI Ý CHỤP MÀN HÌNH: Mở trình duyệt vào downgit.github.io, dán link GitHub vào ô nhập, "
    "chụp lại giao diện trang web ngay trước khi nhấn Download — sau đó chụp tiếp cửa sổ Explorer "
    "hiển thị 3 file vừa giải nén để minh hoạ kết quả.]\n"
    "\n"
    "**Bước 2 — Tạo file `.env` từ mẫu:**\n"
    "\n"
    "Trên Windows (PowerShell):\n"
    "```powershell\n"
    "Copy-Item .env.example .env\n"
    "```\n"
    "\n"
    "Trên macOS/Linux (Terminal):\n"
    "```bash\n"
    "cp .env.example .env\n"
    "```\n"
    "\n"
    "**Bước 3"
)

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    print("OK: Da sua xong")
else:
    # Thu voi \n thay vi \r\n
    OLD2 = OLD.replace('\r\n', '\n')
    if OLD2 in content:
        content = content.replace(OLD2, NEW, 1)
        print("OK (LF): Da sua xong")
    else:
        print("FAILED: Khong tim thay doan can sua")
        # In ra 10 dong xung quanh de debug
        idx = content.find("Kh\u00f4ng y\u00eau c\u1ea7u b\u1ea5t k\u1ef3")
        print(f"idx={idx}")
        print(repr(content[idx:idx+300]))

open('Content.md', 'w', encoding='utf-8').write(content)
print("Luu xong, dong:", content.count('\n'))
