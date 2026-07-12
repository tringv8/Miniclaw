@echo off
setlocal

:: ==============================================================
:: gog-setup.cmd -- Ket noi Google Workspace cho Miniclaw
:: Bam dup de chay -- Khong can cau hinh gi them
:: ==============================================================

set "ROOT=%~dp0"

echo.
echo ==================================================
echo   Miniclaw -- Thiet lap xac thuc Google (Local)
echo ==================================================
echo.

:: Lay email tu tham so dong lenh (neu co)
set "EMAIL=%~1"

:: Chay PowerShell script voi ExecutionPolicy Bypass
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%gog-setup.ps1" %EMAIL%

:: Giu cua so mo de nguoi dung xem ket qua neu bam dup
if "%~1"=="" pause
