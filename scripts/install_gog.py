"""
Script tự động tải và cài gogcli binary phù hợp với hệ điều hành hiện tại.
- Windows: tải file .zip, giải nén vào workspace/bin/gog.exe
- Linux/macOS: tải file .tar.gz, giải nén vào workspace/bin/gog

Cách dùng:
    python scripts/install_gog.py
"""

import os
import platform
import stat
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

GOG_VERSION = "0.12.0"

DOWNLOAD_URLS = {
    "windows": f"https://github.com/steipete/gogcli/releases/download/v{GOG_VERSION}/gogcli_{GOG_VERSION}_windows_amd64.zip",
    "linux": f"https://github.com/steipete/gogcli/releases/download/v{GOG_VERSION}/gogcli_{GOG_VERSION}_linux_amd64.tar.gz",
    "darwin": f"https://github.com/steipete/gogcli/releases/download/v{GOG_VERSION}/gogcli_{GOG_VERSION}_darwin_amd64.tar.gz",
}

# Thư mục workspace/bin nằm cùng cấp với scripts/
SCRIPT_DIR = Path(__file__).parent
BIN_DIR = SCRIPT_DIR.parent / "workspace" / "bin"


def detect_os() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "darwin"
    else:
        return "linux"


def download_file(url: str, dest: Path) -> None:
    print(f"  Đang tải: {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"  Đã lưu vào: {dest}")


def install_gog(os_name: str) -> Path:
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    url = DOWNLOAD_URLS.get(os_name)
    if not url:
        print(f"[LỖI] Hệ điều hành không được hỗ trợ: {os_name}")
        sys.exit(1)

    # Tên file tải về
    archive_name = url.split("/")[-1]
    archive_path = BIN_DIR / archive_name

    print(f"\n[1/3] Phát hiện hệ điều hành: {os_name}")
    print(f"[2/3] Tải gogcli v{GOG_VERSION}...")
    download_file(url, archive_path)

    print("[3/3] Giải nén...")
    bin_name = "gog.exe" if os_name == "windows" else "gog"
    bin_path = BIN_DIR / bin_name

    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            # Tìm file gog.exe trong archive
            for member in zf.namelist():
                if member.endswith("gog.exe") or member == "gog.exe":
                    with zf.open(member) as src, open(bin_path, "wb") as dst:
                        dst.write(src.read())
                    break
    else:
        with tarfile.open(archive_path) as tf:
            for member in tf.getmembers():
                if member.name.endswith("/gog") or member.name == "gog":
                    member.name = "gog"
                    tf.extract(member, BIN_DIR)
                    break

    # Gán quyền thực thi trên Linux/macOS
    if os_name != "windows":
        bin_path.chmod(bin_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Xóa file nén
    archive_path.unlink()

    return bin_path


def main():
    print("=" * 50)
    print("  Cài đặt gogcli (gog)")
    print("=" * 50)

    os_name = detect_os()
    bin_path = install_gog(os_name)

    print(f"\n✅ Đã cài gog tại: {bin_path}")
    print("\n⚠️  Để dùng lệnh 'gog' trực tiếp trong cmd, thêm thư mục sau vào PATH:")
    print(f"   {BIN_DIR}")
    print("\nHoặc gọi trực tiếp:")
    print(f"   {bin_path} --help")


if __name__ == "__main__":
    main()
