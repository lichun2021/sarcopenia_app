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
        # 32x96步道的段顺序，固定为端口1、2的顺序 [0, 1, 2]
        self.walkway_segment_order = [0, 1, 2]  # 对应端口1, 端口2的顺序
        
    def set_array_size(self, rows, cols):
        """设置阵列大小"""
        self.array_rows = rows
        self.array_cols = cols
        self.total_points = rows * cols
    
        
    def prepare_data(self, raw_data):
        """准备数据 - 快速调整数据长度以匹配阵列大小"""
        try:
            # 统一数据类型处理
            if isinstance(raw_data, (list, bytearray)):
                data_array = np.frombuffer(bytes(raw_data), dtype=np.uint8)
            elif isinstance(raw_data, bytes):
                data_array = np.frombuffer(raw_data, dtype=np.uint8)
            elif isinstance(raw_data, str):
                # 字符串类型，可能是错误传入
                raise ValueError(f"不能处理字符串类型的数据: {raw_data[:50]}...")
            else:
                data_array = np.asarray(raw_data, dtype=np.uint8)
        except Exception as e:
            raise ValueError(f"数据类型转换失败: {e}, 数据类型: {type(raw_data)}")
        
        data_len = len(data_array)
        
        # 其他阵列大小的正常处理
        if data_len < self.total_points:
            # 使用numpy的resize，更高效
            result = np.resize(data_array, self.total_points)
            return result, f"Padded ({data_len}->{self.total_points})"
            
        elif data_len > self.total_points:
            # 直接切片，避免复制
            result = data_array[:self.total_points]
            return result, f"Trimmed ({data_len}->{self.total_points})"
            
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
    
    def process_walkway_data(self, raw_data):
        """
        处理32x96步道数据：3个1024字节帧，每个先进行JQ变换，然后合并
        """
        try:
            # 确保数据是numpy数组
            if isinstance(raw_data, (bytes, bytearray)):
                data_array = np.frombuffer(raw_data, dtype=np.uint8)
            else:
                data_array = np.asarray(raw_data, dtype=np.uint8)
            
            data_len = len(data_array)
            
            if data_len < 3072:
                raise ValueError(f"步道数据长度不足，期望3072字节，实际{data_len}字节")
            
            # 分割成3个1024字节的段
            segment1 = data_array[:1024]
            segment2 = data_array[1024:2048]
            segment3 = data_array[2048:3072]
            
            # 对每个段进行JQ变换
            transformed_seg1 = self.jqbed_transform(segment1)
            transformed_seg2 = self.jqbed_transform(segment2) 
            transformed_seg3 = self.jqbed_transform(segment3)
            
            # 将每个变换后的1024字节段重塑为32x32
            matrix1 = transformed_seg1.reshape(32, 32)
            matrix2 = transformed_seg2.reshape(32, 32)
            matrix3 = transformed_seg3.reshape(32, 32)
            
            # 按照端口1、2的固定顺序合并成32x96
            matrices = [matrix1, matrix2, matrix3]
            ordered_matrices = [matrices[i] for i in self.walkway_segment_order]
            combined_matrix = np.hstack(ordered_matrices)
            
            return combined_matrix.ravel(), f"32x96 walkway processed (3x1024->JQ->combined)"
            
        except Exception as e:
            # 降级处理：直接使用原始数据
            try:
                if isinstance(raw_data, (bytes, bytearray)):
                    fallback_array = np.frombuffer(raw_data, dtype=np.uint8)
                else:
                    fallback_array = np.asarray(raw_data, dtype=np.uint8)
                
                if len(fallback_array) >= 3072:
                    return fallback_array[:3072], f"32x96 fallback (no JQ transform)"
                else:
                    # 数据不足，填充到3072
                    padded = np.resize(fallback_array, 3072)
                    return padded, f"32x96 padded fallback ({len(fallback_array)}->3072)"
                    
            except Exception as e2:
                # 最后的降级：返回零数组
                return np.zeros(3072, dtype=np.uint8), f"32x96 zeros fallback"
    
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
            
            # 数据类型检查和转换
            if isinstance(raw_data, str):
                # 如果是字符串，转换为字节
                raw_data = raw_data.encode('latin-1')
            elif not isinstance(raw_data, (bytes, bytearray, list, np.ndarray)):
                # 如果不是预期的数据类型，尝试转换
                raise ValueError(f"不支持的数据类型: {type(raw_data)}, 应为 bytes/bytearray/list/ndarray")
            
            # 特殊处理32x96步道数据
            if self.array_rows == 32 and self.array_cols == 96:
                transformed_data, prep_msg = self.process_walkway_data(raw_data)
                jq_applied = True  # 步道数据已经进行了JQ变换
            else:
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
            'sum_value': int(np.sum(matrix_2d)),
            'nonzero_count': int(np.count_nonzero(matrix_2d)),
            'contact_area': int(np.count_nonzero(matrix_2d)),  # 接触面积等于非零点数
            'total_points': int(matrix_2d.size)
        }
    
    def get_array_info(self):
        """获取阵列信息"""
        return {
            'rows': self.array_rows,
            'cols': self.array_cols,
            'total_points': self.total_points
        } 