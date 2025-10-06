"""
动画效果模块
使用MoviePy创建各种图片动画效果
"""

import os
from moviepy.editor import ImageClip, CompositeVideoClip
import math
from moviepy.video.fx import resize
import numpy as np


def create_animated_clip(image_path, duration, effect_name, intensity=1.0, resolution=None):
    """
    根据效果名称创建动态的ImageClip
    
    Args:
        image_path (str): 图片文件路径
        duration (float): 持续时间（秒）
        effect_name (str): 效果名称
        intensity (float): 动画强度 (0.1-3.0)，默认1.0
        
    Returns:
        ImageClip: 动态图片片段
    """
    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    # 限制强度范围
    intensity = max(0.1, min(3.0, intensity))
    # 解析分辨率
    target_size = None
    if resolution and isinstance(resolution, (tuple, list)) and len(resolution) == 2:
        target_size = (int(resolution[0]), int(resolution[1]))
    
    # 根据效果名称选择对应的动画函数
    effect_functions = {
        'Slow Zoom In': _create_slow_zoom_in,
        'Slow Zoom Out': _create_slow_zoom_out,
        'Pan Left to Right': _create_pan_left_to_right,
        'Pan Right to Left': _create_pan_right_to_left,
        'Pan Diagonal Up Right': _create_pan_diagonal_up_right,
        'Pan Diagonal Up Left': _create_pan_diagonal_up_left,
        'Pan Diagonal Down Right': _create_pan_diagonal_down_right,
        'Pan Diagonal Down Left': _create_pan_diagonal_down_left,
        'Fade In': _create_fade_in,
        'Fade Out': _create_fade_out,
        'No Animation': _create_no_animation
    }
    
    if effect_name not in effect_functions:
        raise ValueError(f"不支持的效果: {effect_name}. 支持的效果: {list(effect_functions.keys())}")
    
    # 调用对应的效果函数，传递强度参数及目标分辨率
    return effect_functions[effect_name](image_path, duration, intensity, target_size)


# 工具函数：根据目标分辨率进行等比例放大（cover），确保无黑边
def _prepare_cover_clip(image_path, duration, target_size, intensity: float = 1.0):
    base = ImageClip(image_path, duration=duration)
    if not target_size:
        return base, base.w, base.h
    tw, th = target_size
    scale = max(tw / base.w, th / base.h)
    # 增加较大的放大量，确保平移过程中也不出现黑边
    # 覆盖系数随强度略增：最低1.18，强度1时约1.4
    strength = max(0.1, min(1.0, float(intensity)))
    cover_margin = 1.18 + 0.22 * strength
    scale *= cover_margin
    resized = base.resize(scale)
    return resized, resized.w, resized.h


def _create_slow_zoom_in(image_path, duration, intensity=1.0, target_size=None):
    """
    慢速放大效果：在duration时间内，图片从原始大小均匀放大
    
    Args:
        image_path (str): 图片文件路径
        duration (float): 持续时间（秒）
        intensity (float): 动画强度，控制放大倍数
        
    Returns:
        ImageClip: 动态图片片段
    """
    # 根据强度计算最大缩放比例
    max_scale = 1.0 + (0.2 * intensity)  # 强度1.0时放大到1.2倍，强度3.0时放大到1.6倍
    
    # 创建基础图片片段并拉伸至目标分辨率
    base = ImageClip(image_path, duration=duration)
    if target_size:
        clip = base.resize(newsize=target_size)
    else:
        clip = base
    
    # 使用resize方法创建缩放动画
    def resize_func(t):
        scale = 1.0 + ((max_scale - 1.0) * t / duration)
        return scale
    
    # 应用缩放效果（以目标分辨率为画布进行合成，避免尺寸差异）
    zoomed = clip.resize(resize_func)
    if target_size:
        return CompositeVideoClip([zoomed.set_position('center')], size=target_size)
    return zoomed


