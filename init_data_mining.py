#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
用于创建ComparisonGroup表并测试数据挖掘功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.database import db
from app.models import ComparisonGroup
import json


def init_database():
    """初始化数据库"""
    print("正在初始化数据库...")

    app = create_app()

    with app.app_context():
        try:
            # 创建所有表
            db.create_all()
            print("✅ 数据库表创建成功")

            # 检查ComparisonGroup表是否存在
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            if "comparison_groups" in tables:
                print("✅ ComparisonGroup表创建成功")
            else:
                print("❌ ComparisonGroup表创建失败")
                return False

            # 测试创建一个示例对比组
            test_categories = [
                {
                    "name": "食品",
                    "path": ["食品"],
                    "total_cny": 1000.0,
                    "item_count": 50,
                },
                {
                    "name": "饮料",
                    "path": ["食品", "饮料"],
                    "total_cny": 200.0,
                    "item_count": 10,
                },
            ]

            test_group = ComparisonGroup(
                name="测试对比组",
                categories_data=json.dumps(test_categories, ensure_ascii=False),
            )

            db.session.add(test_group)
            db.session.commit()

            print(f"✅ 测试对比组创建成功，ID: {test_group.id}")

            # 验证可以正确读取
            saved_group = ComparisonGroup.query.get(test_group.id)
            if saved_group:
                categories = json.loads(saved_group.categories_data)
                print(f"✅ 数据验证成功，对比组名称: {saved_group.name}")
                print(f"   分类数量: {len(categories)}")

                # 清理测试数据
                db.session.delete(saved_group)
                db.session.commit()
                print("✅ 测试数据清理完成")

            return True

        except Exception as e:
            print(f"❌ 数据库初始化失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


def test_api_functions():
    """测试API功能"""
    print("\n正在测试API功能...")

    app = create_app()

    with app.app_context():
        try:
            from app.services import DataMiningService

            # 测试保存对比组
            test_categories = [
                {
                    "name": "电子产品",
                    "path": ["电子产品"],
                    "total_cny": 5000.0,
                    "item_count": 15,
                }
            ]

            group = DataMiningService.save_comparison_group(
                "API测试组", test_categories
            )
            print(f"✅ 保存对比组成功，ID: {group.id}")

            # 测试获取所有对比组
            groups = DataMiningService.get_all_comparison_groups()
            print(f"✅ 获取对比组成功，共 {len(groups)} 个")

            # 测试更新对比组
            updated_group = DataMiningService.update_comparison_group(
                group.id, name="更新后的API测试组"
            )
            print(f"✅ 更新对比组成功，新名称: {updated_group.name}")

            # 测试删除对比组
            success = DataMiningService.delete_comparison_group(group.id)
            if success:
                print("✅ 删除对比组成功")
            else:
                print("❌ 删除对比组失败")

            return True

        except Exception as e:
            print(f"❌ API功能测试失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """主函数"""
    print("🚀 开始数据挖掘功能初始化...")

    # 初始化数据库
    if not init_database():
        print("❌ 数据库初始化失败，退出")
        return False

    # 测试API功能
    if not test_api_functions():
        print("❌ API功能测试失败，退出")
        return False

    print("\n🎉 数据挖掘功能初始化完成！")
    print("现在可以访问 http://127.0.0.1:5000/data-mining 来使用数据挖掘功能")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
