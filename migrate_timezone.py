#!/usr/bin/env python3
"""
时区数据迁移脚本
将现有数据库中的交易时间从东九区时间转换为UTC时间

主要改进：
1. 新增 migrate_transaction_times_safe() 函数，使用原始SQL更新，避免触发 updated_at 的自动更新
2. 修改原有函数，使用批量SQL更新而非ORM更新，提高性能并避免副作用
3. 提供两种迁移模式选择：安全模式（推荐）和普通模式
"""

from datetime import datetime, timezone, timedelta
from app import create_app
from app.models import Receipt, db
from sqlalchemy import text

# 东九区时区（UTC+9）
JST = timezone(timedelta(hours=9))


def parse_datetime_string(date_str, receipt_id=None):
    """解析日期时间字符串为 datetime 对象"""
    if not isinstance(date_str, str):
        return date_str

    # 尝试解析不同的日期时间格式
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # 如果所有格式都失败了
    raise ValueError(f"无法解析时间格式: {date_str} (收据 {receipt_id})")


def migrate_transaction_times_safe():
    """安全迁移交易时间，不触发updated_at更新"""
    app = create_app()

    with app.app_context():
        print("开始安全迁移交易时间数据...")

        # 使用原始SQL查询需要迁移的记录
        result = db.session.execute(
            text(
                """
                SELECT id, transaction_time, updated_at 
                FROM receipts 
                WHERE transaction_time IS NOT NULL
            """
            )
        )

        records = result.fetchall()
        print(f"找到 {len(records)} 个有交易时间的收据需要迁移")

        migrated_count = 0

        for record in records:
            receipt_id = None
            try:
                receipt_id = record[0]
                original_time = record[1]
                original_updated_at = record[2]

                # 如果 original_time 是字符串，需要先转换为 datetime 对象
                try:
                    original_time = parse_datetime_string(original_time, receipt_id)
                except ValueError as e:
                    print(f"跳过收据 {receipt_id}: {e}")
                    continue

                # 假设现有的交易时间是东九区时间但没有时区信息
                if (
                    hasattr(original_time, "tzinfo")
                    and original_time.tzinfo is not None
                ):
                    continue

                # 将原始时间标记为东九区时间
                jst_time = original_time.replace(tzinfo=JST)

                # 转换为UTC时间
                utc_time = jst_time.astimezone(timezone.utc).replace(tzinfo=None)

                print(f"收据 {receipt_id}: {original_time} (JST) -> {utc_time} (UTC)")

                # 使用原始SQL更新，同时保持updated_at不变
                db.session.execute(
                    text(
                        """
                        UPDATE receipts 
                        SET transaction_time = :transaction_time,
                            updated_at = :updated_at
                        WHERE id = :id
                    """
                    ),
                    {
                        "transaction_time": utc_time,
                        "updated_at": original_updated_at,  # 保持原有的updated_at值
                        "id": receipt_id,
                    },
                )
                migrated_count += 1

            except Exception as e:
                print(f"迁移收据 {receipt_id or 'unknown'} 时出错: {e}")
                continue

        # 提交更改
        if migrated_count > 0:
            db.session.commit()
            print(f"成功迁移了 {migrated_count} 个交易时间（未触发updated_at更新）")
        else:
            print("没有需要迁移的数据")


def migrate_transaction_times():
    """迁移交易时间从东九区到UTC"""
    app = create_app()

    with app.app_context():
        print("开始迁移交易时间数据...")

        # 查找所有有交易时间的收据
        receipts = Receipt.query.filter(Receipt.transaction_time.isnot(None)).all()

        print(f"找到 {len(receipts)} 个有交易时间的收据需要迁移")

        migrated_count = 0
        batch_updates = []

        for receipt in receipts:
            try:
                # 假设现有的交易时间是东九区时间但没有时区信息
                original_time = receipt.transaction_time

                # 如果 original_time 是字符串，需要先转换为 datetime 对象
                try:
                    original_time = parse_datetime_string(original_time, receipt.id)
                except ValueError as e:
                    print(f"跳过收据 {receipt.id}: {e}")
                    continue

                # 如果时间已经有时区信息，跳过
                if (
                    hasattr(original_time, "tzinfo")
                    and original_time.tzinfo is not None
                ):
                    continue

                # 将原始时间标记为东九区时间
                jst_time = original_time.replace(tzinfo=JST)

                # 转换为UTC时间
                utc_time = jst_time.astimezone(timezone.utc).replace(tzinfo=None)

                print(f"收据 {receipt.id}: {original_time} (JST) -> {utc_time} (UTC)")

                # 添加到批量更新列表
                batch_updates.append({"id": receipt.id, "transaction_time": utc_time})
                migrated_count += 1

            except Exception as e:
                print(f"迁移收据 {receipt.id} 时出错: {e}")
                continue

        # 使用原始SQL批量更新，避免触发updated_at自动更新
        if batch_updates:
            for update in batch_updates:
                db.session.execute(
                    text(
                        "UPDATE receipts SET transaction_time = :transaction_time WHERE id = :id"
                    ),
                    {
                        "transaction_time": update["transaction_time"],
                        "id": update["id"],
                    },
                )
            db.session.commit()
            print(f"成功迁移了 {migrated_count} 个交易时间")
        else:
            print("没有需要迁移的数据")