def _create_slow_zoom_out(image_path, duration, intensity=1.0, target_size=None):
    """
    慢速缩小效果：在duration时间内，图片从放大状态缩小到原始大小
    
    Args:
        image_path (str): 图片文件路径
        duration (float): 持续时间（秒）
        intensity (float): 动画强度，控制初始放大倍数
        
    Returns:
        ImageClip: 动态图片片段
    """
    # 根据强度计算初始缩放比例
    initial_scale = 1.0 + (0.2 * intensity)
    
    # 创建基础图片片段并拉伸至目标分辨率
    base = ImageClip(image_path, duration=duration)
    if target_size:
        clip = base.resize(newsize=target_size)
    else:
        clip = base
    
    # 使用resize方法创建缩放动画
    def resize_func(t):
        scale = initial_scale - ((initial_scale - 1.0) * t / duration)
        return scale
    
    # 应用缩放效果
    zoomed = clip.resize(resize_func)
    if target_size:
        return CompositeVideoClip([zoomed.set_position('center')], size=target_size)
    return zoomed


def _create_pan_left_to_right(image_path, duration, intensity=1.0, target_size=None):
    """
    从左到右平移效果
    
    Args:
        image_path (str): 图片文件路径
        duration (float): 持续时间（秒）
        intensity (float): 动画强度，控制平移幅度
        
    Returns:
        ImageClip: 动态图片片段
    """
    # 创建cover裁切后的片段，保证无黑边
    clip, rw, rh = _prepare_cover_clip(image_path, duration, target_size, intensity)
    
    # 可移动的最大像素范围（确保始终覆盖目标画布）
    if target_size:
        tw, th = target_size
        max_offset_x = max(0, (rw - tw) / 2)
        base_x = -(rw - tw) / 2
        base_y = -(rh - th) / 2
    else:
        max_offset_x = clip.w * 0.15
        base_x = 0
        base_y = 0
    # 减小实际位移比例以“更慢”，并使用缓动曲线
    move_ratio = 0.4 * min(1.0, intensity)
    
    # 使用set_position方法创建平移动画
    def position_func(t):
        # 缓动：从-1到+1的平滑过渡
        ease = (math.cos(math.pi * (t / duration)) * -1.0)  # 0..1..0 映射为 -1..+1
        offset_x = base_x + ease * max_offset_x * move_ratio
        offset_y = base_y
        return (offset_x, offset_y)
    
    moved = clip.set_position(position_func)
    if target_size:
        return CompositeVideoClip([moved], size=target_size)
    return moved


def _create_pan_right_to_left(image_path, duration, intensity=1.0, target_size=None):
    """
    从右到左平移效果
    """
    clip, rw, rh = _prepare_cover_clip(image_path, duration, target_size, intensity)
    
    # 计算平移范围
    if target_size:
        tw, th = target_size
        max_offset_x = max(0, (rw - tw) / 2)
        base_x = -(rw - tw) / 2
        base_y = -(rh - th) / 2
    else:
        max_offset_x = clip.w * 0.15
        base_x = 0
        base_y = 0
    move_ratio = 0.4 * min(1.0, intensity)
    
    # 使用set_position方法创建平移动画
    def position_func(t):
        ease = (math.cos(math.pi * (t / duration)) * -1.0)  # -1..+1
        offset_x = base_x - ease * max_offset_x * move_ratio
        offset_y = base_y
        return (offset_x, offset_y)
    
    moved = clip.set_position(position_func)
    if target_size:
        return CompositeVideoClip([moved], size=target_size)
    return moved


def _create_pan_up_to_down(image_path, duration, intensity=1.0):
    """
    从上到下平移效果
    """
    clip = ImageClip(image_path, duration=duration)
    
    def make_frame(t):
        pan_range = 0.3 * intensity
        offset_x = 0
        offset_y = (t / duration - 0.5) * clip.h * pan_range
        panned_clip = clip.set_position((offset_x, offset_y))
        return panned_clip.get_frame(t)
    
    animated_clip = clip.fl(lambda gf, t: make_frame(t))
    return animated_clip


