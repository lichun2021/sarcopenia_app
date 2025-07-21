#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理模块 - 负责压力传感器数据的处理和转换
"""

import numpy as np
from datetime import datetime

class DataProcessor:
    """数据处理器类"""
    
    def __init__(self, array_rows=32, array_cols=32):
        self.array_rows = array_rows
        self.array_cols = array_cols
        self.total_points = array_rows * array_cols
        
    def set_array_size(self, rows, cols):
        """设置阵列大小"""
        self.array_rows = rows
        self.array_cols = cols
        self.total_points = rows * cols
        
    def prepare_data(self, raw_data):
        """准备数据 - 快速调整数据长度以匹配阵列大小"""
        # 直接使用numpy处理，避免多次数据复制
        if isinstance(raw_data, (list, bytearray)):
            data_array = np.frombuffer(bytes(raw_data), dtype=np.uint8)
        else:
            data_array = np.asarray(raw_data, dtype=np.uint8)
        
        data_len = len(data_array)
        
        if data_len < self.total_points:
            # 使用numpy的resize，更高效
            result = np.resize(data_array, self.total_points)
            return result, f"Padded ({data_len}->{self.total_points})"
            
        elif data_len > self.total_points:
            # 直接切片，避免复制
            return data_array[:self.total_points], f"Trimmed ({data_len}->{self.total_points})"
            
        return data_array, "Perfect match"
    
    def jqbed_transform(self, data_array):
        """
        JQ公司的数据变换算法 - 优化版本
        基于提供的JavaScript伪代码实现
        """
        if len(data_array) != 1024:  # 32x32 = 1024
            raise ValueError("Data length must be 1024 (32x32)")
            
        # 使用视图而不是复制，提高性能
        ws_point_data = data_array.copy()  # 只复制一次
        ws_2d = ws_point_data.reshape(32, 32)
        
        # 第一步：1-15行调换 (使用numpy数组操作，更快)
        # 前8行分别与对应的后面行交换
        for i in range(8):
            mirror_row = 14 - i
            # 使用numpy的数组交换，比逐个元素交换快得多
            ws_2d[[i, mirror_row]] = ws_2d[[mirror_row, i]]
        
        # 第二步：将前15行移到后面 (1-15)(16-32) => (16-32)(1-15)
        # 使用numpy切片操作，避免创建中间副本
        result_2d = np.vstack([ws_2d[15:], ws_2d[:15]])
        
        # 重新展平为1D数组
        return result_2d.ravel()
    
    def process_frame_data(self, frame_data_dict, enable_jq_transform=True):
        """
        处理完整的帧数据
        
        Args:
            frame_data_dict: 包含数据、时间戳等信息的字典
            enable_jq_transform: 是否启用JQ变换
            
        Returns:
            dict: 处理后的数据字典
        """
        try:
            raw_data = frame_data_dict['data']
            
            # 1. 准备数据
            prepared_data, prep_msg = self.prepare_data(raw_data)
            
            # 2. 应用JQ变换（仅对32x32数据且用户启用时）
            if enable_jq_transform and self.array_rows == 32 and self.array_cols == 32:
                transformed_data = self.jqbed_transform(prepared_data)
                jq_applied = True
            else:
                transformed_data = prepared_data
                jq_applied = False
            
            # 3. 重塑为2D数组
            matrix_2d = transformed_data.reshape(self.array_rows, self.array_cols)
            
            # 4. 计算统计信息
            stats = self.calculate_statistics(matrix_2d)
            
            # 5. 返回处理结果
            result = {
                'original_frame': frame_data_dict,
                'matrix_2d': matrix_2d,
                'transformed_data': transformed_data,
                'preparation_msg': prep_msg,
                'statistics': stats,
                'processing_timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
                'array_size': f"{self.array_rows}x{self.array_cols}",
                'jq_transform_applied': jq_applied
            }
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'original_frame': frame_data_dict
            }
    
    def calculate_statistics(self, matrix_2d):
        """计算统计信息"""
        return {
            'max_value': int(np.max(matrix_2d)),
            'min_value': int(np.min(matrix_2d)),
            'mean_value': float(np.mean(matrix_2d)),
            'std_value': float(np.std(matrix_2d)),
            'nonzero_count': int(np.count_nonzero(matrix_2d)),
            'total_points': int(matrix_2d.size)
        }
    
    def get_array_info(self):
        """获取阵列信息"""
        return {
            'rows': self.array_rows,
            'cols': self.array_cols,
            'total_points': self.total_points
        } 