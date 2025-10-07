# 音频驱动的图片幻灯片生成器 - PowerShell启动脚本
Write-Host "正在启动音频视频生成器..." -ForegroundColor Green

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 切换到脚本所在目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptPath

# 检查Python是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python版本: $pythonVersion" -ForegroundColor Yellow
} catch {
    Write-Host "错误: 未找到Python环境，请先安装Python" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查并安装依赖库
$dependencies = @("PyQt5", "moviepy", "PIL", "numpy", "psutil")

foreach ($dep in $dependencies) {
    try {
        python -c "import $dep" 2>$null
        Write-Host "✓ $dep 已安装" -ForegroundColor Green
    } catch {
        Write-Host "正在安装 $dep..." -ForegroundColor Yellow
        pip install $dep
    }
}

# 启动主程序
Write-Host "启动程序..." -ForegroundColor Green
try {
    python main.py
} catch {
    Write-Host "程序运行出错: $_" -ForegroundColor Red
    Read-Host "按回车键退出"
}
