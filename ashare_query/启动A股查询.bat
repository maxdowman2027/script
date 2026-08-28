@echo off
chcp 65001 >nul
cd /d "%~dp0"
title A股 PE / 股息率查询
echo 正在启动 A股查询工具 ...
python ashare_pe_yield.py
if errorlevel 1 (
    echo.
    echo 启动失败。请确认已安装 Python，并执行:
    echo     pip install -r requirements.txt
    pause
)
