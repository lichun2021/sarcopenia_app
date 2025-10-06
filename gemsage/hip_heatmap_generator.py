#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
臀部热力图生成器 - 基于foot/test.py高质量算法
专门用于五次起坐测试的臀部压力分析
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, zoom
import base64
from io import BytesIO

class HipHeatmapGenerator:
    """臀部热力图生成器 - 集成foot/test.py高质量算法"""

    def __init__(self, upscale=4, gaussian_sigma=1.2, medical_range=(0, 255)):
        """
        参数：
        - upscale: 升采样倍数，16x32 -> 16*upscale x 32*upscale (推荐4)
        - gaussian_sigma: 高斯平滑强度 (推荐1.2)
        - medical_range: 医学色标范围 (推荐0-255)
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

    def create_hip_mask(self, shape):
        """创建臀部区域mask - 针对臀部坐垫的形状"""
        rows, cols = shape
        mask = np.zeros((rows, cols), dtype=bool)

        # 臀部区域通常是椭圆形，覆盖大部分中央区域
        center_row, center_col = rows // 2, cols // 2

        for i in range(rows):
            for j in range(cols):
                # 椭圆形臀部区域
                normalized_i = (i - center_row) / (rows * 0.4)
                normalized_j = (j - center_col) / (cols * 0.3)
                if normalized_i**2 + normalized_j**2 <= 1:
                    mask[i, j] = True

        # 高斯平滑mask边缘
        mask = gaussian_filter(mask.astype(float), sigma=0.8) > 0.3
        return mask

    def generate_hip_heatmap(self, hip_data, title="臀部压力分布", save_path=None):
        """
        生成高质量臀部热力图 - 基于read/test.py的cushion算法

        参数：
        - hip_data: numpy数组，形状为 (height, width) 或 (frames, height, width)
        - title: 图表标题
        - save_path: 保存路径，如果为None则返回base64编码
        """
        # 处理输入数据
        if hip_data.ndim == 3:
            # 如果是多帧数据，取平均值
            arr = hip_data.mean(axis=0)
        else:
            arr = hip_data.copy()

        print(f"📍 生成臀部热力图，数据形状: {arr.shape}")

        # 使用read/test.py的cushion(坐垫)专用算法
        # -------------------------
        # 升采样和平滑（生成高分辨率）
        # -------------------------
        upscale = self.upscale

        # 填0以便插值（避免NaN影响插值质量）
        arr_filled = np.nan_to_num(arr, nan=0.0)

        # 双三次插值升采样 - read/test.py核心算法
        arr_zoom = zoom(arr_filled, upscale, order=3)

        # 高斯平滑 - read/test.py参数
        arr_smooth = gaussian_filter(arr_zoom, sigma=self.gaussian_sigma)

        # *** read/test.py的cushion专用处理 ***
        from scipy.ndimage import median_filter

        # 1. 使用中值滤波去除噪点（3x3窗口，保持边缘和压力分布）
        display_matrix = median_filter(arr_smooth, size=3)

        # 2. 放大压力值（提高到10倍以获得更好的视觉效果）
        display_matrix = display_matrix * 10

        # 3. 应用对比度增强
        # 将低值区域进一步降低，高值区域进一步提高
        # 使用幂次变换增强对比度，避免无效值
        normalized = display_matrix / 255.0
        normalized = np.clip(normalized, 0.0, 1.0)  # 确保在有效范围内
        display_matrix = np.power(normalized, 0.8) * 255

        # 4. 确保不超过255
        arr_smooth = np.minimum(display_matrix, 255)

        print(f"🦴 应用cushion算法: 中值滤波 + 10倍放大 + 对比度增强")

        # 固定色标（医学常用做法）- foot/test.py方法
        vmin, vmax = self.medical_min, self.medical_max

        # jet色表，设bad为透明 - foot/test.py配置
        try:
            cmap = plt.get_cmap('jet').copy()
            cmap.set_bad(color=(0, 0, 0, 0))  # 完全透明
        except Exception:
            cmap = plt.get_cmap('jet')
            cmap.set_bad(color=(0, 0, 0, 0))

        # -------------------------
        # 绘图与渲染 - read/test.py高质量设置
        # -------------------------
        # 调整图像为正方形，与脚印图相似大小
        fig, ax = plt.subplots(figsize=(7, 7))

        # 高质量渲染 - read/test.py参数，强制正方形显示
        im = ax.imshow(
            arr_smooth,
            cmap=cmap,
            vmin=vmin, vmax=vmax,
            origin='lower',
            interpolation='bicubic',  # read/test.py使用的高质量插值
            aspect='equal',  # 保持正方形像素比例
            extent=[0, arr_smooth.shape[1], 0, arr_smooth.shape[1]]  # 强制正方形显示范围
        )

        # colorbar设置 - foot/test.py配置
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('压力 (kPa)', rotation=270, labelpad=15)

        # 标题和轴设置 - 强制正方形
        ax.set_title(title, fontsize=14, pad=15)
        ax.set_xlim(0, arr_smooth.shape[1])
        ax.set_ylim(0, arr_smooth.shape[1])  # 使用相同的范围确保正方形
        ax.set_xticks([])
        ax.set_yticks([])

        # 布局调整 - read/test.py方法，确保正方形显示
        fig.tight_layout()
        fig.subplots_adjust(left=0.05, right=0.85, top=0.95, bottom=0.05)

        # 保存或返回base64
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            return save_path
        else:
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()
            return image_base64

    def generate_five_hip_heatmaps(self, sitstand_data, base_title="起坐臀部压力"):
        """
        为五次起坐生成5张高质量臀部热力图
        使用foot/test.py的升采样+平滑算法
        """
        if sitstand_data is None or len(sitstand_data) == 0:
            return []

        heatmap_images = []
        total_frames = len(sitstand_data)

        # 将数据分为5个阶段
        segment_size = total_frames // 5

        for i in range(5):
            start_idx = i * segment_size
            if i == 4:  # 最后一段包含所有剩余帧
                end_idx = total_frames
            else:
                end_idx = (i + 1) * segment_size

            # 提取当前阶段的数据
            segment_data = sitstand_data[start_idx:end_idx]

            # 提取臀部区域
            if segment_data.shape[1] == 64:
                # 64x32格式：前32行是臀部
                hip_data = segment_data[:, :32, :]
                print(f"📍 提取臀部区域 (64x32 → 32x32臀部)")
            else:
                # 32x32格式：上半部分是臀部
                hip_data = segment_data[:, :16, :]
                print(f"📍 提取臀部区域 (32x32 → 16x32臀部)")

            # 生成高质量臀部热力图
            title = f"{base_title} - 第{i+1}次"

            try:
                print(f"🔥 使用foot/test.py算法生成第{i+1}次臀部热力图")
                image_base64 = self.generate_hip_heatmap(hip_data, title)
                if image_base64:
                    heatmap_images.append(image_base64)
                    print(f"   ✅ 第{i+1}次臀部热力图生成成功")
                else:
                    print(f"   ❌ 第{i+1}次臀部热力图生成失败")
            except Exception as e:
                print(f"   ❌ 第{i+1}次臀部热力图生成失败: {e}")

        return heatmap_images