def _create_pan_down_to_up(image_path, duration, intensity=1.0):
    """
    从下到上平移效果
    """
    clip = ImageClip(image_path, duration=duration)
    
    def make_frame(t):
        pan_range = 0.3 * intensity
        offset_x = 0
        offset_y = (0.5 - t / duration) * clip.h * pan_range
        panned_clip = clip.set_position((offset_x, offset_y))
        return panned_clip.get_frame(t)
    
    animated_clip = clip.fl(lambda gf, t: make_frame(t))
    return animated_clip


def _create_pan_diagonal_up_right(image_path, duration, intensity=1.0, target_size=None):
    """
    斜向右上平移效果
    """
    clip, rw, rh = _prepare_cover_clip(image_path, duration, target_size, intensity)
    
    if target_size:
        tw, th = target_size
        max_offset_x = max(0, (rw - tw) / 2)
        max_offset_y = max(0, (rh - th) / 2)
        base_x = -(rw - tw) / 2
        base_y = -(rh - th) / 2
    else:
        max_offset_x = clip.w * 0.15
        max_offset_y = clip.h * 0.15
        base_x = 0
        base_y = 0
    move_ratio = 0.4 * min(1.0, intensity)
    
    # 使用set_position方法创建平移动画
    def position_func(t):
        ease = (math.cos(math.pi * (t / duration)) * -1.0)
        offset_x = base_x + ease * max_offset_x * move_ratio  # 向右
        offset_y = base_y - ease * max_offset_y * move_ratio  # 向上
        return (offset_x, offset_y)
    
    moved = clip.set_position(position_func)
    if target_size:
        return CompositeVideoClip([moved], size=target_size)
    return moved


def _create_pan_diagonal_up_left(image_path, duration, intensity=1.0, target_size=None):
    """
    斜向左上平移效果
    """
    clip, rw, rh = _prepare_cover_clip(image_path, duration, target_size, intensity)
    
    if target_size:
        tw, th = target_size
        max_offset_x = max(0, (rw - tw) / 2)
        max_offset_y = max(0, (rh - th) / 2)
        base_x = -(rw - tw) / 2
        base_y = -(rh - th) / 2
    else:
        max_offset_x = clip.w * 0.15
        max_offset_y = clip.h * 0.15
        base_x = 0
        base_y = 0
    move_ratio = 0.4 * min(1.0, intensity)
    
    # 使用set_position方法创建平移动画
    def position_func(t):
        ease = (math.cos(math.pi * (t / duration)) * -1.0)
        offset_x = base_x - ease * max_offset_x * move_ratio  # 向左
        offset_y = base_y - ease * max_offset_y * move_ratio  # 向上
        return (offset_x, offset_y)
    
    moved = clip.set_position(position_func)
    if target_size:
        return CompositeVideoClip([moved], size=target_size)
    return moved


def _create_pan_diagonal_down_right(image_path, duration, intensity=1.0, target_size=None):
    """
    斜向右下平移效果
    """
    clip, rw, rh = _prepare_cover_clip(image_path, duration, target_size, intensity)
    
    if target_size:
        tw, th = target_size
        max_offset_x = max(0, (rw - tw) / 2)
        max_offset_y = max(0, (rh - th) / 2)
        base_x = -(rw - tw) / 2
        base_y = -(rh - th) / 2
    else:
        max_offset_x = clip.w * 0.15
        max_offset_y = clip.h * 0.15
        base_x = 0
        base_y = 0
    move_ratio = 0.4 * min(1.0, intensity)
    
    # 使用set_position方法创建平移动画
    def position_func(t):
        ease = (math.cos(math.pi * (t / duration)) * -1.0)
        offset_x = base_x + ease * max_offset_x * move_ratio  # 向右
        offset_y = base_y + ease * max_offset_y * move_ratio  # 向下
        return (offset_x, offset_y)
    
    moved = clip.set_position(position_func)
    if target_size:
        return CompositeVideoClip([moved], size=target_size)
    return moved


