# 音频驱动的图片幻灯片生成器

一个基于PyQt6的音频驱动图片幻灯片生成工具，可以将图片和音频合成为视频。

## 🚀 快速启动

### 方法1：桌面快捷方式（推荐）
1. 在桌面上找到 `音频视频生成器.bat` 文件
2. 双击即可启动程序

### 方法2：直接运行
1. 进入项目文件夹 `D:\app\audioToVideo`
2. 双击 `启动音频视频生成器.bat` 文件

### 方法3：PowerShell启动
1. 右键点击 `启动音频视频生成器.ps1`
2. 选择"使用PowerShell运行"

## 📋 系统要求

- Windows 10/11
- Python 3.11+
- 以下Python库：
  - PyQt5
  - moviepy
  - PIL (Pillow)
  - numpy

## 🔧 安装依赖

如果遇到依赖库缺失的问题，可以运行：

```bash
pip install PyQt5 moviepy pillow numpy
```

## 🎯 功能特点

- ✅ 支持单个和批量音频处理
- ✅ 多种动画效果选择
- ✅ 可插入视频片段（最多999个）
- ✅ 智能时长分配算法
- ✅ 视频长度以音频长度为准
- ✅ 自动保存配置
- ✅ 实时处理日志
- ✅ 支持多种图片和音频格式

## 📁 文件说明

- `main.py` - 主程序文件
- `animation_effects.py` - 动画效果模块
- `config_manager.py` - 配置管理模块
- `启动音频视频生成器.bat` - Windows批处理启动脚本
- `启动音频视频生成器.ps1` - PowerShell启动脚本
- `launcher.py` - Python启动器

## 🐛 常见问题

### Q: 出现"DLL load failed"错误
A: 重新安装PyQt5：
```bash
pip uninstall PyQt5 -y
pip install PyQt5
```

### Q: 程序无法启动
A: 检查Python环境是否正确安装，并确保所有依赖库都已安装。

### Q: 生成的视频质量不佳
A: 调整导出设置中的FPS、CRF和预设参数。

## 📞 技术支持

如有问题，请检查程序日志输出或联系开发者。