# ==============================================================
# gog-setup.ps1 -- Xac thuc Google cho Miniclaw (chay cuc bo Windows)
# Cach dung: .\gog-setup.ps1 your@gmail.com
#
# Tuong duong voi docker/gog-setup.sh nhung danh cho Windows local.
# Script se tu tai gogcli neu chua cai dat.
# ==============================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Email
)

# --- Mau sac ---
function Write-Green($msg)  { Write-Host $msg -ForegroundColor Green }
function Write-Yellow($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Red($msg)    { Write-Host $msg -ForegroundColor Red }
function Write-Cyan($msg)   { Write-Host $msg -ForegroundColor Cyan }

# --- Banner ---
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Miniclaw -- Thiet lap xac thuc Google (Local)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# --- Kiem tra email ---
if (-not $Email) {
    Write-Yellow "Cach dung: .\gog-setup.ps1 your@gmail.com"
    Write-Host ""
    $Email = Read-Host "Nhap dia chi email Google cua ban"
    if (-not $Email) {
        Write-Red "[LOI] Email khong duoc de trong."
        exit 1
    }
}

# --- Duong dan cuc bo (tuong duong Docker) ---
$MINICLAW_DIR = Join-Path $env:USERPROFILE ".miniclaw"
$SECRETS_DIR  = Join-Path $MINICLAW_DIR "workspace\secrets"
$CREDS_FILE   = Join-Path $SECRETS_DIR "gog-credentials.json"
$SERVICES     = "gmail,calendar,drive,docs,sheets"
$GOG_VERSION  = "0.12.0"
$GOG_EXE      = Join-Path $env:LOCALAPPDATA "miniclaw\bin\gog.exe"

# --- Buoc 0: Tu dong cai gogcli neu chua co ---
Write-Cyan "[0/3] Kiem tra gogcli..."

# Thu tim trong PATH truoc
$gogCmd = $null
try {
    $found = Get-Command gog -ErrorAction Stop
    $gogCmd = $found.Source
} catch {
    # Khong co trong PATH, kiem tra vi tri cai dat cua chung ta
    if (Test-Path $GOG_EXE) {
        $gogCmd = $GOG_EXE
    }
}

if (-not $gogCmd) {
    Write-Yellow "  gogcli chua duoc cai dat. Dang tai phien ban v$GOG_VERSION..."

    $downloadUrl = "https://github.com/steipete/gogcli/releases/download/v$GOG_VERSION/gogcli_${GOG_VERSION}_windows_amd64.zip"
    $zipPath    = Join-Path $env:TEMP "gogcli.zip"
    $extractDir = Join-Path $env:TEMP "gogcli_extract"

    try {
        Write-Host "  Dang tai tu: $downloadUrl"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
        Write-Green "  OK: Tai xong"

        # Giai nen
        if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
        Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

        # Tim file .exe
        $exeFound = Get-ChildItem -Path $extractDir -Filter "*.exe" -Recurse | Select-Object -First 1
        if (-not $exeFound) {
            Write-Red "[LOI] Khong tim thay file .exe sau khi giai nen."
            exit 1
        }

        # Sao chep vao thu muc cai dat
        $binDir = Split-Path $GOG_EXE -Parent
        if (-not (Test-Path $binDir)) {
            New-Item -ItemType Directory -Path $binDir -Force | Out-Null
        }
        Copy-Item $exeFound.FullName -Destination $GOG_EXE -Force
        Write-Green "  OK: Da cai gogcli tai: $GOG_EXE"

        # Don dep
        Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
        Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

        # Them vao PATH phien hien tai
        $env:PATH = "$binDir;$env:PATH"
        $gogCmd = $GOG_EXE

        Write-Host ""
        Write-Yellow "  Goi y: De dung 'gog' tu bat ky dau, them vao PATH nguoi dung:"
        Write-Host "  Thu muc: $binDir"
        Write-Host "  Lenh them PATH (chay PowerShell voi quyen Admin):"
        Write-Cyan "  [Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH','User') + ';$binDir', 'User')"
        Write-Host ""

    } catch {
        Write-Red "[LOI] Khong the tai gogcli: $_"
        Write-Host ""
        Write-Yellow "Tai thu cong tai:"
        Write-Host "  https://github.com/steipete/gogcli/releases/tag/v$GOG_VERSION"
        Write-Yellow "Dat file gog.exe vao thu muc nam trong PATH va chay lai script nay."
        exit 1
    }
} else {
    Write-Green "  OK: Da co gogcli: $gogCmd"
}

Write-Host ""

# --- Buoc 1: Kiem tra file credentials ---
Write-Cyan "[1/3] Kiem tra file Google credentials..."

if (-not (Test-Path $CREDS_FILE)) {
    Write-Host ""
    Write-Red "  [LOI] Khong tim thay file credentials tai:"
    Write-Host "    $CREDS_FILE"
    Write-Host ""
    Write-Yellow "  Huong dan tao credentials:"
    Write-Host "   1. Vao Google Cloud Console: https://console.cloud.google.com/"
    Write-Host "   2. Tao project -> APIs and Services -> Credentials"
    Write-Host "   3. Tao 'OAuth 2.0 Client ID' loai 'Desktop App'"
    Write-Host "   4. Tai file JSON ve"
    Write-Host "   5. Dat file vao thu muc sau va doi ten thanh gog-credentials.json:"
    Write-Cyan "      $SECRETS_DIR"
    Write-Host ""
    Write-Host "  Tao thu muc secrets (neu chua co):"
    Write-Cyan "  New-Item -ItemType Directory -Force -Path '$SECRETS_DIR'"
    Write-Host ""
    exit 1
}

Write-Green "  OK: Tim thay file credentials: $CREDS_FILE"
Write-Host ""

# --- Buoc 2: Dang ky credentials ---
Write-Cyan "[2/3] Dang ky file credentials voi gogcli..."

try {
    & $gogCmd auth credentials $CREDS_FILE
    if ($LASTEXITCODE -ne 0) {
        throw "gog auth credentials that bai (exit code $LASTEXITCODE)"
    }
    Write-Green "  OK: Da dang ky credentials"
} catch {
    Write-Red "  [LOI] Dang ky credentials that bai: $_"
    exit 1
}

Write-Host ""

# --- Buoc 3: Xac thuc OAuth ---
Write-Cyan "[3/3] Bat dau xac thuc OAuth cho: $Email"
Write-Host ""
Write-Yellow "  Huong dan:"
Write-Host "   1. URL xac thuc se xuat hien ben duoi"
Write-Host "   2. Mo URL do trong trinh duyet"
Write-Host "   3. Dang nhap Google va cap quyen cho cac dich vu:"
Write-Cyan "      $SERVICES"
Write-Host "   4. Trinh duyet se chuyen den trang loi/trong -- KHONG SAO"
Write-Host "   5. Sao chep TOAN BO URL tren thanh dia chi va dan vao day"
Write-Host ""

try {
    & $gogCmd auth add $Email --services $SERVICES --manual
    if ($LASTEXITCODE -ne 0) {
        throw "gog auth add that bai (exit code $LASTEXITCODE)"
    }
} catch {
    Write-Host ""
    Write-Red "[LOI] Xac thuc that bai: $_"
    exit 1
}

# --- Thanh cong ---
Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "  OK: Xac thuc thanh cong!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Kiem tra ket noi Google Calendar:"
Write-Cyan "  gog calendar calendars"
Write-Host ""
Write-Host "Khoi dong lai Miniclaw de ap dung:"
Write-Cyan "  .\miniclaw-launcher.cmd"
Write-Host ""