def migrate_other_timestamps():
    """迁移其他时间戳字段"""
    app = create_app()

    with app.app_context():
        print("开始迁移其他时间戳...")

        # 查找所有收据
        receipts = Receipt.query.all()

        migrated_count = 0
        batch_updates = []

        for receipt in receipts:
            try:
                update_data = {"id": receipt.id}
                needs_update = False

                # 迁移 created_at
                if receipt.created_at:
                    try:
                        created_at = parse_datetime_string(
                            receipt.created_at, receipt.id
                        )
                        if (
                            not hasattr(created_at, "tzinfo")
                            or created_at.tzinfo is None
                        ):
                            jst_time = created_at.replace(tzinfo=JST)
                            utc_time = jst_time.astimezone(timezone.utc).replace(
                                tzinfo=None
                            )
                            update_data["created_at"] = utc_time
                            needs_update = True
                    except ValueError as e:
                        print(f"跳过收据 {receipt.id} 的 created_at: {e}")

                # 迁移 updated_at
                if receipt.updated_at:
                    try:
                        updated_at = parse_datetime_string(
                            receipt.updated_at, receipt.id
                        )
                        if (
                            not hasattr(updated_at, "tzinfo")
                            or updated_at.tzinfo is None
                        ):
                            jst_time = updated_at.replace(tzinfo=JST)
                            utc_time = jst_time.astimezone(timezone.utc).replace(
                                tzinfo=None
                            )
                            update_data["updated_at"] = utc_time
                            needs_update = True
                    except ValueError as e:
                        print(f"跳过收据 {receipt.id} 的 updated_at: {e}")

                if needs_update:
                    batch_updates.append(update_data)
                    migrated_count += 1

            except Exception as e:
                print(f"迁移收据 {receipt.id} 的其他时间戳时出错: {e}")
                continue

        # 使用原始SQL批量更新，避免触发自动更新机制
        if batch_updates:
            for update in batch_updates:
                set_clauses = []
                params = {"id": update["id"]}

                if "created_at" in update:
                    set_clauses.append("created_at = :created_at")
                    params["created_at"] = update["created_at"]

                if "updated_at" in update:
                    set_clauses.append("updated_at = :updated_at")
                    params["updated_at"] = update["updated_at"]

                if set_clauses:
                    sql = f"UPDATE receipts SET {', '.join(set_clauses)} WHERE id = :id"
                    db.session.execute(text(sql), params)

            db.session.commit()
            print(f"成功迁移了 {migrated_count} 个收据的其他时间戳")
        else:
            print("没有需要迁移的其他时间戳")


if __name__ == "__main__":
    print("时区数据迁移工具")
    print("=" * 50)
    print("1. 安全迁移（推荐）- 不触发updated_at更新")
    print("2. 普通迁移 - 可能会触发updated_at更新")

    choice = input("请选择迁移方式 (1/2): ")

    if choice not in ["1", "2"]:
        print("无效选择，迁移已取消")
        exit(0)

    response = input("确定要将现有数据从东九区时间迁移到UTC吗？(y/n): ")
    if response.lower() != "y":
        print("迁移已取消")
        exit(0)

    try:
        if choice == "1":
            migrate_transaction_times_safe()
            print("使用安全模式迁移完成！updated_at字段未被修改。")
        else:
            migrate_transaction_times()
            print("使用普通模式迁移完成！")
        # migrate_other_timestamps()
    except Exception as e:
        print(f"迁移失败: {e}")
        exit(1)
