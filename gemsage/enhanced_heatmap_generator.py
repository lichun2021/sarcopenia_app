#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版热力图生成器 - 基于foot/test.py高质量算法
专业医学级热力图渲染，支持直接numpy数组输入
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 无GUI环境
import matplotlib.pyplot as plt
from matplotlib import cm
from scipy.ndimage import gaussian_filter, zoom
import base64
from io import BytesIO

class EnhancedHeatmapGenerator:
    """增强版热力图生成器 - 医学级高质量渲染"""
    
    def __init__(self, upscale=4, gaussian_sigma=1.2, medical_range=(0, 255)):
        """
        参数：
        - upscale: 升采样倍数，32x32 -> 32*upscale (推荐4)
        - gaussian_sigma: 高斯平滑强度 (推荐1.2)
        - medical_range: 医学色标范围 kPa (推荐0-100)
        """
        self.upscale = upscale
        self.gaussian_sigma = gaussian_sigma
        self.medical_min, self.medical_max = medical_range
        
        # 设置中文字体
        self._setup_chinese_font()
    
    def _setup_chinese_font(self):
        """设置中文字体"""
        plt.rcParams['font.sans-serif'] = [
            'Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans'
        ]
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
    
    def generate_heatmap(self, pressure_data, title="足底压力分布", save_path=None):
        """
        生成高质量热力图
        
        参数：
        - pressure_data: numpy数组，形状为 (height, width) 或 (frames, height, width)
        - title: 图表标题
        - save_path: 保存路径，如果为None则返回base64编码
        
        返回：
        - 如果save_path为None: 返回base64编码的PNG图像
        - 如果指定save_path: 保存文件并返回文件路径
        """
        # 处理输入数据
        if pressure_data.ndim == 3:
            # 如果是多帧数据，取平均值
            arr = pressure_data.mean(axis=0)
        else:
            arr = pressure_data.copy()
        
        # 处理不同尺寸的数据（支持臀部16x32格式）
        if arr.shape == (16, 32):
            # 16x32的臀部数据，可以直接处理
            print(f"处理臀部数据: {arr.shape}")
        elif arr.shape != (32, 32):
            print(f"警告: 数据形状为 {arr.shape}，期望 (32, 32) 或 (16, 32)")
            if arr.size == 1024:
                arr = arr.reshape(32, 32)
            else:
                # 尝试处理其他尺寸
                print(f"尝试处理非标准尺寸: {arr.shape}")
        
        # 高质量升采样和平滑处理
        arr_filled = np.nan_to_num(arr, nan=0.0)  # 填0以便插值
        
        # 双三次插值升采样
        target_shape = (arr.shape[0] * self.upscale, arr.shape[1] * self.upscale)
        arr_zoom = zoom(arr_filled, self.upscale, order=3)  # 双三次插值
        
        # 高斯平滑
        arr_smooth = gaussian_filter(arr_zoom, sigma=self.gaussian_sigma)
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # 医学级色彩映射 (兼容新版matplotlib)
        try:
            cmap = plt.colormaps.get_cmap('jet').copy()
            cmap.set_bad(color=(0, 0, 0, 0))  # 透明背景
        except AttributeError:
            # 兼容旧版matplotlib
            cmap = cm.get_cmap('jet').copy()
            try:
                cmap.set_bad(color=(0, 0, 0, 0))
            except Exception:
                cmap = cm.get_cmap('jet')
        
        # 绘制热力图
        im = ax.imshow(
            arr_smooth,
            cmap=cmap,
            vmin=self.medical_min,
            vmax=self.medical_max,
            origin='lower',
            interpolation='bicubic',
            aspect='equal',
            extent=[0, arr_smooth.shape[1], 0, arr_smooth.shape[0]]
        )
        
        # 颜色条
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('压力 (kPa)', rotation=270, labelpad=15)
        
        # 标题和布局
        plt.title(title, fontsize=16, pad=20)
        ax.set_xlim(0, arr_smooth.shape[1])
        ax.set_ylim(0, arr_smooth.shape[0])
        ax.set_xticks([])
        ax.set_yticks([])
        
        # 优化布局
        fig.tight_layout()
        fig.subplots_adjust(left=0.05, right=0.85, top=0.90, bottom=0.05)
        
        if save_path:
            # 保存到文件
            plt.savefig(save_path, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            return save_path
        else:
            # 返回base64编码
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()
            return image_base64
    
    def generate_left_right_heatmaps(self, pressure_data, title_prefix="压力分布"):
        """
        生成左右脚分离的热力图
        
        参数：
        - pressure_data: numpy数组 (frames, height, width) 或 (height, width)
        - title_prefix: 标题前缀
        
        返回：
        - (left_base64, right_base64): 左右脚热力图的base64编码
        """
        # 处理输入数据
        if pressure_data.ndim == 3:
            arr = pressure_data.mean(axis=0)
        else:
            arr = pressure_data.copy()
        
        if arr.shape != (32, 32):
            if arr.size == 1024:
                arr = arr.reshape(32, 32)
            else:
                raise ValueError(f"不支持的数据形状: {arr.shape}")
        
        # 分离左右脚 (假设左右各占一半)
        left_foot = arr[:, :16]   # 左半部分
        right_foot = arr[:, 16:]  # 右半部分
        
        # 生成左脚热力图
        left_base64 = self._generate_single_foot_heatmap(
            left_foot, f"{title_prefix} - 左脚"
        )
        
        # 生成右脚热力图  
        right_base64 = self._generate_single_foot_heatmap(
            right_foot, f"{title_prefix} - 右脚"
        )
        
        return left_base64, right_base64
    
    def _generate_single_foot_heatmap(self, foot_data, title):
        """生成单脚热力图"""
        # 升采样处理
        foot_filled = np.nan_to_num(foot_data, nan=0.0)
        foot_zoom = zoom(foot_filled, self.upscale, order=3)
        foot_smooth = gaussian_filter(foot_zoom, sigma=self.gaussian_sigma)
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(6, 8))
        
        # 色彩映射 (兼容新版matplotlib)
        try:
            cmap = plt.colormaps.get_cmap('jet').copy()
            cmap.set_bad(color=(0, 0, 0, 0))
        except AttributeError:
            # 兼容旧版matplotlib
            cmap = cm.get_cmap('jet').copy()
            try:
                cmap.set_bad(color=(0, 0, 0, 0))
            except Exception:
                cmap = cm.get_cmap('jet')
        
        # 绘制
        im = ax.imshow(
            foot_smooth,
            cmap=cmap,
            vmin=self.medical_min,
            vmax=self.medical_max,
            origin='lower',
            interpolation='bicubic',
            aspect='equal'
        )
        
        # 颜色条和布局
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('压力 (kPa)', rotation=270, labelpad=15)
        
        plt.title(title, fontsize=14, pad=15)
        ax.set_xticks([])
        ax.set_yticks([])
        
        fig.tight_layout()
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return image_base64


