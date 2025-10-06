"""
配置文件管理器
用于保存和加载应用程序的设置
"""
import json
import os
from typing import Dict, Any, Optional


class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = config_file
        self.default_config = {
            "image_folder": "",
            "audio_file": "",
            "output_folder": "",
            "image_duration_min": 4.0,
            "image_duration_max": 6.0,
            "animation_effect": "Slow Zoom In",
            "animation_intensity": 1.0,
            "resolution": "1920x1080",
            "custom_width": 1920,
            "custom_height": 1080,
            "fps": 24,
            "preset": "ultrafast",
            "crf": 23,
            "threads": 0
        }
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置，确保所有键都存在
                    merged_config = self.default_config.copy()
                    merged_config.update(config)
                    return merged_config
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def update_config(self, **kwargs) -> bool:
        """更新配置并保存"""
        config = self.load_config()
        config.update(kwargs)
        return self.save_config(config)
    
    def reset_config(self) -> bool:
        """重置为默认配置"""
        return self.save_config(self.default_config.copy())
    
    def get_config_path(self) -> str:
        """获取配置文件路径"""
        return os.path.abspath(self.config_file)
