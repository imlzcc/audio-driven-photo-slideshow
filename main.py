"""
Audio-Driven Photo Slideshow Generator
音频驱动的图片幻灯片生成器
"""

import sys
import os
import random
import time
import shutil
from typing import List, Optional
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                             QMessageBox, QDoubleSpinBox, QComboBox, QProgressBar,
                             QGroupBox, QFrame, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from animation_effects import create_animated_clip, get_supported_effects
from config_manager import ConfigManager


class VideoGenerationWorker(QThread):
    """视频生成工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(int)  # 进度更新 (0-100)
    status_updated = pyqtSignal(str)    # 状态更新
    log_updated = pyqtSignal(str)       # 日志更新
    generation_finished = pyqtSignal(bool, str)  # 生成完成 (成功/失败, 消息)
    
    def __init__(self, image_folder: str, audio_file: str, image_duration: float | tuple, 
                 animation_effect: str, output_path: str, animation_intensity: float = 1.0,
                 resolution: tuple | None = None, fps: int = 24, preset: str = "ultrafast",
                 crf: int = 23, threads: int | None = None, processed_folder: str | None = None,
                 video_clip_folder: str | None = None, enable_video_clips: bool = False, 
                 video_clip_count: int = 3, video_clip_scale_mode: str = "crop"):
        super().__init__()
        self.image_folder = image_folder
        self.audio_file = audio_file
        self.image_duration = image_duration  # 可为浮点数或(min,max)元组
        self.animation_effect = animation_effect
        self.output_path = output_path
        self.animation_intensity = animation_intensity
        self.resolution = resolution
        self.fps = fps
        self.preset = preset
        self.crf = crf
        self.threads = threads if threads and threads > 0 else max(1, (os.cpu_count() or 2) - 1)
        self.processed_folder = processed_folder
        self.video_clip_folder = video_clip_folder
        self.enable_video_clips = enable_video_clips
        self.video_clip_count = video_clip_count
        self.video_clip_scale_mode = video_clip_scale_mode
        
        # 支持的图片格式
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        
        # 支持的视频格式
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        
        # 跟踪实际处理的图片
        self.actually_processed_images = []
        
        # 线程控制
        self._is_running = True
    
    def run(self):
        """执行视频生成"""
        try:
            if not self._is_running:
                return
            # 步骤1: 输入验证
            self.log_updated.emit("=== 开始视频生成 ===")
            self.log_updated.emit(f"图片文件夹: {self.image_folder}")
            self.log_updated.emit(f"音频文件: {self.audio_file}")
            if isinstance(self.image_duration, tuple):
                self.log_updated.emit(f"图片时长范围: {self.image_duration[0]} - {self.image_duration[1]} 秒")
            else:
                self.log_updated.emit(f"图片时长: {self.image_duration}秒")
            self.log_updated.emit(f"动画效果: {self.animation_effect}")
            self.log_updated.emit(f"动画强度: {self.animation_intensity}x")
            self.log_updated.emit(f"输出路径: {self.output_path}")
            if self.resolution:
                self.log_updated.emit(f"目标分辨率: {self.resolution[0]}x{self.resolution[1]}")
            self.log_updated.emit(f"导出FPS: {self.fps}")
            self.log_updated.emit(f"编码预设: {self.preset} | CRF: {self.crf} | 线程: {self.threads}")
            
            self.status_updated.emit("验证输入文件...")
            self.log_updated.emit("步骤1: 验证输入文件...")
            self.progress_updated.emit(5)
            
            if not os.path.exists(self.image_folder):
                raise FileNotFoundError(f"图片文件夹不存在: {self.image_folder}")
            
            if not os.path.exists(self.audio_file):
                raise FileNotFoundError(f"音频文件不存在: {self.audio_file}")
            
            self.log_updated.emit("✓ 输入文件验证通过")
            
            # 步骤2: 加载音频文件
            self.status_updated.emit("加载音频文件...")
            self.log_updated.emit("步骤2: 加载音频文件...")
            self.progress_updated.emit(10)
            
            audio_clip = AudioFileClip(self.audio_file)
            audio_duration = audio_clip.duration
            self.log_updated.emit(f"✓ 音频加载完成，时长: {audio_duration:.2f}秒 ({audio_duration/60:.1f}分钟)")
            
            # 步骤3: 读取图片文件夹
            self.status_updated.emit("扫描图片文件...")
            self.log_updated.emit("步骤3: 扫描图片文件...")
            self.progress_updated.emit(15)
            
            image_files = []
            for file in os.listdir(self.image_folder):
                if any(file.lower().endswith(ext) for ext in self.image_extensions):
                    image_files.append(os.path.join(self.image_folder, file))
            
            if not image_files:
                raise ValueError("图片文件夹中没有找到支持的图片文件")
            
            # 按文件名排序
            image_files.sort()
            self.log_updated.emit(f"✓ 找到 {len(image_files)} 张图片")
            self.log_updated.emit(f"图片列表: {[os.path.basename(f) for f in image_files[:5]]}{'...' if len(image_files) > 5 else ''}")
            
            # 步骤4: 创建视频片段
            self.status_updated.emit("创建视频片段...")
            self.log_updated.emit("步骤4: 创建视频片段...")
            self.log_updated.emit(f"预计处理 {len(image_files)} 张图片，每张 {self.image_duration} 秒")
            self.progress_updated.emit(20)
            
            # 如果启用了视频片段插入，需要预留时间
            available_duration = audio_duration
            if self.enable_video_clips:
                # 估算视频片段需要的总时长（假设每个视频片段平均8秒）
                estimated_video_clips_duration = self.video_clip_count * 8.0
                available_duration = audio_duration - estimated_video_clips_duration
                self.log_updated.emit(f"为视频片段预留时间: {estimated_video_clips_duration:.1f}s, 图片可用时长: {available_duration:.1f}s")
            
            clips = []
            current_video_duration = 0.0
            total_images = len(image_files)
            processed_count = 0
            
            for i, image_path in enumerate(image_files):
                # 检查时长上限（使用可用时长而不是音频时长）
                if current_video_duration >= available_duration:
                    self.log_updated.emit(f"已达到图片可用时长上限，停止处理剩余图片")
                    break
                
                # 计算当前片段时长（范围内随机）
                remaining_time = available_duration - current_video_duration
                if isinstance(self.image_duration, tuple):
                    dmin, dmax = self.image_duration
                    rnd = random.random()
                    desired = dmin + (dmax - dmin) * rnd
                else:
                    desired = float(self.image_duration)
                clip_duration = min(desired, remaining_time)
                
                if clip_duration <= 0:
                    self.log_updated.emit(f"剩余时间不足，停止处理")
                    break
                
                # 更新状态
                self.status_updated.emit(f"正在处理第 {i+1} / {total_images} 张图片...")
                progress = 20 + (i / total_images) * 60  # 20% 到 80%
                self.progress_updated.emit(int(progress))
                
                try:
                    # 选择动画效果
                    effect = self.animation_effect
                    if effect == "随机效果":
                        # 随机选择一个效果（排除"随机效果"和"No Animation"）
                        available_effects = [e for e in get_supported_effects() 
                                           if e not in ["随机效果", "No Animation"]]
                        effect = random.choice(available_effects)
                    
                    self.log_updated.emit(f"处理图片 {i+1}: {os.path.basename(image_path)} (目标: {desired:.1f}s, 实际: {clip_duration:.1f}s, 效果: {effect}, 强度: {self.animation_intensity}x)")
                    
                    # 创建动画片段
                    clip = create_animated_clip(
                        image_path,
                        clip_duration,
                        effect,
                        self.animation_intensity,
                        self.resolution
                    )
                    clips.append(clip)
                    
                    # 记录实际处理的图片
                    self.actually_processed_images.append(image_path)
                    
                    current_video_duration += clip_duration
                    processed_count += 1
                    
                    self.log_updated.emit(f"✓ 图片 {i+1} 处理完成，当前视频时长: {current_video_duration:.1f}s")
                    
                except Exception as e:
                    self.log_updated.emit(f"✗ 处理图片 {i+1} 失败: {str(e)}")
                    continue
            
            if not clips:
                raise ValueError("没有成功创建任何视频片段")
            
            self.log_updated.emit(f"✓ 视频片段创建完成，共处理 {processed_count} 张图片")
            self.log_updated.emit(f"总视频时长: {current_video_duration:.1f}s")
            
            # 步骤5: 插入视频片段
            if self.enable_video_clips:
                self.status_updated.emit("插入视频片段...")
                self.log_updated.emit("步骤5: 插入视频片段...")
                self.progress_updated.emit(80)
                clips = self.insert_video_clips(clips, audio_duration, image_files)
                
                # 重新计算视频总时长
                new_video_duration = sum(clip.duration for clip in clips)
                self.log_updated.emit(f"插入视频片段后，总时长: {new_video_duration:.2f}s")
                
                # 如果视频时长超过音频时长，给出警告
                if new_video_duration > audio_duration:
                    self.log_updated.emit(f"警告: 插入视频片段后，视频时长({new_video_duration:.2f}s)超过音频时长({audio_duration:.2f}s)")
                    self.log_updated.emit("系统将循环播放音频以匹配视频长度")
                
                self.log_updated.emit("✓ 视频片段插入完成")
            
            # 步骤6: 最终视频合成
            self.status_updated.emit("合成视频...")
            self.log_updated.emit("步骤6: 合成视频...")
            self.progress_updated.emit(85)
            
            # 拼接视频片段
            self.log_updated.emit("正在拼接视频片段...")
            # 已统一分辨率时使用更快的 chain 方式
            if self.resolution:
                final_video = concatenate_videoclips(clips, method="chain")
            else:
                final_video = concatenate_videoclips(clips)
            final_video_duration = final_video.duration
            self.log_updated.emit(f"✓ 视频拼接完成，最终时长: {final_video_duration:.1f}s")
            
            # 精确同步音频
            self.status_updated.emit("同步音频...")
            self.log_updated.emit("步骤7: 同步音频...")
            self.progress_updated.emit(90)
            
            # 将音频剪辑到与视频相同的长度
            self.log_updated.emit("正在同步音频到视频长度...")
            self.log_updated.emit(f"音频时长: {audio_clip.duration:.2f}s, 视频时长: {final_video_duration:.2f}s")
            
            # 处理音频和视频时长不匹配的情况
            if final_video_duration > audio_clip.duration:
                # 视频比音频长，需要循环播放音频
                self.log_updated.emit(f"视频时长({final_video_duration:.2f}s)超过音频时长({audio_clip.duration:.2f}s)，将循环播放音频")
                
                # 计算需要循环的次数
                loops_needed = int(final_video_duration / audio_clip.duration) + 1
                self.log_updated.emit(f"需要循环播放 {loops_needed} 次音频")
                
                # 创建循环音频
                audio_clips = [audio_clip] * loops_needed
                from moviepy.editor import concatenate_audioclips
                looped_audio = concatenate_audioclips(audio_clips)
                
                # 剪辑到视频长度
                synced_audio = looped_audio.subclip(0, final_video_duration)
                final_video = final_video.set_audio(synced_audio)
                self.log_updated.emit(f"✓ 音频循环播放完成，最终时长: {final_video_duration:.2f}s")
                
            else:
                # 视频比音频短或相等，直接剪辑音频
                synced_audio = audio_clip.subclip(0, final_video_duration)
                final_video = final_video.set_audio(synced_audio)
                self.log_updated.emit(f"✓ 音频同步完成，同步时长: {final_video_duration:.2f}s")
            
            # 步骤8: 导出视频
            self.status_updated.emit("导出视频中...")
            self.log_updated.emit("步骤8: 导出视频...")
            self.log_updated.emit(f"正在导出到: {self.output_path}")
            self.log_updated.emit("注意: 导出过程可能需要较长时间，请耐心等待...")
            self.progress_updated.emit(95)
            
            # 根据视频长度调整导出参数
            ffmpeg_params = ["-movflags", "+faststart", "-pix_fmt", "yuv420p"]
            self.log_updated.emit("开始编码导出...")
            final_video.write_videofile(
                self.output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                preset=self.preset,
                threads=self.threads,
                ffmpeg_params=ffmpeg_params + ["-crf", str(self.crf)],
                verbose=False,
                logger=None,
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            self.log_updated.emit("✓ 视频导出完成")
            
            # 清理资源
            self.log_updated.emit("正在清理资源...")
            audio_clip.close()
            final_video.close()
            self.log_updated.emit("✓ 资源清理完成")
            
            # 移动已处理的图片到指定文件夹
            if self.processed_folder and os.path.exists(self.processed_folder):
                self.move_processed_images()
            
            self.status_updated.emit("完成！")
            self.progress_updated.emit(100)
            self.log_updated.emit("=== 视频生成完成 ===")
            self.generation_finished.emit(True, f"视频已成功保存到: {self.output_path}")
            
        except Exception as e:
            self.log_updated.emit(f"✗ 生成失败: {str(e)}")
            self.status_updated.emit("生成失败")
            self.generation_finished.emit(False, f"生成失败: {str(e)}")
    
    def move_processed_images(self):
        """移动已处理的图片到已处理文件夹"""
        try:
            self.log_updated.emit("步骤8: 移动已处理图片...")
            self.status_updated.emit("移动已处理图片...")
            
            # 只移动实际处理的图片
            processed_images = self.actually_processed_images
            
            if not processed_images:
                self.log_updated.emit("没有找到需要移动的已处理图片文件")
                return
            
            # 确保已处理文件夹存在
            if not os.path.exists(self.processed_folder):
                os.makedirs(self.processed_folder)
                self.log_updated.emit(f"创建已处理文件夹: {self.processed_folder}")
            
            moved_count = 0
            for image_path in processed_images:
                try:
                    filename = os.path.basename(image_path)
                    destination = os.path.join(self.processed_folder, filename)
                    
                    # 如果目标文件已存在，添加时间戳
                    if os.path.exists(destination):
                        name, ext = os.path.splitext(filename)
                        timestamp = int(time.time())
                        filename = f"{name}_{timestamp}{ext}"
                        destination = os.path.join(self.processed_folder, filename)
                    
                    # 移动文件
                    shutil.move(image_path, destination)
                    moved_count += 1
                    self.log_updated.emit(f"✓ 已移动: {filename}")
                    
                except Exception as e:
                    self.log_updated.emit(f"✗ 移动失败 {os.path.basename(image_path)}: {str(e)}")
                    continue
            
            self.log_updated.emit(f"✓ 已移动 {moved_count} 张已处理的图片到已处理文件夹")
            self.log_updated.emit(f"总共处理了 {len(self.actually_processed_images)} 张图片，移动了 {moved_count} 张")
            
        except Exception as e:
            self.log_updated.emit(f"✗ 移动已处理图片失败: {str(e)}")
    
    def get_video_clips(self):
        """获取视频片段文件列表"""
        if not self.enable_video_clips or not self.video_clip_folder or not os.path.exists(self.video_clip_folder):
            return []
        
        video_clips = []
        for file in os.listdir(self.video_clip_folder):
            if any(file.lower().endswith(ext) for ext in self.video_extensions):
                video_clips.append(os.path.join(self.video_clip_folder, file))
        
        # 随机选择指定数量的视频片段
        if len(video_clips) > self.video_clip_count:
            video_clips = random.sample(video_clips, self.video_clip_count)
        
        return sorted(video_clips)
    
    def insert_video_clips(self, clips, audio_duration, image_files):
        """在视频片段中插入视频片段 - 按照用户建议的简单逻辑"""
        if not self.enable_video_clips or not clips:
            return clips
        
        video_clips = self.get_video_clips()
        if not video_clips:
            self.log_updated.emit("没有找到可用的视频片段")
            return clips
        
        self.log_updated.emit(f"找到 {len(video_clips)} 个视频片段，准备插入")
        
        try:
            from moviepy.editor import VideoFileClip
            
            # 第一步：获取音频时长
            self.log_updated.emit(f"音频时长: {audio_duration:.1f}s")
            
            # 第二步：获取三个视频片段时长
            video_clip_data = []
            total_video_duration = 0
            
            for video_path in video_clips:
                try:
                    video_clip = VideoFileClip(video_path)
                    video_clip = video_clip.without_audio()
                    
                    # 保持视频片段完整，但限制最大时长
                    original_duration = video_clip.duration
                    max_allowed_duration = 15.0
                    min_allowed_duration = 1.0
                    
                    if original_duration > max_allowed_duration:
                        start_time = (original_duration - max_allowed_duration) / 2
                        video_clip = video_clip.subclip(start_time, start_time + max_allowed_duration)
                        actual_duration = max_allowed_duration
                        self.log_updated.emit(f"视频片段过长，从中间截取: {os.path.basename(video_path)} ({original_duration:.1f}s -> {actual_duration:.1f}s)")
                    elif original_duration < min_allowed_duration:
                        loops_needed = int(min_allowed_duration / original_duration) + 1
                        video_clips_loop = [video_clip] * loops_needed
                        video_clip = concatenate_videoclips(video_clips_loop).subclip(0, min_allowed_duration)
                        actual_duration = min_allowed_duration
                        self.log_updated.emit(f"视频片段过短，循环播放: {os.path.basename(video_path)} ({original_duration:.1f}s -> {actual_duration:.1f}s)")
                    else:
                        actual_duration = original_duration
                        self.log_updated.emit(f"视频片段时长合适: {os.path.basename(video_path)} ({actual_duration:.1f}s)")
                    
                    video_clip_data.append({
                        'clip': video_clip,
                        'duration': actual_duration,
                        'path': video_path
                    })
                    total_video_duration += actual_duration
                    
                except Exception as e:
                    self.log_updated.emit(f"✗ 加载视频片段失败 {os.path.basename(video_path)}: {str(e)}")
                    continue
            
            if not video_clip_data:
                self.log_updated.emit("没有成功加载任何视频片段")
                return clips
            
            self.log_updated.emit(f"视频片段总时长: {total_video_duration:.1f}s")
            
            # 第三步：计算差值
            remaining_time = audio_duration - total_video_duration
            self.log_updated.emit(f"剩余时间给图片: {remaining_time:.1f}s")
            
            if remaining_time <= 0:
                self.log_updated.emit(f"警告: 视频片段总时长({total_video_duration:.1f}s)超过音频时长({audio_duration:.1f}s)")
                remaining_time = audio_duration * 0.1
                self.log_updated.emit(f"调整后剩余时间: {remaining_time:.1f}s")
            
            # 第四步：根据剩余时间重新生成图片片段
            self.log_updated.emit(f"使用剩余时长 {remaining_time:.1f}s 重新生成图片片段")
            
            # 清空现有图片片段
            clips = []
            
            # 根据剩余时间和图片时长范围计算能放多少张图片
            if isinstance(self.image_duration, tuple):
                dmin, dmax = self.image_duration
            else:
                dmin = dmax = float(self.image_duration)
            
            self.log_updated.emit(f"图片时长范围: {dmin}-{dmax}s, 剩余时间: {remaining_time:.1f}s")
            
            # 计算能放多少张图片
            if dmin <= 0:
                self.log_updated.emit(f"错误: 图片最小时长({dmin})必须大于0")
                max_images = 0
            else:
                max_images = int(remaining_time / dmin)
                self.log_updated.emit(f"最多可放: {max_images}张图片")
            
            if max_images > 0 and len(image_files) > 0:
                # 重新生成图片片段，使用剩余时间
                current_time = 0.0
                for i in range(min(max_images, len(image_files))):
                    # 计算当前片段时长
                    remaining_for_this_image = remaining_time - current_time
                    if remaining_for_this_image <= 0:
                        break
                    
                    # 在范围内随机，但不超过剩余时间
                    if isinstance(self.image_duration, tuple):
                        rnd = random.random()
                        desired = dmin + (dmax - dmin) * rnd
                    else:
                        desired = float(self.image_duration)
                    
                    self.log_updated.emit(f"计算图片片段{i+1}: desired={desired:.1f}s, remaining={remaining_for_this_image:.1f}s")
                    
                    if desired <= 0 or remaining_for_this_image <= 0:
                        self.log_updated.emit(f"跳过图片片段{i+1}: desired={desired:.1f}s, remaining={remaining_for_this_image:.1f}s")
                        break
                    
                    clip_duration = min(desired, remaining_for_this_image)
                    
                    if clip_duration <= 0:
                        break
                    
                    try:
                        # 选择动画效果
                        effect = self.animation_effect
                        if effect == "随机效果":
                            effects = ['Slow Zoom In', 'Slow Zoom Out', 'Pan Left to Right', 'Pan Right to Left']
                            effect = random.choice(effects)
                        
                        # 创建图片片段
                        clip = create_animated_clip(
                            image_files[i], 
                            clip_duration, 
                            effect, 
                            self.animation_intensity,
                            self.resolution
                        )
                        
                        clips.append(clip)
                        current_time += clip_duration
                        self.log_updated.emit(f"重新生成图片片段{i+1}: {os.path.basename(image_files[i])}, 时长={clip_duration:.1f}s")
                        
                    except Exception as e:
                        self.log_updated.emit(f"重新生成图片片段失败 {os.path.basename(image_files[i])}: {str(e)}")
                        break
                
                # 验证重新生成后的总时长
                total_image_duration = sum(clip.duration for clip in clips)
                self.log_updated.emit(f"重新生成后图片片段总时长: {total_image_duration:.1f}s")
            else:
                self.log_updated.emit(f"剩余时间不足，无法生成图片片段")
            
            # 第六步：创建最终视频序列 - 随机穿插图片和视频片段
            final_clips = []
            
            # 创建所有片段的列表（图片 + 视频）
            all_segments = []
            
            # 添加图片片段
            for i, clip in enumerate(clips):
                all_segments.append({
                    'type': 'image',
                    'clip': clip,
                    'duration': clip.duration,
                    'name': f'图片片段{i+1}'
                })
            
            # 添加视频片段
            for i, data in enumerate(video_clip_data):
                try:
                    video_clip = data['clip']
                    if self.resolution:
                        video_clip = self._adjust_video_clip_resolution(video_clip)
                    
                    all_segments.append({
                        'type': 'video',
                        'clip': video_clip,
                        'duration': data['duration'],
                        'name': f'视频片段{i+1}: {os.path.basename(data["path"])}'
                    })
                    
                except Exception as e:
                    self.log_updated.emit(f"✗ 处理视频片段失败 {os.path.basename(data['path'])}: {str(e)}")
            
            # 随机打乱片段顺序
            random.shuffle(all_segments)
            self.log_updated.emit(f"随机打乱片段顺序，共 {len(all_segments)} 个片段")
            
            # 按顺序添加所有片段
            for i, segment in enumerate(all_segments):
                final_clips.append(segment['clip'])
                self.log_updated.emit(f"✓ 添加{segment['name']}: 时长={segment['duration']:.1f}s")
            
            # 计算最终总时长
            total_duration = sum(clip.duration for clip in final_clips)
            self.log_updated.emit(f"最终视频总时长: {total_duration:.1f}s (目标音频时长: {audio_duration:.1f}s)")
            
            if abs(total_duration - audio_duration) > 0.1:
                self.log_updated.emit(f"警告: 视频时长({total_duration:.1f}s)与音频时长({audio_duration:.1f}s)不匹配！")
            
            return final_clips
            
        except Exception as e:
            self.log_updated.emit(f"✗ 视频片段插入失败: {str(e)}")
            return clips
    
    def _adjust_video_clip_resolution(self, video_clip):
        """调整视频片段分辨率"""
        if not self.resolution:
            return video_clip
            
        target_width, target_height = self.resolution
        original_width, original_height = video_clip.size
        
        # 如果尺寸已经匹配，无需调整
        if original_width == target_width and original_height == target_height:
            self.log_updated.emit(f"视频片段尺寸已匹配: {original_width}x{original_height}")
            return video_clip
        
        # 根据缩放模式处理
        if self.video_clip_scale_mode == "stretch":
            # 拉伸模式：强制调整到目标尺寸（可能变形）
            video_clip = video_clip.resize((target_width, target_height))
            self.log_updated.emit(f"拉伸视频片段: {original_width}x{original_height} -> {target_width}x{target_height}")
            
        elif self.video_clip_scale_mode == "fit":
            # 适应模式：保持比例，添加黑边
            width_ratio = target_width / original_width
            height_ratio = target_height / original_height
            scale_ratio = min(width_ratio, height_ratio)  # 选择较小的比例
            
            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)
            
            # 缩放到合适尺寸
            video_clip = video_clip.resize((new_width, new_height))
            
            # 如果尺寸不匹配，添加黑边
            if new_width != target_width or new_height != target_height:
                # 创建黑色背景
                from moviepy.editor import ColorClip, CompositeVideoClip
                background = ColorClip(size=(target_width, target_height), color=(0, 0, 0), duration=video_clip.duration)
                
                # 计算居中位置
                x_offset = (target_width - new_width) // 2
                y_offset = (target_height - new_height) // 2
                
                # 将视频片段合成到背景上
                video_clip = CompositeVideoClip([background, video_clip.set_position((x_offset, y_offset))])
            
            self.log_updated.emit(f"适应模式调整: {original_width}x{original_height} -> {target_width}x{target_height} (保持比例)")
            
        else:  # crop 模式（默认）
            # 裁剪模式：保持比例，居中裁剪
            width_ratio = target_width / original_width
            height_ratio = target_height / original_height
            scale_ratio = max(width_ratio, height_ratio)  # 选择较大的比例确保填满目标尺寸
            
            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)
            
            # 先缩放到合适尺寸
            video_clip = video_clip.resize((new_width, new_height))
            
            # 居中裁剪到目标尺寸
            x_center = new_width // 2
            y_center = new_height // 2
            x1 = x_center - target_width // 2
            y1 = y_center - target_height // 2
            x2 = x1 + target_width
            y2 = y1 + target_height
            
            video_clip = video_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
            
            self.log_updated.emit(f"裁剪模式调整: {original_width}x{original_height} -> {target_width}x{target_height} (保持比例)")
        
        return video_clip
    
    def stop(self):
        """停止线程"""
        self._is_running = False
        self.quit()
        self.wait(5000)  # 等待最多5秒


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio-Driven Photo Slideshow Generator")
        self.setGeometry(100, 100, 800, 700)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 加载配置
        self.config = self.config_manager.load_config()
        
        # 存储选择的文件路径
        self.selected_image_folder = None
        self.selected_audio_file = None
        self.selected_audio_folder = None
        self.selected_processed_folder = None
        self.selected_output_folder = None
        self.selected_video_clip_folder = None
        
        # 处理模式
        self.processing_mode = "single"  # "single" 或 "batch"
        
        # 视频片段设置
        self.enable_video_clips = False
        self.video_clip_count = 3
        self.video_clip_scale_mode = "crop"  # "crop", "fit", "stretch"
        
        # 工作线程
        self.worker_thread = None
        
        self.setup_ui()
        self.load_config_to_ui()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止工作线程
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
        
        # 接受关闭事件
        event.accept()
    
    def load_config_to_ui(self):
        # 临时禁用自动保存，避免加载时触发保存
        self._loading_config = True
        
        # 加载文件路径
        if self.config.get("image_folder"):
            self.selected_image_folder = self.config["image_folder"]
            self.image_folder_label.setText(f"已选择: {os.path.basename(self.selected_image_folder)}")
        
        if self.config.get("audio_file"):
            self.selected_audio_file = self.config["audio_file"]
            self.audio_file_label.setText(f"已选择: {os.path.basename(self.selected_audio_file)}")
        
        if self.config.get("audio_folder"):
            self.selected_audio_folder = self.config["audio_folder"]
            self.audio_folder_label.setText(f"已选择: {os.path.basename(self.selected_audio_folder)}")
        
        # 加载处理模式
        self.processing_mode = self.config.get("processing_mode", "single")
        
        # 更新处理模式按钮状态
        if hasattr(self, 'single_mode_btn') and hasattr(self, 'batch_mode_btn'):
            if self.processing_mode == "single":
                self.single_mode_btn.setChecked(True)
                self.batch_mode_btn.setChecked(False)
            else:
                self.single_mode_btn.setChecked(False)
                self.batch_mode_btn.setChecked(True)
        
        if self.config.get("processed_folder"):
            self.selected_processed_folder = self.config["processed_folder"]
            self.processed_folder_label.setText(f"已选择: {os.path.basename(self.selected_processed_folder)}")
        
        if self.config.get("output_folder"):
            self.selected_output_folder = self.config["output_folder"]
            self.output_folder_label.setText(f"已选择: {os.path.basename(self.selected_output_folder)}")
        
        if self.config.get("video_clip_folder"):
            self.selected_video_clip_folder = self.config["video_clip_folder"]
            self.video_clip_folder_label.setText(f"已选择: {os.path.basename(self.selected_video_clip_folder)}")
        
        # 加载视频片段设置
        self.enable_video_clips = self.config.get("enable_video_clips", False)
        self.video_clip_count = self.config.get("video_clip_count", 3)
        self.video_clip_scale_mode = self.config.get("video_clip_scale_mode", "crop")
        
        # 更新视频片段UI状态
        if hasattr(self, 'enable_video_clips_checkbox'):
            self.enable_video_clips_checkbox.setChecked(self.enable_video_clips)
            self.video_clip_count_spin.setEnabled(self.enable_video_clips)
            self.video_clip_count_spin.setValue(self.video_clip_count)
            
            # 更新缩放模式下拉框
            if hasattr(self, 'video_clip_scale_combo'):
                if self.video_clip_scale_mode == "crop":
                    self.video_clip_scale_combo.setCurrentText("裁剪模式 (保持比例)")
                elif self.video_clip_scale_mode == "fit":
                    self.video_clip_scale_combo.setCurrentText("适应模式 (添加黑边)")
                elif self.video_clip_scale_mode == "stretch":
                    self.video_clip_scale_combo.setCurrentText("拉伸模式 (可能变形)")
            
            # 更新按钮样式
            if self.enable_video_clips:
                self.enable_video_clips_checkbox.setStyleSheet("""
                    QPushButton {
                        background-color: #28a745;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #218838;
                    }
                """)
            else:
                self.enable_video_clips_checkbox.setStyleSheet("""
                    QPushButton {
                        background-color: #6c757d;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #5a6268;
                    }
                """)
        
        # 加载参数设置
        self.duration_min_spin.setValue(self.config.get("image_duration_min", 4.0))
        self.duration_max_spin.setValue(self.config.get("image_duration_max", 6.0))
        
        effect = self.config.get("animation_effect", "Slow Zoom In")
        if effect in get_supported_effects():
            self.effect_combo.setCurrentText(effect)
        
        self.intensity_spinbox.setValue(self.config.get("animation_intensity", 1.0))
        
        # 加载分辨率设置
        resolution = self.config.get("resolution", "1920x1080 (16:9)")
        if resolution == "Custom...":
            self.resolution_combo.setCurrentText("Custom...")
            self.custom_width_spin.setValue(self.config.get("custom_width", 1920))
            self.custom_height_spin.setValue(self.config.get("custom_height", 1080))
        else:
            self.resolution_combo.setCurrentText(resolution)
        
        # 加载导出设置
        self.fps_spin.setValue(self.config.get("fps", 24))
        self.preset_combo.setCurrentText(self.config.get("preset", "ultrafast"))
        self.crf_spin.setValue(self.config.get("crf", 23))
        self.threads_spin.setValue(self.config.get("threads", 0))
        
        # 重新启用自动保存
        self._loading_config = False
    
    def save_config_from_ui(self):
        """将当前UI设置保存到配置"""
        config = {
            "image_folder": self.selected_image_folder or "",
            "audio_file": self.selected_audio_file or "",
            "audio_folder": self.selected_audio_folder or "",
            "processed_folder": self.selected_processed_folder or "",
            "output_folder": self.selected_output_folder or "",
            "video_clip_folder": self.selected_video_clip_folder or "",
            "processing_mode": self.processing_mode,
            "enable_video_clips": self.enable_video_clips,
            "video_clip_count": self.video_clip_count,
            "video_clip_scale_mode": self.video_clip_scale_mode,
            "image_duration_min": self.duration_min_spin.value(),
            "image_duration_max": self.duration_max_spin.value(),
            "animation_effect": self.effect_combo.currentText(),
            "animation_intensity": self.intensity_spinbox.value(),
            "resolution": self.resolution_combo.currentText(),
            "custom_width": self.custom_width_spin.value(),
            "custom_height": self.custom_height_spin.value(),
            "fps": self.fps_spin.value(),
            "preset": self.preset_combo.currentText(),
            "crf": self.crf_spin.value(),
            "threads": self.threads_spin.value()
        }
        self.config_manager.save_config(config)
        self.config = config
    
    def setup_ui(self):
        """设置用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("音频驱动的图片幻灯片生成器")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        main_layout.addWidget(title_label)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上半部分：控制面板
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setSpacing(15)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # 输入选择区
        input_group = self.create_input_selection_group()
        control_layout.addWidget(input_group)
        
        # 输出选择区
        output_group = self.create_output_selection_group()
        control_layout.addWidget(output_group)
        
        # 参数配置区
        config_group = self.create_configuration_group()
        control_layout.addWidget(config_group)
        
        # 执行与反馈区
        action_group = self.create_action_feedback_group()
        control_layout.addWidget(action_group)
        
        # 下半部分：日志面板
        log_group = self.create_log_panel()
        
        # 添加到分割器
        splitter.addWidget(control_widget)
        splitter.addWidget(log_group)
        splitter.setSizes([300, 300])  # 设置初始大小比例
        
        main_layout.addWidget(splitter)
    
    def create_input_selection_group(self) -> QGroupBox:
        """创建输入选择区"""
        group = QGroupBox("输入选择")
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # 图片文件夹选择
        folder_layout = QHBoxLayout()
        self.folder_btn = QPushButton("选择图片文件夹")
        self.folder_btn.clicked.connect(self.select_image_folder)
        self.image_folder_label = QLabel("未选择文件夹")
        self.image_folder_label.setWordWrap(True)
        self.image_folder_label.setStyleSheet("color: #666; font-style: italic;")
        
        folder_layout.addWidget(self.folder_btn)
        folder_layout.addWidget(self.image_folder_label, 1)
        layout.addLayout(folder_layout)
        
        # 音频文件选择
        audio_layout = QHBoxLayout()
        self.audio_btn = QPushButton("选择音频文件")
        self.audio_btn.clicked.connect(self.select_audio_file)
        self.audio_file_label = QLabel("未选择音频文件")
        self.audio_file_label.setWordWrap(True)
        self.audio_file_label.setStyleSheet("color: #666; font-style: italic;")
        
        audio_layout.addWidget(self.audio_btn)
        audio_layout.addWidget(self.audio_file_label, 1)
        layout.addLayout(audio_layout)
        
        # 音频文件夹选择
        audio_folder_layout = QHBoxLayout()
        self.audio_folder_btn = QPushButton("选择音频文件夹")
        self.audio_folder_btn.clicked.connect(self.select_audio_folder)
        self.audio_folder_label = QLabel("未选择音频文件夹")
        self.audio_folder_label.setWordWrap(True)
        self.audio_folder_label.setStyleSheet("color: #666; font-style: italic;")
        
        audio_folder_layout.addWidget(self.audio_folder_btn)
        audio_folder_layout.addWidget(self.audio_folder_label, 1)
        layout.addLayout(audio_folder_layout)
        
        # 处理模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("处理模式:")
        self.single_mode_btn = QPushButton("单个处理")
        self.batch_mode_btn = QPushButton("批量处理")
        
        # 设置按钮样式
        self.single_mode_btn.setCheckable(True)
        self.batch_mode_btn.setCheckable(True)
        self.single_mode_btn.setChecked(True)  # 默认选择单个处理
        
        # 连接信号
        self.single_mode_btn.clicked.connect(lambda: self.set_processing_mode("single"))
        self.batch_mode_btn.clicked.connect(lambda: self.set_processing_mode("batch"))
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.single_mode_btn)
        mode_layout.addWidget(self.batch_mode_btn)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # 视频片段设置
        video_clip_layout = QHBoxLayout()
        self.video_clip_btn = QPushButton("选择视频片段文件夹")
        self.video_clip_btn.clicked.connect(self.select_video_clip_folder)
        self.video_clip_folder_label = QLabel("未选择视频片段文件夹")
        self.video_clip_folder_label.setWordWrap(True)
        self.video_clip_folder_label.setStyleSheet("color: #666; font-style: italic;")
        
        video_clip_layout.addWidget(self.video_clip_btn)
        video_clip_layout.addWidget(self.video_clip_folder_label, 1)
        layout.addLayout(video_clip_layout)
        
        # 视频片段控制设置
        video_clip_control_layout = QHBoxLayout()
        
        # 是否插入视频片段开关
        self.enable_video_clips_checkbox = QPushButton("插入视频片段")
        self.enable_video_clips_checkbox.setCheckable(True)
        self.enable_video_clips_checkbox.setChecked(False)
        self.enable_video_clips_checkbox.clicked.connect(self.toggle_video_clips)
        
        # 视频片段数量设置
        clip_count_label = QLabel("插入数量:")
        self.video_clip_count_spin = QDoubleSpinBox()
        self.video_clip_count_spin.setRange(1, 10)
        self.video_clip_count_spin.setDecimals(0)
        self.video_clip_count_spin.setValue(3)
        self.video_clip_count_spin.setSuffix(" 个")
        self.video_clip_count_spin.setEnabled(False)
        self.video_clip_count_spin.valueChanged.connect(self.auto_save_config)
        
        video_clip_control_layout.addWidget(self.enable_video_clips_checkbox)
        video_clip_control_layout.addWidget(clip_count_label)
        video_clip_control_layout.addWidget(self.video_clip_count_spin)
        video_clip_control_layout.addStretch()
        layout.addLayout(video_clip_control_layout)
        
        # 视频片段缩放模式设置
        scale_mode_layout = QHBoxLayout()
        scale_mode_label = QLabel("缩放模式:")
        self.video_clip_scale_combo = QComboBox()
        self.video_clip_scale_combo.addItems(["裁剪模式 (保持比例)", "适应模式 (添加黑边)", "拉伸模式 (可能变形)"])
        self.video_clip_scale_combo.setCurrentText("裁剪模式 (保持比例)")
        self.video_clip_scale_combo.currentTextChanged.connect(self.on_scale_mode_changed)
        
        scale_mode_layout.addWidget(scale_mode_label)
        scale_mode_layout.addWidget(self.video_clip_scale_combo)
        scale_mode_layout.addStretch()
        layout.addLayout(scale_mode_layout)
        
        return group
    
    def create_output_selection_group(self) -> QGroupBox:
        """创建输出选择区"""
        group = QGroupBox("输出选择")
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # 输出视频文件夹选择
        output_layout = QHBoxLayout()
        self.output_btn = QPushButton("选择输出视频文件夹")
        self.output_btn.clicked.connect(self.select_output_folder)
        self.output_folder_label = QLabel("未选择输出文件夹")
        self.output_folder_label.setWordWrap(True)
        self.output_folder_label.setStyleSheet("color: #666; font-style: italic;")
        
        output_layout.addWidget(self.output_btn)
        output_layout.addWidget(self.output_folder_label, 1)
        layout.addLayout(output_layout)
        
        # 已处理图片文件夹选择
        processed_layout = QHBoxLayout()
        self.processed_btn = QPushButton("选择已处理图片文件夹")
        self.processed_btn.clicked.connect(self.select_processed_folder)
        self.processed_folder_label = QLabel("未选择已处理文件夹")
        self.processed_folder_label.setWordWrap(True)
        self.processed_folder_label.setStyleSheet("color: #666; font-style: italic;")
        
        processed_layout.addWidget(self.processed_btn)
        processed_layout.addWidget(self.processed_folder_label, 1)
        layout.addLayout(processed_layout)
        
        return group
    
    def create_configuration_group(self) -> QGroupBox:
        """创建参数配置区"""
        group = QGroupBox("参数配置")
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # 图片时长设置（范围）
        duration_layout = QHBoxLayout()
        duration_label = QLabel("每张图片播放时长范围 (秒):")
        self.duration_min_spin = QDoubleSpinBox()
        self.duration_min_spin.setRange(0.1, 60.0)
        self.duration_min_spin.setValue(4.0)
        self.duration_min_spin.setDecimals(1)
        self.duration_min_spin.setSuffix(" 秒")
        dash_label = QLabel(" - ")
        self.duration_max_spin = QDoubleSpinBox()
        self.duration_max_spin.setRange(0.1, 60.0)
        self.duration_max_spin.setValue(6.0)
        self.duration_max_spin.setDecimals(1)
        self.duration_max_spin.setSuffix(" 秒")
        
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_min_spin)
        duration_layout.addWidget(dash_label)
        duration_layout.addWidget(self.duration_max_spin)
        duration_layout.addStretch()
        layout.addLayout(duration_layout)
        
        # 动画效果设置
        effect_layout = QHBoxLayout()
        effect_label = QLabel("动画效果:")
        self.effect_combo = QComboBox()
        
        # 添加动画效果选项
        effects = ["随机效果", "Slow Zoom In", "Slow Zoom Out", 
                  "Pan Left to Right", "Pan Right to Left",
                  "Pan Diagonal Up Right", "Pan Diagonal Up Left",
                  "Pan Diagonal Down Right", "Pan Diagonal Down Left"]
        self.effect_combo.addItems(effects)
        self.effect_combo.setCurrentText("随机效果")
        
        effect_layout.addWidget(effect_label)
        effect_layout.addWidget(self.effect_combo)
        effect_layout.addStretch()
        layout.addLayout(effect_layout)
        
        # 动画强度设置
        intensity_layout = QHBoxLayout()
        intensity_label = QLabel("动画强度:")
        self.intensity_spinbox = QDoubleSpinBox()
        self.intensity_spinbox.setRange(0.1, 3.0)
        self.intensity_spinbox.setValue(1.0)
        self.intensity_spinbox.setDecimals(1)
        self.intensity_spinbox.setSingleStep(0.1)
        self.intensity_spinbox.setSuffix("x")
        
        # 添加强度说明标签
        intensity_info = QLabel("(0.1x=轻微, 1.0x=标准, 3.0x=强烈)")
        intensity_info.setStyleSheet("color: #666; font-size: 11px;")
        
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addWidget(self.intensity_spinbox)
        intensity_layout.addWidget(intensity_info)
        intensity_layout.addStretch()
        layout.addLayout(intensity_layout)

        # 分辨率设置
        resolution_layout = QHBoxLayout()
        resolution_label = QLabel("分辨率:")
        self.resolution_combo = QComboBox()
        # 预置常用分辨率（宽x高）
        self.resolution_combo.addItems([
            "1920x1080 (16:9)",
            "1280x720 (16:9)",
            "2560x1440 (16:9)",
            "3840x2160 (16:9)",
            "1080x1080 (1:1)",
            "1080x1920 (9:16)",
            "Custom..."
        ])
        self.resolution_combo.setCurrentIndex(0)  # 默认1920x1080

        # 自定义分辨率（可选）
        self.custom_width_spin = QDoubleSpinBox()
        self.custom_width_spin.setRange(320, 7680)
        self.custom_width_spin.setDecimals(0)
        self.custom_width_spin.setValue(1920)
        self.custom_width_spin.setSuffix(" w")
        self.custom_width_spin.setEnabled(False)

        self.custom_height_spin = QDoubleSpinBox()
        self.custom_height_spin.setRange(240, 4320)
        self.custom_height_spin.setDecimals(0)
        self.custom_height_spin.setValue(1080)
        self.custom_height_spin.setSuffix(" h")
        self.custom_height_spin.setEnabled(False)

        def on_resolution_changed(index: int):
            is_custom = (self.resolution_combo.currentText().startswith("Custom"))
            self.custom_width_spin.setEnabled(is_custom)
            self.custom_height_spin.setEnabled(is_custom)

        self.resolution_combo.currentIndexChanged.connect(on_resolution_changed)

        resolution_layout.addWidget(resolution_label)
        resolution_layout.addWidget(self.resolution_combo)
        resolution_layout.addWidget(self.custom_width_spin)
        resolution_layout.addWidget(self.custom_height_spin)
        resolution_layout.addStretch()
        layout.addLayout(resolution_layout)
        
        # 连接所有参数控件的信号到自动保存
        self.connect_config_signals()
        
        return group
    
    def connect_config_signals(self):
        """连接所有参数控件的信号到自动保存"""
        # 图片时长设置
        self.duration_min_spin.valueChanged.connect(self.auto_save_config)
        self.duration_max_spin.valueChanged.connect(self.auto_save_config)
        
        # 动画效果设置
        self.effect_combo.currentTextChanged.connect(self.auto_save_config)
        
        # 动画强度设置
        self.intensity_spinbox.valueChanged.connect(self.auto_save_config)
        
        # 分辨率设置
        self.resolution_combo.currentTextChanged.connect(self.auto_save_config)
        self.custom_width_spin.valueChanged.connect(self.auto_save_config)
        self.custom_height_spin.valueChanged.connect(self.auto_save_config)
    
    def auto_save_config(self):
        """自动保存配置"""
        # 如果正在加载配置，不执行自动保存
        if hasattr(self, '_loading_config') and self._loading_config:
            return
        self.save_config_from_ui()
    
    def create_action_feedback_group(self) -> QGroupBox:
        """创建执行与反馈区"""
        group = QGroupBox("执行与反馈")
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # 生成按钮
        # 生成按钮和重置配置按钮
        button_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("生成视频")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.clicked.connect(self.generate_video)
        
        self.reset_config_btn = QPushButton("重置配置")
        self.reset_config_btn.setMinimumHeight(50)
        self.reset_config_btn.clicked.connect(self.reset_config)
        self.reset_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        
        button_layout.addWidget(self.generate_btn)
        button_layout.addWidget(self.reset_config_btn)
        layout.addLayout(button_layout)

        # 性能/导出设置
        perf_layout = QHBoxLayout()
        fps_label = QLabel("FPS:")
        self.fps_spin = QDoubleSpinBox()
        self.fps_spin.setRange(12, 60)
        self.fps_spin.setDecimals(0)
        self.fps_spin.setValue(24)
        preset_label = QLabel("Preset:")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium"])  # 仅加速预设
        self.preset_combo.setCurrentText("ultrafast")
        crf_label = QLabel("CRF:")
        self.crf_spin = QDoubleSpinBox()
        self.crf_spin.setRange(15, 35)
        self.crf_spin.setDecimals(0)
        self.crf_spin.setValue(23)
        threads_label = QLabel("Threads:")
        self.threads_spin = QDoubleSpinBox()
        self.threads_spin.setRange(1, max(1, (os.cpu_count() or 2)))
        self.threads_spin.setDecimals(0)
        self.threads_spin.setValue(max(1, (os.cpu_count() or 2) - 1))

        perf_layout.addWidget(fps_label)
        perf_layout.addWidget(self.fps_spin)
        perf_layout.addSpacing(10)
        perf_layout.addWidget(preset_label)
        perf_layout.addWidget(self.preset_combo)
        perf_layout.addSpacing(10)
        perf_layout.addWidget(crf_label)
        perf_layout.addWidget(self.crf_spin)
        perf_layout.addSpacing(10)
        perf_layout.addWidget(threads_label)
        perf_layout.addWidget(self.threads_spin)
        layout.addLayout(perf_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # 连接性能设置控件的信号到自动保存
        self.connect_performance_signals()
        
        return group
    
    def connect_performance_signals(self):
        """连接性能设置控件的信号到自动保存"""
        # 性能/导出设置
        self.fps_spin.valueChanged.connect(self.auto_save_config)
        self.preset_combo.currentTextChanged.connect(self.auto_save_config)
        self.crf_spin.valueChanged.connect(self.auto_save_config)
        self.threads_spin.valueChanged.connect(self.auto_save_config)
    
    def create_log_panel(self) -> QGroupBox:
        """创建日志面板"""
        group = QGroupBox("处理日志")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 日志文本区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        # 清空日志按钮
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.clear_log)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        layout.addWidget(self.log_text)
        layout.addWidget(clear_btn)
        
        return group
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log_text.append("日志已清空")
    
    def add_log_message(self, message: str):
        """添加日志消息"""
        self.log_text.append(message)
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QDoubleSpinBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                min-width: 100px;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                min-width: 150px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 4px;
            }
        """)
    
    def select_image_folder(self):
        """选择图片文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "选择包含图片的文件夹"
        )
        
        if folder_path:
            self.selected_image_folder = folder_path
            self.image_folder_label.setText(f"已选择: {os.path.basename(folder_path)}")
            self.image_folder_label.setStyleSheet("color: #333; font-style: normal;")
            
            # 自动保存配置
            self.config_manager.update_config(image_folder=folder_path)
    
    def select_audio_file(self):
        """选择音频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.wma);;所有文件 (*)"
        )
        
        if file_path:
            self.selected_audio_file = file_path
            file_name = os.path.basename(file_path)
            self.audio_file_label.setText(f"已选择: {file_name}")
            self.audio_file_label.setStyleSheet("color: #333; font-style: normal;")
            
            # 自动保存配置
            self.config_manager.update_config(audio_file=file_path)
    
    def select_audio_folder(self):
        """选择音频文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "选择音频文件夹"
        )
        
        if folder_path:
            self.selected_audio_folder = folder_path
            self.audio_folder_label.setText(f"已选择: {os.path.basename(folder_path)}")
            self.audio_folder_label.setStyleSheet("color: #333; font-style: normal;")
            
            # 自动保存配置
            self.config_manager.update_config(audio_folder=folder_path)
    
    def set_processing_mode(self, mode: str):
        """设置处理模式"""
        self.processing_mode = mode
        
        # 更新按钮状态
        if mode == "single":
            self.single_mode_btn.setChecked(True)
            self.batch_mode_btn.setChecked(False)
        else:  # batch
            self.single_mode_btn.setChecked(False)
            self.batch_mode_btn.setChecked(True)
        
        # 保存配置
        self.config_manager.update_config(processing_mode=mode)
    
    def select_video_clip_folder(self):
        """选择视频片段文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "选择视频片段文件夹"
        )
        
        if folder_path:
            self.selected_video_clip_folder = folder_path
            self.video_clip_folder_label.setText(f"已选择: {os.path.basename(folder_path)}")
            self.video_clip_folder_label.setStyleSheet("color: #333; font-style: normal;")
            
            # 自动保存配置
            self.config_manager.update_config(video_clip_folder=folder_path)
    
    def toggle_video_clips(self):
        """切换视频片段插入功能"""
        self.enable_video_clips = self.enable_video_clips_checkbox.isChecked()
        self.video_clip_count_spin.setEnabled(self.enable_video_clips)
        
        # 更新按钮样式
        if self.enable_video_clips:
            self.enable_video_clips_checkbox.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
        else:
            self.enable_video_clips_checkbox.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
        
        # 保存配置
        self.config_manager.update_config(enable_video_clips=self.enable_video_clips)
    
    def on_scale_mode_changed(self, mode_text: str):
        """处理缩放模式变化"""
        if "裁剪模式" in mode_text:
            self.video_clip_scale_mode = "crop"
        elif "适应模式" in mode_text:
            self.video_clip_scale_mode = "fit"
        elif "拉伸模式" in mode_text:
            self.video_clip_scale_mode = "stretch"
        
        # 保存配置
        self.config_manager.update_config(video_clip_scale_mode=self.video_clip_scale_mode)
    
    def select_processed_folder(self):
        """选择已处理图片文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "选择已处理图片文件夹"
        )
        
        if folder_path:
            self.selected_processed_folder = folder_path
            self.processed_folder_label.setText(f"已选择: {os.path.basename(folder_path)}")
            self.processed_folder_label.setStyleSheet("color: #333; font-style: normal;")
            
            # 自动保存配置
            self.config_manager.update_config(processed_folder=folder_path)
    
    def select_output_folder(self):
        """选择输出视频文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "选择输出视频文件夹"
        )
        
        if folder_path:
            self.selected_output_folder = folder_path
            self.output_folder_label.setText(f"已选择: {os.path.basename(folder_path)}")
            self.output_folder_label.setStyleSheet("color: #333; font-style: normal;")
            
            # 自动保存配置
            self.config_manager.update_config(output_folder=folder_path)
            
    def reset_config(self):
        """重置配置为默认值"""
        reply = QMessageBox.question(
            self, 
            "确认重置", 
            "确定要重置所有配置为默认值吗？\n这将清除所有已选择的文件和设置。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 重置配置
            self.config_manager.reset_config()
            self.config = self.config_manager.load_config()
            
            # 重置UI
            self.selected_image_folder = None
            self.selected_audio_file = None
            self.selected_audio_folder = None
            self.selected_processed_folder = None
            self.selected_output_folder = None
            self.selected_video_clip_folder = None
            self.processing_mode = "single"
            self.enable_video_clips = False
            self.video_clip_count = 3
            self.video_clip_scale_mode = "crop"
            
            self.image_folder_label.setText("未选择文件夹")
            self.image_folder_label.setStyleSheet("color: #999; font-style: italic;")
            self.audio_file_label.setText("未选择音频文件")
            self.audio_file_label.setStyleSheet("color: #999; font-style: italic;")
            self.audio_folder_label.setText("未选择音频文件夹")
            self.audio_folder_label.setStyleSheet("color: #999; font-style: italic;")
            self.processed_folder_label.setText("未选择已处理文件夹")
            self.processed_folder_label.setStyleSheet("color: #999; font-style: italic;")
            self.output_folder_label.setText("未选择输出文件夹")
            self.output_folder_label.setStyleSheet("color: #999; font-style: italic;")
            self.video_clip_folder_label.setText("未选择视频片段文件夹")
            self.video_clip_folder_label.setStyleSheet("color: #999; font-style: italic;")
            
            # 重置处理模式按钮
            self.single_mode_btn.setChecked(True)
            self.batch_mode_btn.setChecked(False)
            
            # 重置视频片段设置
            self.enable_video_clips_checkbox.setChecked(False)
            self.video_clip_count_spin.setEnabled(False)
            self.video_clip_count_spin.setValue(3)
            self.video_clip_scale_combo.setCurrentText("裁剪模式 (保持比例)")
            
            # 重新加载配置到UI
            self.load_config_to_ui()
            
            QMessageBox.information(self, "重置完成", "配置已重置为默认值")
    
    def generate_video(self):
        """生成视频"""
        # 输入验证
        if not self.selected_image_folder:
            QMessageBox.warning(self, "警告", "请先选择图片文件夹")
            return
        
        if self.processing_mode == "single":
            if not self.selected_audio_file:
                QMessageBox.warning(self, "警告", "请先选择音频文件")
                return
            self.process_single_audio()
        else:  # batch mode
            if not self.selected_audio_folder:
                QMessageBox.warning(self, "警告", "请先选择音频文件夹")
                return
            self.process_batch_audio()
    
    def process_single_audio(self):
        """处理单个音频文件"""
        # 生成默认文件名（使用音频文件名）
        audio_basename = os.path.splitext(os.path.basename(self.selected_audio_file))[0]
        default_filename = f"{audio_basename}.mp4"
        
        if self.selected_output_folder:
            default_path = os.path.join(self.selected_output_folder, default_filename)
        else:
            default_path = default_filename
        
        # 检查文件是否已存在
        if os.path.exists(default_path):
            # 文件已存在，弹窗确认
            reply = QMessageBox.question(
                self,
                "文件已存在",
                f"文件 '{default_filename}' 已存在，是否覆盖？\n\n"
                f"路径: {default_path}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                # 用户选择不覆盖，打开文件对话框让用户选择其他位置或文件名
                output_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "保存视频文件",
                    default_path,
                    "MP4视频文件 (*.mp4);;所有文件 (*)"
                )
            else:
                # 用户选择覆盖，直接使用默认路径
                output_path = default_path
        else:
            # 文件不存在，直接使用默认路径
            output_path = default_path
        
        if not output_path:
            return
        
        # 保存输出文件夹到配置
        output_folder = os.path.dirname(output_path)
        self.selected_output_folder = output_folder
        self.output_folder_label.setText(f"已选择: {os.path.basename(output_folder)}")
        self.output_folder_label.setStyleSheet("color: #333; font-style: normal;")
        self.config_manager.update_config(output_folder=output_folder)
        
        # 开始处理单个音频
        self.start_video_generation(self.selected_audio_file, output_path)
    
    def process_batch_audio(self):
        """处理批量音频文件"""
        # 获取音频文件夹中的所有音频文件
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
        audio_files = []
        
        for file in os.listdir(self.selected_audio_folder):
            if any(file.lower().endswith(ext) for ext in audio_extensions):
                audio_files.append(os.path.join(self.selected_audio_folder, file))
        
        if not audio_files:
            QMessageBox.warning(self, "警告", "音频文件夹中没有找到支持的音频文件")
            return
        
        # 按文件名排序
        audio_files.sort()
        
        # 确认批量处理
        reply = QMessageBox.question(
            self,
            "确认批量处理",
            f"找到 {len(audio_files)} 个音频文件，是否开始批量处理？\n\n"
            f"音频文件列表:\n" + "\n".join([os.path.basename(f) for f in audio_files[:5]]) + 
            (f"\n... 还有 {len(audio_files) - 5} 个文件" if len(audio_files) > 5 else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始批量处理
        self.start_batch_processing(audio_files)
    
    def start_batch_processing(self, audio_files):
        """开始批量处理"""
        self.batch_audio_files = audio_files
        self.current_batch_index = 0
        self.process_next_batch_audio()
    
    def process_next_batch_audio(self):
        """处理下一个批量音频文件"""
        if self.current_batch_index >= len(self.batch_audio_files):
            # 批量处理完成
            self.add_log_message("=== 批量处理完成 ===")
            self.status_label.setText("批量处理完成！")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            QMessageBox.information(self, "批量处理完成", f"已成功处理 {len(self.batch_audio_files)} 个音频文件")
            
            # 清理工作线程
            if self.worker_thread:
                self.worker_thread.stop()
                self.worker_thread.deleteLater()
                self.worker_thread = None
            
            # 清理批量处理相关属性
            if hasattr(self, 'batch_audio_files'):
                delattr(self, 'batch_audio_files')
            if hasattr(self, 'current_batch_index'):
                delattr(self, 'current_batch_index')
            return
        
        current_audio = self.batch_audio_files[self.current_batch_index]
        audio_basename = os.path.splitext(os.path.basename(current_audio))[0]
        default_filename = f"{audio_basename}.mp4"
        
        if self.selected_output_folder:
            output_path = os.path.join(self.selected_output_folder, default_filename)
        else:
            output_path = default_filename
        
        # 如果文件已存在，添加序号
        counter = 1
        original_output_path = output_path
        while os.path.exists(output_path):
            name, ext = os.path.splitext(original_output_path)
            output_path = f"{name}_{counter}{ext}"
            counter += 1
        
        self.add_log_message(f"开始处理第 {self.current_batch_index + 1}/{len(self.batch_audio_files)} 个音频: {os.path.basename(current_audio)}")
        self.add_log_message(f"剩余待处理: {len(self.batch_audio_files) - self.current_batch_index - 1} 个音频文件")
        
        # 开始处理当前音频
        self.start_video_generation(current_audio, output_path)
    
    def start_video_generation(self, audio_file, output_path):
        """开始视频生成"""
        # 获取参数
        # 取时长范围并确保 min<=max
        dur_min = float(self.duration_min_spin.value())
        dur_max = float(self.duration_max_spin.value())
        if dur_min > dur_max:
            dur_min, dur_max = dur_max, dur_min
        animation_effect = self.effect_combo.currentText()
        animation_intensity = self.intensity_spinbox.value()
        # 解析分辨率
        selected_res = self.resolution_combo.currentText()
        if selected_res.startswith("Custom"):
            target_resolution = (int(self.custom_width_spin.value()), int(self.custom_height_spin.value()))
        else:
            try:
                wh = selected_res.split(" ")[0]
                w, h = wh.split("x")
                target_resolution = (int(w), int(h))
            except Exception:
                target_resolution = (1920, 1080)
        
        # 禁用生成按钮
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("生成中...")
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.worker_thread = VideoGenerationWorker(
            self.selected_image_folder,
            audio_file,
            (dur_min, dur_max),
            animation_effect,
            output_path,
            animation_intensity,
            target_resolution,
            int(self.fps_spin.value()),
            self.preset_combo.currentText(),
            int(self.crf_spin.value()),
            int(self.threads_spin.value()),
            self.selected_processed_folder,
            self.selected_video_clip_folder,
            self.enable_video_clips,
            int(self.video_clip_count_spin.value()),
            self.video_clip_scale_mode
        )
        
        # 连接信号
        self.worker_thread.progress_updated.connect(self.progress_bar.setValue)
        self.worker_thread.status_updated.connect(self.status_label.setText)
        self.worker_thread.log_updated.connect(self.add_log_message)
        self.worker_thread.generation_finished.connect(self.on_generation_finished)
        
        # 启动线程
        self.worker_thread.start()
    
    def on_generation_finished(self, success: bool, message: str):
        """处理生成完成"""
        # 恢复UI状态
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("生成视频")
        self.progress_bar.setVisible(False)
        
        # 检查是否是批量处理模式
        is_batch_mode = hasattr(self, 'batch_audio_files') and hasattr(self, 'current_batch_index')
        
        if success:
            self.status_label.setText("生成完成！")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            
            if is_batch_mode:
                # 批量处理模式，处理下一个文件
                self.add_log_message(f"✓ 第 {self.current_batch_index + 1} 个音频处理完成")
                self.current_batch_index += 1
                self.process_next_batch_audio()
            else:
                # 单个处理模式
                QMessageBox.information(self, "成功", message)
        else:
            self.status_label.setText("生成失败")
            self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            
            if is_batch_mode:
                # 批量处理模式，询问是否继续
                reply = QMessageBox.question(
                    self,
                    "批量处理错误",
                    f"处理第 {self.current_batch_index + 1} 个音频文件时出错：\n{message}\n\n是否继续处理剩余文件？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.add_log_message(f"✗ 第 {self.current_batch_index + 1} 个音频处理失败，继续处理下一个")
                    self.current_batch_index += 1
                    self.process_next_batch_audio()
                else:
                    # 停止批量处理
                    self.add_log_message("用户选择停止批量处理")
                    self.status_label.setText("批量处理已停止")
                    
                    # 清理工作线程
                    if self.worker_thread:
                        self.worker_thread.stop()
                        self.worker_thread.deleteLater()
                        self.worker_thread = None
                    
                    # 清理批量处理相关属性
                    if hasattr(self, 'batch_audio_files'):
                        delattr(self, 'batch_audio_files')
                    if hasattr(self, 'current_batch_index'):
                        delattr(self, 'current_batch_index')
            else:
                # 单个处理模式
                QMessageBox.critical(self, "错误", message)
        
        # 清理工作线程（只在非批量处理模式或批量处理完成时清理）
        if not is_batch_mode:
            if self.worker_thread:
                self.worker_thread.stop()
                self.worker_thread.deleteLater()
                self.worker_thread = None


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()