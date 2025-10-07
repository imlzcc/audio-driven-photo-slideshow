#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频驱动的图片幻灯片生成器 - 启动器
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入并运行主程序
try:
    from main import main
    main()
except Exception as e:
    print(f"启动失败: {e}")
    input("按回车键退出...")