def _create_pan_diagonal_down_left(image_path, duration, intensity=1.0, target_size=None):
    """
    斜向左下平移效果
    """
    clip, rw, rh = _prepare_cover_clip(image_path, duration, target_size)
    
    if target_size:
        tw, th = target_size
        max_offset_x = max(0, (rw - tw) / 2)
        max_offset_y = max(0, (rh - th) / 2)
        base_x = -(rw - tw) / 2
        base_y = -(rh - th) / 2
    else:
        max_offset_x = clip.w * 0.15
        max_offset_y = clip.h * 0.15
        base_x = 0
        base_y = 0
    move_ratio = 0.4 * min(1.0, intensity)
    
    # 使用set_position方法创建平移动画
    def position_func(t):
        ease = (math.cos(math.pi * (t / duration)) * -1.0)
        offset_x = base_x - ease * max_offset_x * move_ratio  # 向左
        offset_y = base_y + ease * max_offset_y * move_ratio   # 向下
        return (offset_x, offset_y)
    
    moved = clip.set_position(position_func)
    if target_size:
        return CompositeVideoClip([moved], size=target_size)
    return moved


def _create_no_animation(image_path, duration, intensity=1.0, target_size=None):
    """
    无动画效果
    """
    base = ImageClip(image_path, duration=duration)
    if target_size:
        base = base.resize(newsize=target_size)
        return CompositeVideoClip([base.set_position('center')], size=target_size)
    return base


def _create_fade_in(image_path, duration, intensity=1.0, target_size=None):
    """
    淡入：静止图，整个时长做淡入
    """
    base = ImageClip(image_path, duration=duration)
    if target_size:
        base = base.resize(newsize=target_size)
    clip = CompositeVideoClip([base.set_position('center')], size=target_size) if target_size else base
    fade_time = max(0.2, min(duration, duration * 0.6))  # 淡入时间占比0.2~0.6
    return clip.fadein(fade_time)


def _create_fade_out(image_path, duration, intensity=1.0, target_size=None):
    """
    淡出：静止图，整个时长做淡出
    """
    base = ImageClip(image_path, duration=duration)
    if target_size:
        base = base.resize(newsize=target_size)
    clip = CompositeVideoClip([base.set_position('center')], size=target_size) if target_size else base
    fade_time = max(0.2, min(duration, duration * 0.6))
    return clip.fadeout(fade_time)


# 获取所有支持的效果列表
def get_supported_effects():
    """
    获取所有支持的动画效果列表
    
    Returns:
        list: 效果名称列表
    """
    return [
        'Slow Zoom In',
        'Slow Zoom Out', 
        'Pan Left to Right',
        'Pan Right to Left',
        'Pan Diagonal Up Right',
        'Pan Diagonal Up Left',
        'Pan Diagonal Down Right',
        'Pan Diagonal Down Left',
        'Fade In',
        'Fade Out',
        'No Animation'
    ]


# 效果描述
def get_effect_description(effect_name):
    """
    获取效果的描述
    
    Args:
        effect_name (str): 效果名称
        
    Returns:
        str: 效果描述
    """
    descriptions = {
        'Slow Zoom In': '慢速放大：图片从原始大小均匀放大',
        'Slow Zoom Out': '慢速缩小：图片从放大状态缩小到原始大小',
        'Pan Left to Right': '从左到右平移',
        'Pan Right to Left': '从右到左平移',
        'Pan Diagonal Up Right': '斜向右上平移',
        'Pan Diagonal Up Left': '斜向左上平移',
        'Pan Diagonal Down Right': '斜向右下平移',
        'Pan Diagonal Down Left': '斜向左下平移',
        'Fade In': '静止图淡入',
        'Fade Out': '静止图淡出',
        'No Animation': '无动画效果'
    }
    
    return descriptions.get(effect_name, '未知效果')
