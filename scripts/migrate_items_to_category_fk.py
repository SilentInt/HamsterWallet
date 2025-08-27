#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：将商品表的三级分类字段迁移为外键引用
将 category_1, category_2, category_3 字段替换为 category_id 外键
"""

import sqlite3
import sys
from typing import Dict, Optional


def get_category_id_by_path(
    cursor, category_1: str, category_2: str, category_3: str
) -> Optional[int]:
    """根据三级分类路径查找对应的分类ID"""
    try:
        # 先查找一级分类
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND level = 1", (category_1,)
        )
        level1_result = cursor.fetchone()
        if not level1_result:
            return None
        level1_id = level1_result[0]

        # 查找二级分类
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND level = 2 AND parent_id = ?",
            (category_2, level1_id),
        )
        level2_result = cursor.fetchone()
        if not level2_result:
            return None
        level2_id = level2_result[0]

        # 查找三级分类
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND level = 3 AND parent_id = ?",
            (category_3, level2_id),
        )
        level3_result = cursor.fetchone()
        if not level3_result:
            return None

        return level3_result[0]
    except Exception as e:
        print(f"查找分类ID时出错: {e}")
        return None


def migrate_items_to_category_fk(db_path: str):
    """执行商品表分类字段迁移"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 首先检查当前表结构
        cursor.execute("PRAGMA table_info(items)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"当前items表列: {columns}")

        # 检查是否已经有category_id字段
        if "category_id" in columns:
            print("category_id字段已存在，检查是否需要迁移数据...")
        else:
            # 添加新的category_id字段
            print("添加category_id字段...")
            cursor.execute(
                "ALTER TABLE items ADD COLUMN category_id INTEGER REFERENCES categories(id)"
            )

        # 获取所有需要迁移的商品数据
        cursor.execute(
            """
            SELECT id, category_1, category_2, category_3, category_id 
            FROM items 
            WHERE category_1 IS NOT NULL AND category_2 IS NOT NULL AND category_3 IS NOT NULL
        """
        )
        items_to_migrate = cursor.fetchall()

        print(f"找到 {len(items_to_migrate)} 个商品需要迁移分类")

        migrated_count = 0
        failed_items = []

        for item_id, cat1, cat2, cat3, current_category_id in items_to_migrate:
            # 如果已经有category_id，跳过
            if current_category_id is not None:
                continue

            # 查找对应的分类ID
            category_id = get_category_id_by_path(cursor, cat1, cat2, cat3)

            if category_id:
                # 更新商品的category_id
                cursor.execute(
                    "UPDATE items SET category_id = ? WHERE id = ?",
                    (category_id, item_id),
                )
                migrated_count += 1
                if migrated_count % 10 == 0:
                    print(f"已迁移 {migrated_count} 个商品...")
            else:
                failed_items.append(
                    {
                        "id": item_id,
                        "category_1": cat1,
                        "category_2": cat2,
                        "category_3": cat3,
                    }
                )

        # 提交更改
        conn.commit()

        print(f"\n迁移完成:")
        print(f"  成功迁移: {migrated_count} 个商品")
        print(f"  失败数量: {len(failed_items)} 个商品")

        if failed_items:
            print("\n失败的商品分类:")
            for item in failed_items[:10]:  # 只显示前10个
                print(
                    f"  商品ID {item['id']}: {item['category_1']} -> {item['category_2']} -> {item['category_3']}"
                )
            if len(failed_items) > 10:
                print(f"  ... 还有 {len(failed_items) - 10} 个")

        # 验证迁移结果
        cursor.execute("SELECT COUNT(*) FROM items WHERE category_id IS NOT NULL")
        migrated_total = cursor.fetchone()[0]
        print(f"\n验证: 共有 {migrated_total} 个商品设置了category_id")

        # 可选：删除旧的分类字段（谨慎操作）
        response = input(
            "\n是否删除旧的分类字段 (category_1, category_2, category_3)? (y/N): "
        )
        if response.lower() == "y":
            print("创建备份表...")
            cursor.execute("CREATE TABLE items_backup AS SELECT * FROM items")

            print("重建items表...")
            cursor.execute(
                """
                CREATE TABLE items_new (
                    id INTEGER PRIMARY KEY,
                    receipt_id INTEGER NOT NULL REFERENCES receipts(id),
                    name_ja VARCHAR(100),
                    name_zh VARCHAR(100),
                    price_jpy FLOAT,
                    price_cny FLOAT,
                    special_info VARCHAR(50),
                    is_special_offer BOOLEAN NOT NULL DEFAULT 0,
                    category_id INTEGER REFERENCES categories(id),
                    notes VARCHAR
                )
            """
            )

            cursor.execute(
                """
                INSERT INTO items_new (id, receipt_id, name_ja, name_zh, price_jpy, price_cny, 
                                     special_info, is_special_offer, category_id, notes)
                SELECT id, receipt_id, name_ja, name_zh, price_jpy, price_cny, 
                       special_info, is_special_offer, category_id, notes
                FROM items
            """
            )

            cursor.execute("DROP TABLE items")
            cursor.execute("ALTER TABLE items_new RENAME TO items")

            conn.commit()
            print("旧字段删除完成，备份表为 items_backup")

    except Exception as e:
        print(f"迁移过程中出错: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    return True


def main():
    """主函数"""
    db_path = "hamster.db"

    print("开始迁移商品表分类字段...")
    success = migrate_items_to_category_fk(db_path)

    if success:
        print("迁移完成！")
    else:
        print("迁移失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
