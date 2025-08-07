"""
数据格式转换器
将实时压力传感器数据转换为 SarcNeuro Edge 可识别的 CSV 格式
"""
import json
import numpy as np
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SarcopeniaDataConverter:
    """肌少症数据转换器"""
    
    def __init__(self):
        self.frame_interval = 0.01  # 默认10ms间隔 (100 FPS)
        
    def convert_frames_to_csv(
        self, 
        pressure_frames: List[List[int]], 
        start_time: Optional[datetime] = None,
        frame_rate: float = 100.0
    ) -> str:
        """
        将压力帧数据转换为CSV格式
        
        Args:
            pressure_frames: 压力数据帧列表，每帧为1024个整数的列表
            start_time: 开始时间，如果为None则使用当前时间
            frame_rate: 帧率 (FPS)
            
        Returns:
            CSV格式的字符串
        """
        if not pressure_frames:
            raise ValueError("压力数据帧为空")
            
        if start_time is None:
            start_time = datetime.now(timezone.utc)
            
        frame_interval = 1.0 / frame_rate
        csv_lines = ["time,max_pressure,timestamp,contact_area,total_pressure,data"]
        
        for i, frame in enumerate(pressure_frames):
            try:
                # 验证数据长度
                if len(frame) not in [1024, 2048, 3072]:  # 32x32, 32x64, 32x96
                    logger.warning(f"帧{i}: 数据长度异常({len(frame)}), 跳过")
                    continue
                
                # 计算时间
                time_val = i * frame_interval
                current_time = start_time.timestamp() + time_val
                timestamp = datetime.fromtimestamp(current_time, timezone.utc).isoformat().replace('+00:00', 'Z')
                
                # 计算压力统计
                frame_array = np.array(frame, dtype=int)
                max_pressure = int(np.max(frame_array))
                total_pressure = int(np.sum(frame_array))
                
                # 计算接触面积（压力值大于阈值的传感器数量）
                contact_threshold = max(10, max_pressure * 0.05)  # 动态阈值
                contact_area = int(np.sum(frame_array > contact_threshold))
                
                # 转换为JSON字符串
                data_json = json.dumps(frame)
                
                # 构建CSV行
                csv_line = f"{time_val:.3f},{max_pressure},{timestamp},{contact_area},{total_pressure},\"{data_json}\""
                csv_lines.append(csv_line)
                
            except Exception as e:
                logger.error(f"处理帧{i}时出错: {e}")
                continue
        
        if len(csv_lines) <= 1:
            raise ValueError("没有有效的压力数据帧")
            
        logger.info(f"成功转换{len(csv_lines)-1}帧数据为CSV格式")
        return "\n".join(csv_lines)
    
    def convert_single_frame_to_csv(
        self, 
        frame: List[int], 
        frame_index: int = 0,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        转换单帧数据为CSV格式（用于实时处理）
        
        Args:
            frame: 单帧压力数据
            frame_index: 帧索引
            timestamp: 时间戳
            
        Returns:
            CSV格式的单行数据
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        if len(frame) not in [1024, 2048, 3072]:
            raise ValueError(f"数据长度异常: {len(frame)}")
            
        # 计算统计值
        frame_array = np.array(frame, dtype=int)
        max_pressure = int(np.max(frame_array))
        total_pressure = int(np.sum(frame_array))
        
        contact_threshold = max(10, max_pressure * 0.05)
        contact_area = int(np.sum(frame_array > contact_threshold))
        
        time_val = frame_index * self.frame_interval
        timestamp_str = timestamp.isoformat().replace('+00:00', 'Z')
        data_json = json.dumps(frame)
        
        return f"{time_val:.3f},{max_pressure},{timestamp_str},{contact_area},{total_pressure},\"{data_json}\""
    
    def create_patient_info_dict(
        self,
        name: str,
        age: int, 
        gender: str,
        height: Optional[float] = None,
        weight: Optional[float] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建患者信息字典
        
        Args:
            name: 患者姓名
            age: 年龄
            gender: 性别 ("男" 或 "女")
            height: 身高(cm)
            weight: 体重(kg)
            phone: 电话
            email: 邮箱
            
        Returns:
            患者信息字典
        """
        # 性别转换
        gender_map = {"男": "MALE", "女": "FEMALE", "MALE": "MALE", "FEMALE": "FEMALE"}
        gender_en = gender_map.get(gender, "MALE")
        
        patient_info = {
            "name": name,
            "age": age,
            "gender": gender_en
        }
        
        if height is not None:
            patient_info["height"] = height
        if weight is not None:
            patient_info["weight"] = weight
        if phone:
            patient_info["phone"] = phone
        if email:
            patient_info["email"] = email
            
        return patient_info
    
    def estimate_quality_metrics(self, pressure_frames: List[List[int]]) -> Dict[str, Any]:
        """
        估算数据质量指标
        
        Args:
            pressure_frames: 压力数据帧
            
        Returns:
            数据质量指标字典
        """
        if not pressure_frames:
            return {"quality": "无数据", "score": 0}
            
        total_frames = len(pressure_frames)
        valid_frames = 0
        total_pressure_sum = 0
        max_pressures = []
        
        for frame in pressure_frames:
            if len(frame) in [1024, 2048, 3072]:
                valid_frames += 1
                frame_array = np.array(frame)
                total_pressure_sum += np.sum(frame_array)
                max_pressures.append(np.max(frame_array))
        
        if valid_frames == 0:
            return {"quality": "数据异常", "score": 0}
        
        # 计算质量指标
        validity_ratio = valid_frames / total_frames
        avg_total_pressure = total_pressure_sum / valid_frames
        pressure_stability = 1.0 - (np.std(max_pressures) / max(np.mean(max_pressures), 1))
        
        # 综合评分
        quality_score = (validity_ratio * 0.4 + 
                        min(avg_total_pressure / 50000, 1.0) * 0.3 + 
                        pressure_stability * 0.3) * 100
        
        quality_levels = [
            (90, "优秀"),
            (75, "良好"),
            (60, "一般"),
            (40, "较差"),
            (0, "很差")
        ]
        
        quality_text = "很差"
        for threshold, text in quality_levels:
            if quality_score >= threshold:
                quality_text = text
                break
        
        return {
            "quality": quality_text,
            "score": round(quality_score, 1),
            "valid_frames": valid_frames,
            "total_frames": total_frames,
            "validity_ratio": round(validity_ratio * 100, 1),
            "avg_pressure": round(avg_total_pressure, 1),
            "pressure_stability": round(pressure_stability * 100, 1)
        }

# 测试函数
def test_converter():
    """测试转换器功能"""
    converter = SarcopeniaDataConverter()
    
    # 创建模拟数据
    test_frames = []
    for i in range(100):  # 100帧数据
        # 创建模拟的32x32压力数据
        frame = [50 + int(30 * np.sin(i * 0.1 + j * 0.01)) for j in range(1024)]
        test_frames.append(frame)
    
    try:
        # 转换为CSV
        csv_data = converter.convert_frames_to_csv(test_frames, frame_rate=100.0)
        
        # 评估数据质量
        quality = converter.estimate_quality_metrics(test_frames)
        
        # 转换测试成功
        return csv_data
        
    except Exception as e:
        return None  # 转换测试失败

if __name__ == "__main__":
    test_converter()