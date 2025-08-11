"""
数据迁移脚本：从旧系统迁移数据到新系统
"""

import sqlite3
import os
import shutil
from datetime import datetime
from app import create_app
from app.database import db
from app.models import Receipt, Item, RecognitionStatus

# 全局变量保存ID映射关系
id_mapping = {}


def migrate_data():
    """执行数据迁移"""
    app = create_app()

    with app.app_context():
        print("开始数据迁移...")

        # 连接原有数据库
        old_db_path = "data/receipt_manager.sqlite"
        if not os.path.exists(old_db_path):
            print(f"原有数据库不存在: {old_db_path}")
            return

        old_conn = sqlite3.connect(old_db_path)
        old_cursor = old_conn.cursor()

        try:
            # 迁移小票数据
            migrate_receipts(old_cursor)

            # 迁移商品数据
            migrate_items(old_cursor)

            # 迁移图片文件
            migrate_receipt_images()

            print("数据迁移完成!")

        except Exception as e:
            print(f"迁移过程中出错: {e}")
            db.session.rollback()
        finally:
            old_conn.close()


def migrate_receipts(old_cursor):
    """迁移小票数据"""
    global id_mapping
    print("正在迁移小票数据...")

    # 查询原有小票数据
    old_cursor.execute(
        """
        SELECT id, shop_name, shop_category, transaction_time, upload_time, 
               notes, img_md5, receipt_name
        FROM receipts
        ORDER BY id
    """
    )

    old_receipts = old_cursor.fetchall()
    migrated_count = 0

    for old_receipt in old_receipts:
        (
            old_id,
            shop_name,
            shop_category,
            transaction_time,
            upload_time,
            notes,
            img_md5,
            receipt_name,
        ) = old_receipt

        # 检查是否已存在（根据图片文件名）
        image_filename = find_image_by_md5(img_md5)
        existing = Receipt.query.filter_by(image_filename=image_filename).first()
        if existing:
            print(f"小票已存在，跳过: {receipt_name}")
            continue

        # 创建新小票记录
        new_receipt = Receipt(
            name=receipt_name or "未命名小票",
            image_filename=image_filename,
            store_name=shop_name,
            store_category=shop_category,
            transaction_time=(
                datetime.fromisoformat(transaction_time) if transaction_time else None
            ),
            notes=notes,
        )

        # 手动设置创建时间和状态
        if upload_time:
            new_receipt.created_at = datetime.fromisoformat(upload_time)
        new_receipt.status = RecognitionStatus.SUCCESS  # 原有数据认为是已识别成功的

        db.session.add(new_receipt)
        db.session.flush()  # 获取新ID

        # 保存旧ID和新ID的映射关系
        id_mapping[old_id] = new_receipt.id

        migrated_count += 1
        if migrated_count % 50 == 0:
            print(f"已迁移 {migrated_count} 条小票数据...")

    db.session.commit()
    print(f"小票数据迁移完成，共迁移 {migrated_count} 条记录")


def migrate_items(old_cursor):
    """迁移商品数据"""
    global id_mapping
    print("正在迁移商品数据...")

    # 查询原有商品数据
    old_cursor.execute(
        """
        SELECT id, receipt_id, japanese_name, chinese_name, category_1, category_2, 
               category_3, jpy_price, cny_price, is_special, user_rating, user_comment
        FROM receipt_items
        ORDER BY id
    """
    )

    old_items = old_cursor.fetchall()
    migrated_count = 0
    skipped_count = 0

    for old_item in old_items:
        (
            old_id,
            old_receipt_id,
            japanese_name,
            chinese_name,
            category_1,
            category_2,
            category_3,
            jpy_price,
            cny_price,
            is_special,
            user_rating,
            user_comment,
        ) = old_item

        # 查找对应的新小票ID
        new_receipt_id = id_mapping.get(old_receipt_id)
        if not new_receipt_id:
            print(f"未找到对应的小票ID: {old_receipt_id}，跳过商品 {japanese_name}")
            skipped_count += 1
            continue

        # 处理特价信息
        special_info = None
        is_special_offer = bool(is_special)
        if is_special:
            special_info = "是"

        # 组合用户评论和评分
        item_notes = ""
        if user_rating:
            item_notes += f"评分: {user_rating}/5"
        if user_comment:
            if item_notes:
                item_notes += " | "
            item_notes += f"评论: {user_comment}"

        # 创建新商品记录
        new_item = Item()
        new_item.receipt_id = new_receipt_id
        new_item.name_ja = japanese_name
        new_item.name_zh = chinese_name
        new_item.price_jpy = jpy_price
        new_item.price_cny = cny_price
        new_item.special_info = special_info
        new_item.is_special_offer = is_special_offer
        new_item.category_1 = category_1
        new_item.category_2 = category_2
        new_item.category_3 = category_3
        new_item.notes = item_notes if item_notes else None

        db.session.add(new_item)
        migrated_count += 1

        if migrated_count % 100 == 0:
            print(f"已迁移 {migrated_count} 条商品数据...")

    db.session.commit()
    print(
        f"商品数据迁移完成，共迁移 {migrated_count} 条记录，跳过 {skipped_count} 条记录"
    )


def find_image_by_md5(img_md5):
    """根据MD5查找对应的图片文件名"""
    receipts_dir = "data/receipts"
    if not os.path.exists(receipts_dir):
        return None

    # 尝试不同的文件扩展名
    for ext in [".jpeg", ".jpg", ".png"]:
        filename = f"{img_md5}{ext}"
        if os.path.exists(os.path.join(receipts_dir, filename)):
            return filename

    return None


def migrate_receipt_images():
    """迁移小票图片文件"""
    print("正在迁移小票图片...")

    old_receipts_dir = "data/receipts"
    new_receipts_dir = "uploads"

    if not os.path.exists(old_receipts_dir):
        print(f"原图片目录不存在: {old_receipts_dir}")
        return

    # 确保新目录存在
    os.makedirs(new_receipts_dir, exist_ok=True)

    # 复制所有图片文件
    files = os.listdir(old_receipts_dir)
    copied_count = 0

    for filename in files:
        old_file_path = os.path.join(old_receipts_dir, filename)
        new_file_path = os.path.join(new_receipts_dir, filename)

        if os.path.isfile(old_file_path):
            if not os.path.exists(new_file_path):
                shutil.copy2(old_file_path, new_file_path)
                copied_count += 1
            else:
                print(f"文件已存在，跳过: {filename}")

    print(f"图片迁移完成，共复制 {copied_count} 个文件")


def check_migration_results():
    """检查迁移结果"""
    app = create_app()
    with app.app_context():
        receipt_count = Receipt.query.count()
        item_count = Item.query.count()

        print(f"\n迁移结果统计:")
        print(f"小票数量: {receipt_count}")
        print(f"商品数量: {item_count}")

        # 显示一些示例数据
        print(f"\n示例小票数据:")
        sample_receipts = Receipt.query.limit(3).all()
        for receipt in sample_receipts:
            print(f"  {receipt.id}: {receipt.name} - {receipt.store_name}")

        print(f"\n示例商品数据:")
        sample_items = Item.query.limit(3).all()
        for item in sample_items:
            print(f"  {item.id}: {item.name_ja} - ¥{item.price_jpy}")


if __name__ == "__main__":
    # 执行迁移
    migrate_data()

    # 检查结果
    check_migration_results()