def test_enhanced_heatmap():
    """测试增强版热力图生成器"""
    # 创建测试数据（模拟32x32压力传感器）
    test_data = np.zeros((32, 32))
    
    # 模拟左脚压力分布
    test_data[10:25, 5:12] = 50  # 左脚跟
    test_data[5:15, 8:15] = 70   # 左脚掌
    
    # 模拟右脚压力分布
    test_data[10:25, 20:27] = 60  # 右脚跟
    test_data[5:15, 17:24] = 80   # 右脚掌
    
    # 添加一些噪声
    test_data += np.random.normal(0, 5, test_data.shape)
    test_data = np.maximum(test_data, 0)  # 确保非负
    
    # 创建生成器
    generator = EnhancedHeatmapGenerator()
    
    # 生成整体热力图
    print("生成整体热力图...")
    overall_base64 = generator.generate_heatmap(
        test_data, title="测试：足底压力分布"
    )
    print(f"整体热力图 base64 长度: {len(overall_base64)} 字符")
    
    # 生成左右分离热力图
    print("生成左右分离热力图...")
    left_base64, right_base64 = generator.generate_left_right_heatmaps(
        test_data, title_prefix="测试"
    )
    print(f"左脚热力图 base64 长度: {len(left_base64)} 字符")
    print(f"右脚热力图 base64 长度: {len(right_base64)} 字符")
    
    # 保存到文件测试
    print("保存到文件测试...")
    file_path = generator.generate_heatmap(
        test_data, title="测试：足底压力分布", 
        save_path="test_enhanced_heatmap.png"
    )
    print(f"热力图已保存到: {file_path}")
    
    return overall_base64, left_base64, right_base64


if __name__ == "__main__":
    test_enhanced_heatmap()