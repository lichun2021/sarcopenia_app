#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志管理工具
根据config.ini配置控制日志记录行为
"""

import os
import configparser
from datetime import datetime
from typing import Optional

class LoggerUtils:
    """统一日志管理类"""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config = self._load_config(config_file)
        self._ensure_log_dir()
    
    def _load_config(self, config_file: str) -> dict:
        """加载配置文件"""
        config = configparser.ConfigParser()
        
        # 默认配置
        default_config = {
            'save_logs': False,
            'enable_debug': False,
            'verbose_logging': False,
            'logs_dir': 'logs'
        }
        
        try:
            if os.path.exists(config_file):
                config.read(config_file, encoding='utf-8')
                
                # 读取配置值
                if 'DEBUG' in config:
                    debug_section = config['DEBUG']
                    default_config['save_logs'] = debug_section.getboolean('save_logs', False)
                    default_config['enable_debug'] = debug_section.getboolean('enable_debug', False)
                    default_config['verbose_logging'] = debug_section.getboolean('verbose_logging', False)
                
                if 'PATHS' in config:
                    paths_section = config['PATHS']
                    default_config['logs_dir'] = paths_section.get('logs_dir', 'logs')
                    
        except Exception as e:
            print(f"[WARN] 加载配置文件失败，使用默认配置: {e}")
        
        return default_config
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if self.config['save_logs']:
            log_dir = self.config['logs_dir']
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except Exception as e:
                    print(f"[ERROR] 创建日志目录失败: {e}")
                    self.config['save_logs'] = False  # 禁用日志保存
    
    def log(self, message: str, level: str = "INFO", category: str = "SYSTEM"):
        """统一日志记录方法
        
        Args:
            message: 日志消息
            level: 日志级别 (DEBUG, INFO, WARN, ERROR)
            category: 日志分类 (SYSTEM, UI, DEVICE, ANALYSIS等)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] [{category}] {message}"
        
        # 控制台输出 (根据调试配置)
        if self.config['enable_debug'] or level in ['ERROR', 'WARN']:
            print(formatted_message)
        
        # 文件日志 (根据save_logs配置)
        if self.config['save_logs']:
            self._write_to_file(formatted_message, level, category)
    
    def _write_to_file(self, formatted_message: str, level: str, category: str):
        """写入日志文件"""
        try:
            log_dir = self.config['logs_dir']
            
            # 根据分类和级别决定日志文件
            if level == "ERROR":
                log_file = os.path.join(log_dir, "error.log")
            elif category == "DEVICE":
                log_file = os.path.join(log_dir, "device.log")
            elif category == "ANALYSIS":
                log_file = os.path.join(log_dir, "analysis.log")
            else:
                log_file = os.path.join(log_dir, "system.log")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_message + "\n")
                f.flush()
                
        except Exception as e:
            # 日志写入失败，只在控制台显示错误
            if self.config['enable_debug']:
                print(f"[ERROR] 日志写入失败: {e}")
    
    def debug(self, message: str, category: str = "DEBUG"):
        """调试日志"""
        if self.config['enable_debug'] or self.config['verbose_logging']:
            self.log(message, "DEBUG", category)
    
    def info(self, message: str, category: str = "INFO"):
        """信息日志"""
        self.log(message, "INFO", category)
    
    def warn(self, message: str, category: str = "WARN"):
        """警告日志"""
        self.log(message, "WARN", category)
    
    def error(self, message: str, category: str = "ERROR"):
        """错误日志"""
        self.log(message, "ERROR", category)
    
    def device_log(self, message: str, level: str = "INFO"):
        """设备相关日志"""
        self.log(message, level, "DEVICE")
    
    def analysis_log(self, message: str, level: str = "INFO"):
        """分析相关日志"""
        self.log(message, level, "ANALYSIS")
    
    def ui_log(self, message: str, level: str = "INFO"):
        """UI相关日志"""
        self.log(message, level, "UI")

# 全局日志实例
logger = LoggerUtils()

# 便捷函数
def log_debug(message: str, category: str = "DEBUG"):
    logger.debug(message, category)

def log_info(message: str, category: str = "INFO"):
    logger.info(message, category)

def log_warn(message: str, category: str = "WARN"):
    logger.warn(message, category)

def log_error(message: str, category: str = "ERROR"):
    logger.error(message, category)

def log_device(message: str, level: str = "INFO"):
    logger.device_log(message, level)

def log_analysis(message: str, level: str = "INFO"):
    logger.analysis_log(message, level)

def log_ui(message: str, level: str = "INFO"):
    logger.ui_log(message, level)