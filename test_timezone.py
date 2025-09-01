#!/usr/bin/env python3
"""
时区功能测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime
from app.services import convert_local_to_utc, convert_utc_to_local, get_user_timezone
from config import ConfigManager

def test_timezone_functions():
    """测试时区转换函数"""
    print("=== 时区功能测试 ===")
    
    # 测试当前时区设置
    current_timezone = get_user_timezone()
    print(f"当前用户时区: {current_timezone}")
    
    # 测试本地时间转UTC
    local_time = datetime(2024, 1, 1, 12, 0, 0)
    print(f"本地时间: {local_time}")
    
    utc_time = convert_local_to_utc(local_time)
    print(f"转换为UTC: {utc_time}")
    
    # 测试UTC转本地时间
    back_to_local = convert_utc_to_local(utc_time)
    print(f"转换回本地时间: {back_to_local}")
    
    # 验证往返转换是否一致
    if local_time == back_to_local:
        print("✅ 往返转换测试通过")
    else:
        print("❌ 往返转换测试失败")
    
    # 测试不同时区
    test_timezones = [
        'Asia/Shanghai',
        'Asia/Tokyo', 
        'America/New_York',
        'Europe/London',
        'UTC'
    ]
    
    print("\n=== 不同时区转换测试 ===")
    local_test_time = datetime(2024, 6, 15, 15, 30, 0)  # 夏季时间
    print(f"测试本地时间: {local_test_time}")
    
    for tz in test_timezones:
        try:
            utc_result = convert_local_to_utc(local_test_time, tz)
            local_result = convert_utc_to_local(utc_result, tz)
            print(f"{tz:20} -> UTC: {utc_result} -> 本地: {local_result}")
        except Exception as e:
            print(f"{tz:20} -> 错误: {e}")

def test_config_timezone():
    """测试配置文件中的时区设置"""
    print("\n=== 配置时区测试 ===")
    
    # 获取当前设置
    settings = ConfigManager.load_settings()
    print(f"配置文件中的时区: {settings.get('user_timezone', '未设置')}")
    
    # 测试保存时区设置
    test_timezone = 'Asia/Tokyo'
    success, message = ConfigManager.save_settings({'user_timezone': test_timezone})
    if success:
        print(f"✅ 成功保存时区设置: {test_timezone}")
        
        # 验证设置已保存
        new_settings = ConfigManager.load_settings()
        saved_timezone = new_settings.get('user_timezone')
        if saved_timezone == test_timezone:
            print(f"✅ 时区设置验证成功: {saved_timezone}")
        else:
            print(f"❌ 时区设置验证失败: 期望 {test_timezone}, 实际 {saved_timezone}")
    else:
        print(f"❌ 保存时区设置失败: {message}")

if __name__ == '__main__':
    test_timezone_functions()
    test_config_timezone()
