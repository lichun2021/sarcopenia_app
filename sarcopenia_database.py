#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
肌少症检测系统统一数据库管理模块
包含患者档案、设备配置、检测记录等所有数据管理
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class SarcopeniaDatabase:
    """肌少症检测系统统一数据库管理类"""
    
    def __init__(self, db_path="sarcopenia_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 患者档案表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    gender TEXT NOT NULL CHECK (gender IN ('男', '女')),
                    age INTEGER NOT NULL CHECK (age > 0 AND age <= 120),
                    height REAL CHECK (height IS NULL OR (height >= 50 AND height <= 250)),
                    weight REAL CHECK (weight IS NULL OR (weight >= 10 AND weight <= 300)),
                    phone TEXT,
                    notes TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_time TEXT NOT NULL,
                    updated_time TEXT NOT NULL
                )
            ''')
            
            # 设备配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    serial_port TEXT NOT NULL,
                    baud_rate INTEGER DEFAULT 1000000,
                    array_rows INTEGER DEFAULT 32,
                    array_cols INTEGER DEFAULT 32,
                    is_active BOOLEAN DEFAULT 1,
                    config_data TEXT,
                    created_time TEXT NOT NULL,
                    updated_time TEXT NOT NULL
                )
            ''')
            
            # 检测会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    session_name TEXT NOT NULL,
                    test_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'interrupted')),
                    current_step INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 6,
                    created_time TEXT NOT NULL,
                    completed_time TEXT,
                    notes TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
                )
            ''')
            
            # 检测步骤详情表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    step_number INTEGER NOT NULL,
                    step_name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    duration INTEGER,
                    repetitions INTEGER DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),
                    data_file_path TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    notes TEXT,
                    FOREIGN KEY (session_id) REFERENCES test_sessions (id) ON DELETE CASCADE
                )
            ''')
            
            # 检测数据文件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_data_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    created_time TEXT NOT NULL,
                    FOREIGN KEY (step_id) REFERENCES test_steps (id) ON DELETE CASCADE
                )
            ''')
            
            # AI分析结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    analysis_type TEXT NOT NULL,
                    analysis_data TEXT NOT NULL,
                    ai_report_path TEXT,
                    confidence_score REAL,
                    created_time TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES test_sessions (id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            print("[INFO] 肌少症检测系统数据库初始化完成")
            
        except Exception as e:
            print(f"[ERROR] 数据库初始化失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # ==================== 患者档案管理 ====================
    def add_patient(self, name: str, gender: str, age: int, height: Optional[float] = None, 
                   weight: Optional[float] = None, phone: Optional[str] = None, 
                   notes: Optional[str] = None) -> int:
        """添加新患者档案"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO patients 
                (name, gender, age, height, weight, phone, notes, created_time, updated_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, gender, age, height, weight, phone, notes, current_time, current_time))
            
            patient_id = cursor.lastrowid
            conn.commit()
            print(f"[INFO] 患者档案已添加: {name} (ID: {patient_id})")
            return patient_id
            
        except Exception as e:
            print(f"[ERROR] 添加患者档案失败: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    def get_all_patients(self) -> List[Dict]:
        """获取所有活跃患者档案"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, name, gender, age, height, weight, phone, notes, created_time, updated_time
                FROM patients
                WHERE is_active = 1
                ORDER BY updated_time DESC
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            patients = []
            for row in cursor.fetchall():
                patient = dict(zip(columns, row))
                patients.append(patient)
            
            return patients
            
        except Exception as e:
            print(f"[ERROR] 获取患者档案失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_patient_by_id(self, patient_id: int) -> Optional[Dict]:
        """根据ID获取患者档案"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, name, gender, age, height, weight, phone, notes, created_time, updated_time
                FROM patients
                WHERE id = ? AND is_active = 1
            ''', (patient_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            print(f"[ERROR] 获取患者档案失败: {e}")
            return None
        finally:
            conn.close()
    
    def search_patients(self, keyword: str) -> List[Dict]:
        """搜索患者档案"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, name, gender, age, height, weight, phone, notes, created_time, updated_time
                FROM patients
                WHERE is_active = 1 AND (name LIKE ? OR phone LIKE ? OR notes LIKE ?)
                ORDER BY updated_time DESC
            ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            
            columns = [desc[0] for desc in cursor.description]
            patients = []
            for row in cursor.fetchall():
                patient = dict(zip(columns, row))
                patients.append(patient)
            
            return patients
            
        except Exception as e:
            print(f"[ERROR] 搜索患者档案失败: {e}")
            return []
        finally:
            conn.close()
    
    def update_patient(self, patient_id: int, **kwargs) -> bool:
        """更新患者档案"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 构建更新字段
            fields = []
            values = []
            for key, value in kwargs.items():
                if key in ['name', 'gender', 'age', 'height', 'weight', 'phone', 'notes']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if not fields:
                return False
            
            # 添加更新时间
            fields.append("updated_time = ?")
            values.append(datetime.now().isoformat())
            values.append(patient_id)
            
            cursor.execute(f'''
                UPDATE patients 
                SET {', '.join(fields)}
                WHERE id = ?
            ''', values)
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                print(f"[INFO] 患者档案已更新: ID {patient_id}")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] 更新患者档案失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_patient(self, patient_id: int) -> bool:
        """删除患者档案（软删除）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('UPDATE patients SET is_active = 0 WHERE id = ?', (patient_id,))
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                print(f"[INFO] 患者档案已删除: ID {patient_id}")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] 删除患者档案失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ==================== 设备配置管理 ====================
    def add_device_config(self, device_name: str, device_type: str, serial_port: str, 
                         baud_rate: int = 1000000, array_rows: int = 32, array_cols: int = 32,
                         config_data: str = None) -> int:
        """添加设备配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO device_configs 
                (device_name, device_type, serial_port, baud_rate, array_rows, array_cols, config_data, created_time, updated_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (device_name, device_type, serial_port, baud_rate, array_rows, array_cols, config_data, current_time, current_time))
            
            config_id = cursor.lastrowid
            conn.commit()
            print(f"[INFO] 设备配置已添加: {device_name} (ID: {config_id})")
            return config_id
            
        except Exception as e:
            print(f"[ERROR] 添加设备配置失败: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    def get_all_device_configs(self) -> List[Dict]:
        """获取所有活跃设备配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, device_name, device_type, serial_port, baud_rate, array_rows, array_cols, 
                       config_data, created_time, updated_time
                FROM device_configs
                WHERE is_active = 1
                ORDER BY updated_time DESC
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            configs = []
            for row in cursor.fetchall():
                config = dict(zip(columns, row))
                configs.append(config)
            
            return configs
            
        except Exception as e:
            print(f"[ERROR] 获取设备配置失败: {e}")
            return []
        finally:
            conn.close()
    
    # ==================== 检测会话管理 ====================
    def create_test_session(self, patient_id: int, session_name: str) -> int:
        """创建新的检测会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO test_sessions 
                (patient_id, session_name, test_date, status, created_time)
                VALUES (?, ?, ?, 'pending', ?)
            ''', (patient_id, session_name, current_time, current_time))
            
            session_id = cursor.lastrowid
            
            # 初始化6个检测步骤
            test_steps = [
                (1, "静坐检测", "坐垫", 10, 1),
                (2, "起坐测试", "坐垫", 30, 5),
                (3, "静态站立", "脚垫", 10, 1),  
                (4, "前后脚站立", "脚垫", 10, 1),
                (5, "双脚前后站立", "脚垫", 10, 1),
                (6, "4.5米步道折返", "步道", 60, 1)
            ]
            
            for step_num, step_name, device, duration, reps in test_steps:
                cursor.execute('''
                    INSERT INTO test_steps 
                    (session_id, step_number, step_name, device_type, duration, repetitions, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending')
                ''', (session_id, step_num, step_name, device, duration, reps))
            
            conn.commit()
            print(f"[INFO] 检测会话已创建: {session_name} (ID: {session_id})")
            return session_id
            
        except Exception as e:
            print(f"[ERROR] 创建检测会话失败: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    def get_patient_test_sessions(self, patient_id: int) -> List[Dict]:
        """获取患者的检测会话列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, session_name, test_date, status, current_step, total_steps, 
                       created_time, completed_time, notes
                FROM test_sessions
                WHERE patient_id = ?
                ORDER BY created_time DESC
            ''', (patient_id,))
            
            columns = [desc[0] for desc in cursor.description]
            sessions = []
            for row in cursor.fetchall():
                session = dict(zip(columns, row))
                sessions.append(session)
            
            return sessions
            
        except Exception as e:
            print(f"[ERROR] 获取检测会话失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_session_steps(self, session_id: int) -> List[Dict]:
        """获取检测会话的步骤详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, step_number, step_name, device_type, duration, repetitions, 
                       status, data_file_path, start_time, end_time, notes
                FROM test_steps
                WHERE session_id = ?
                ORDER BY step_number
            ''', (session_id,))
            
            columns = [desc[0] for desc in cursor.description]
            steps = []
            for row in cursor.fetchall():
                step = dict(zip(columns, row))
                steps.append(step)
            
            return steps
            
        except Exception as e:
            print(f"[ERROR] 获取检测步骤失败: {e}")
            return []
        finally:
            conn.close()
    
    def update_test_session_progress(self, session_id: int, current_step: int, status: str = None) -> bool:
        """更新检测会话进度"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if status:
                if status == 'completed':
                    cursor.execute('''
                        UPDATE test_sessions 
                        SET current_step = ?, status = ?, completed_time = ?
                        WHERE id = ?
                    ''', (current_step, status, datetime.now().isoformat(), session_id))
                else:
                    cursor.execute('''
                        UPDATE test_sessions 
                        SET current_step = ?, status = ?
                        WHERE id = ?
                    ''', (current_step, status, session_id))
            else:
                cursor.execute('''
                    UPDATE test_sessions 
                    SET current_step = ?
                    WHERE id = ?
                ''', (current_step, session_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except Exception as e:
            print(f"[ERROR] 更新检测会话进度失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def update_test_step_status(self, step_id: int, status: str, data_file_path: str = None, 
                               start_time: str = None, end_time: str = None, notes: str = None) -> bool:
        """更新检测步骤状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            update_fields = ["status = ?"]
            values = [status]
            
            if data_file_path:
                update_fields.append("data_file_path = ?")
                values.append(data_file_path)
            
            if start_time:
                update_fields.append("start_time = ?")
                values.append(start_time)
            
            if end_time:
                update_fields.append("end_time = ?")
                values.append(end_time)
            
            if notes:
                update_fields.append("notes = ?")
                values.append(notes)
            
            values.append(step_id)
            
            cursor.execute(f'''
                UPDATE test_steps 
                SET {', '.join(update_fields)}
                WHERE id = ?
            ''', values)
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except Exception as e:
            print(f"[ERROR] 更新检测步骤状态失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_test_session(self, session_id: int) -> bool:
        """删除检测会话及其所有步骤"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 先删除所有步骤
            cursor.execute('DELETE FROM test_steps WHERE session_id = ?', (session_id,))
            
            # 再删除会话
            cursor.execute('DELETE FROM test_sessions WHERE id = ?', (session_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                print(f"[INFO] 成功删除会话 ID: {session_id}")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] 删除检测会话失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

# 全局数据库实例
db = SarcopeniaDatabase()

# 测试代码
if __name__ == "__main__":
    # 测试患者档案
    patient_id = db.add_patient("张三", "男", 65, 170.0, 70.0, "13800138000", "测试患者")
    
    if patient_id > 0:
        # 测试检测会话
        session_id = db.create_test_session(patient_id, f"检测-{datetime.now().strftime('%Y%m%d%H%M')}")
        
        # 获取患者信息
        patient = db.get_patient_by_id(patient_id)
        print(f"患者信息: {patient}")
        
        # 获取检测会话
        sessions = db.get_patient_test_sessions(patient_id)
        print(f"检测会话: {sessions}")
        
        # 获取检测步骤
        if session_id > 0:
            steps = db.get_session_steps(session_id)
            print(f"检测步骤: {steps}")