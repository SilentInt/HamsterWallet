#!/usr/bin/env python3
"""
分类数据迁移脚本
从原有数据库中的items表的三级分类字段迁移到新的统一分类表
"""

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
from config import Config
from app import create_app
from app.category_models import Category
from app.database import db


def get_unique_categories():
    """从items表中提取所有唯一的三级分类组合"""
    db_path = Config.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")

    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return {}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 获取所有不为空的分类组合
        cursor.execute(
            """
            SELECT DISTINCT category_1, category_2, category_3 
            FROM items 
            WHERE category_1 IS NOT NULL 
            AND category_1 != ''
            ORDER BY category_1, category_2, category_3
        """
        )

        categories = cursor.fetchall()

        # 组织分类层级结构
        category_tree = defaultdict(lambda: defaultdict(set))

        for cat1, cat2, cat3 in categories:
            if cat1:
                if cat2:
                    category_tree[cat1][cat2].add(cat3 if cat3 else None)
                else:
                    category_tree[cat1][None].add(None)

        return category_tree

    finally:
        conn.close()


def migrate_categories():
    """迁移分类数据到新的统一分类表"""

    # 创建Flask应用上下文
    app = create_app()

    with app.app_context():
        try:
            # 获取原有分类数据
            category_tree = get_unique_categories()

            if not category_tree:
                print("没有找到需要迁移的分类数据")
                return

            print("=== 开始分类数据迁移 ===")

            # 检查是否已经存在categories表
            try:
                existing_categories = Category.query.count()
                if existing_categories > 0:
                    print(f"警告: categories表中已存在 {existing_categories} 条记录")
                    response = input("是否要清空现有数据并重新迁移? (y/N): ")
                    if response.lower() != "y":
                        print("迁移已取消")
                        return

                    # 清空现有数据
                    db.session.query(Category).delete()
                    db.session.commit()
                    print("已清空现有分类数据")

            except Exception as e:
                print(f"检查现有数据时出错: {e}")
                # 如果表不存在，创建表
                db.create_all()
                print("已创建categories表")

            migrated_count = 0

            # 迁移一级分类
            level1_map = {}
            for cat1_name in category_tree.keys():
                if cat1_name:
                    category = Category(name=cat1_name, level=1)
                    db.session.add(category)
                    db.session.flush()  # 获取ID
                    level1_map[cat1_name] = category.id
                    migrated_count += 1
                    print(f"创建一级分类: {cat1_name} (ID: {category.id})")

            # 迁移二级分类
            level2_map = {}
            for cat1_name, cat2_dict in category_tree.items():
                if cat1_name and cat1_name in level1_map:
                    for cat2_name in cat2_dict.keys():
                        if cat2_name:
                            category = Category(
                                name=cat2_name, level=2, parent_id=level1_map[cat1_name]
                            )
                            db.session.add(category)
                            db.session.flush()  # 获取ID
                            level2_map[f"{cat1_name}_{cat2_name}"] = category.id
                            migrated_count += 1
                            print(
                                f"创建二级分类: {cat1_name} -> {cat2_name} (ID: {category.id})"
                            )

            # 迁移三级分类
            for cat1_name, cat2_dict in category_tree.items():
                if cat1_name and cat1_name in level1_map:
                    for cat2_name, cat3_set in cat2_dict.items():
                        if cat2_name and f"{cat1_name}_{cat2_name}" in level2_map:
                            for cat3_name in cat3_set:
                                if cat3_name:
                                    category = Category(
                                        name=cat3_name,
                                        level=3,
                                        parent_id=level2_map[
                                            f"{cat1_name}_{cat2_name}"
                                        ],
                                    )
                                    db.session.add(category)
                                    db.session.flush()  # 获取ID
                                    migrated_count += 1
                                    print(
                                        f"创建三级分类: {cat1_name} -> {cat2_name} -> {cat3_name} (ID: {category.id})"
                                    )

            # 提交所有更改
            db.session.commit()

            print(f"\n=== 迁移完成 ===")
            print(f"总共迁移了 {migrated_count} 个分类")

            # 验证迁移结果
            level1_count = Category.query.filter_by(level=1).count()
            level2_count = Category.query.filter_by(level=2).count()
            level3_count = Category.query.filter_by(level=3).count()

            print(f"一级分类: {level1_count} 个")
            print(f"二级分类: {level2_count} 个")
            print(f"三级分类: {level3_count} 个")
            print(f"总计: {level1_count + level2_count + level3_count} 个")

        except Exception as e:
            db.session.rollback()
            print(f"迁移过程中发生错误: {e}")
            import traceback

            traceback.print_exc()


def print_category_preview():
    """预览要迁移的分类数据"""
    category_tree = get_unique_categories()

    if not category_tree:
        print("没有找到分类数据")
        return

    print("=== 分类数据预览 ===")
    total_categories = 0

    for cat1_name, cat2_dict in category_tree.items():
        if cat1_name:
            total_categories += 1
            print(f"1. {cat1_name}")

            for cat2_name, cat3_set in cat2_dict.items():
                if cat2_name:
                    total_categories += 1
                    print(f"  2. {cat2_name}")

                    for cat3_name in cat3_set:
                        if cat3_name:
                            total_categories += 1
                            print(f"    3. {cat3_name}")

    print(f"\n总共将迁移 {total_categories} 个分类")


if __name__ == "__main__":
    print("分类数据迁移工具")
    print("1. 预览分类数据")
    print("2. 执行迁移")

    choice = input("请选择操作 (1/2): ")

    if choice == "1":
        print_category_preview()
    elif choice == "2":
        migrate_categories()
    else:
        print("无效的选择")
