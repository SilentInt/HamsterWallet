#!/usr/bin/env python3
"""
修复时区问题的脚本
将所有直接使用 start_datetime 和 end_datetime 与 Receipt.transaction_time 比较的地方
替换为使用 convert_local_to_utc 转换后的时间进行比较
"""

import re
import os

def fix_timezone_in_file(file_path):
    """修复文件中的时区问题"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 模式1: Receipt.transaction_time >= start_datetime
    pattern1 = r'Receipt\.transaction_time\s*>=\s*start_datetime(?!_utc)'
    replacement1 = 'Receipt.transaction_time >= start_datetime_utc'
    content = re.sub(pattern1, replacement1, content)
    
    # 模式2: Receipt.transaction_time <= end_datetime
    pattern2 = r'Receipt\.transaction_time\s*<=\s*end_datetime(?!_utc)'
    replacement2 = 'Receipt.transaction_time <= end_datetime_utc'
    content = re.sub(pattern2, replacement2, content)
    
    # 添加UTC转换的代码（只在start_datetime行之前）
    # 查找所有 start_datetime = datetime.fromisoformat(start_date) 的行
    start_pattern = r'(\s+)start_datetime = datetime\.fromisoformat\(start_date\)'
    start_replacement = r'\1start_datetime = datetime.fromisoformat(start_date)\n\1# 将用户本地时间转换为UTC时间\n\1start_datetime_utc = convert_local_to_utc(start_datetime)'
    content = re.sub(start_pattern, start_replacement, content)
    
    # 查找所有 end_datetime = ... 的行（在replace之后）
    end_pattern = r'(\s+)(end_datetime = end_datetime\.replace\(\s*\n\s*hour=23, minute=59, second=59, microsecond=999999\s*\n\s*\))'
    end_replacement = r'\1\2\n\1# 将用户本地时间转换为UTC时间\n\1end_datetime_utc = convert_local_to_utc(end_datetime)'
    content = re.sub(end_pattern, end_replacement, content, flags=re.MULTILINE)
    
    # 简单的end_datetime模式
    simple_end_pattern = r'(\s+)(end_datetime = datetime\.fromisoformat\(end_date\))'
    simple_end_replacement = r'\1\2\n\1# 将用户本地时间转换为UTC时间\n\1end_datetime_utc = convert_local_to_utc(end_datetime)'
    content = re.sub(simple_end_pattern, simple_end_replacement, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已修复 {file_path}")
        return True
    else:
        print(f"无需修复 {file_path}")
        return False

def main():
    # 修复services.py文件
    services_file = 'app/services.py'
    if os.path.exists(services_file):
        fix_timezone_in_file(services_file)
    else:
        print(f"文件不存在: {services_file}")

if __name__ == "__main__":
    main()
