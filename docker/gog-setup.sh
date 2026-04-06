#!/bin/bash
# =============================================================
# gog-setup.sh — Xác thực Google cho Miniclaw (chạy trong container)
# Cách dùng: ./gog-setup.sh your@gmail.com
# =============================================================

set -e

CREDS="/root/.miniclaw/workspace/secrets/gog-credentials.json"
SERVICES="gmail,calendar,drive,docs,sheets"

# Màu sắc
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "=================================================="
echo "  🐈 Miniclaw — Thiết lập xác thực Google"
echo "=================================================="
echo ""

# Kiểm tra email đầu vào
if [ -z "$1" ]; then
    echo -e "${YELLOW}Cách dùng:${NC} $0 your@gmail.com"
    exit 1
fi

EMAIL="$1"

# Kiểm tra file credentials
if [ ! -f "$CREDS" ]; then
    echo -e "${RED}[LỖI]${NC} Không tìm thấy file credentials tại:"
    echo "  $CREDS"
    echo ""
    echo "Hãy đặt file .json tải từ Google Console vào thư mục secrets/"
    echo "và đổi tên thành: gog-credentials.json"
    exit 1
fi

echo -e "${GREEN}✓${NC} Tìm thấy file credentials"
echo ""

# Khai báo credentials
echo "[1/2] Đăng ký file credentials..."
gog auth credentials "$CREDS"
echo -e "${GREEN}✓${NC} Đã đăng ký credentials"
echo ""

# Xác thực OAuth (chế độ --manual: chỉ cần paste URL từ trình duyệt)
echo "[2/2] Bắt đầu xác thực OAuth cho: $EMAIL"
echo ""
echo -e "${YELLOW}Hướng dẫn:${NC}"
echo "  1. Mở URL bên dưới trong trình duyệt trên máy tính của bạn"
echo "  2. Đăng nhập Google và cấp quyền"
echo "  3. Sau khi xong, trình duyệt sẽ hiện trang lỗi — KHÔNG sao"
echo "  4. Sao chép TOÀN BỘ URL trên thanh địa chỉ trình duyệt"
echo "  5. Dán URL đó vào đây khi được hỏi"
echo ""

gog auth add "$EMAIL" --services "$SERVICES" --manual

echo ""
echo -e "${GREEN}=================================================="
echo "  ✅ Xác thực thành công!"
echo "==================================================${NC}"
echo ""
echo "Kiểm tra kết quả:"
echo "  gog calendar calendars"
echo ""
