#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SarcNeuro Edge 依赖检查脚本
用于诊断服务启动失败的原因
"""

import sys
import subprocess
import os

def check_python_version():
    """检查Python版本"""
    print(f"Python版本: {sys.version}")
    return True

def check_dependencies():
    """检查所需依赖包"""
    required_packages = [
        'fastapi',
        'uvicorn', 
        'sqlalchemy',
        'pydantic',
        'numpy',
        'pandas',
        'python-multipart'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - 已安装")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_packages.append(package)
    
    return missing_packages

def check_service_directory():
    """检查服务目录和文件"""
    service_dir = "sarcneuro-edge"
    standalone_script = os.path.join(service_dir, "standalone_upload.py")
    
    if not os.path.exists(service_dir):
        print(f"❌ 服务目录不存在: {service_dir}")
        return False
    else:
        print(f"✅ 服务目录存在: {service_dir}")
    
    if not os.path.exists(standalone_script):
        print(f"❌ 启动脚本不存在: {standalone_script}")
        return False
    else:
        print(f"✅ 启动脚本存在: {standalone_script}")
    
    return True

def test_direct_import():
    """测试直接导入启动脚本"""
    print("\n测试直接导入启动脚本...")
    try:
        # 添加路径
        sys.path.insert(0, "sarcneuro-edge")
        
        # 测试导入
        import standalone_upload
        print("✅ 可以成功导入 standalone_upload")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def main():
    """主函数"""
    print("SarcNeuro Edge 依赖检查")
    print("=" * 50)
    
    # 检查Python版本
    check_python_version()
    print()
    
    # 检查服务目录
    if not check_service_directory():
        return
    print()
    
    # 检查依赖包
    print("检查依赖包:")
    missing = check_dependencies()
    print()
    
    if missing:
        print("缺少以下依赖包:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\n请安装缺少的依赖包:")
        print(f"pip install {' '.join(missing)}")
    else:
        print("✅ 所有依赖包都已安装")
        
        # 测试直接导入
        test_direct_import()

if __name__ == "__main__":
    main()