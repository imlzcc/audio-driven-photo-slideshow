"""
简单的动画效果测试脚本
"""

import os
from animation_effects import create_animated_clip, get_supported_effects

def test_animation_effects():
    """测试动画效果"""
    print("=== 动画效果测试 ===")
    
    # 显示所有支持的效果
    print("\n支持的效果列表:")
    effects = get_supported_effects()
    for i, effect in enumerate(effects, 1):
        print(f"{i:2d}. {effect}")
    
    # 测试创建动画片段（不需要实际图片文件）
    print("\n=== 测试动画片段创建 ===")
    
    # 创建一个测试图片路径（实际使用时需要真实图片）
    test_image_path = "test_image.jpg"
    test_duration = 2.0
    test_intensity = 1.5
    
    print(f"测试图片路径: {test_image_path}")
    print(f"测试持续时间: {test_duration}秒")
    print(f"测试强度: {test_intensity}x")
    
    # 测试几个主要效果
    test_effects = ["Slow Zoom In", "Pan Left to Right", "Pan Diagonal Up Right"]
    
    for effect in test_effects:
        print(f"\n测试 '{effect}' 效果:")
        try:
            # 这里会因为没有实际图片文件而失败，但可以测试函数调用
            clip = create_animated_clip(test_image_path, test_duration, effect, test_intensity)
            print(f"✓ {effect} 效果创建成功")
            print(f"  片段时长: {clip.duration}秒")
            print(f"  片段尺寸: {clip.size}")
        except FileNotFoundError as e:
            print(f"✗ 文件不存在（预期错误）: {e}")
        except Exception as e:
            print(f"✗ 创建失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_animation_effects()
