@echo off
chcp 65001 >nul
title 音频驱动的图片幻灯片生成器
echo 正在启动音频视频生成器...
echo.

cd /d "%~dp0"

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境，请先安装Python
    pause
    exit /b 1
)

REM 检查依赖库
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo 正在安装PyQt5...
    pip install PyQt5
)

python -c "import moviepy" >nul 2>&1
if errorlevel 1 (
    echo 正在安装moviepy...
    pip install moviepy
)

python -c "import psutil" >nul 2>&1
if errorlevel 1 (
    echo 正在安装psutil...
    pip install psutil
)

echo 启动程序...
python main.py

if errorlevel 1 (
    echo.
    echo 程序运行出错，请检查错误信息
    pause
)