@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"

if exist "%ROOT%web\frontend_python_codex\.venv\Scripts\python.exe" (
  "%ROOT%web\frontend_python_codex\.venv\Scripts\python.exe" -m miniclaw.cli.launcher %*
  exit /b %ERRORLEVEL%
)

python -m miniclaw.cli.launcher %*
exit /b %ERRORLEVEL%
