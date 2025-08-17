# app/services.py
import os
import threading
import copy
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, and_
from flask import current_app

from .models import db, Receipt, Item, RecognitionStatus
from .ai_service import AIService
from .file_service import FileService

# 默认用户时区（东九区）
DEFAULT_USER_TIMEZONE = timezone(timedelta(hours=9))


def convert_local_to_utc(local_datetime, user_timezone=DEFAULT_USER_TIMEZONE):
    """
    将用户本地时间转换为UTC时间

    Args:
        local_datetime: 用户本地时间（naive datetime）
        user_timezone: 用户时区，默认为东九区

    Returns:
        UTC时间（naive datetime）
    """
    if local_datetime is None:
        return None

    # 如果已经有时区信息，先转换为UTC
    if local_datetime.tzinfo is not None:
        return local_datetime.astimezone(timezone.utc).replace(tzinfo=None)

    # 将本地时间标记为用户时区
    local_tz_time = local_datetime.replace(tzinfo=user_timezone)

    # 转换为UTC时间（移除时区信息）
    utc_time = local_tz_time.astimezone(timezone.utc).replace(tzinfo=None)

    return utc_time


class ReceiptService:
    """处理小票相关业务逻辑"""

    @staticmethod
    def _process_recognition_task(app, receipt_id):
        with app.app_context():
            receipt = Receipt.query.get(receipt_id)
            if not receipt:
                return

            # 1. 更新状态为正在处理
            receipt.status = RecognitionStatus.PROCESSING
            db.session.commit()

        # 2. 调用AI服务
        ai_service = AIService()
        image_full_path = None
        if receipt.image_filename:
            image_full_path = FileService.get_image_path(receipt.image_filename)

        try:
            ai_data = ai_service.recognize_receipt(
                text_description=receipt.text_description,
                image_path=image_full_path,
            )

            # 3. 根据AI结果更新数据库
            if ai_data:
                ReceiptService.update_receipt_from_ai(receipt, ai_data)
                receipt.status = RecognitionStatus.SUCCESS
            else:
                receipt.status = RecognitionStatus.FAILED

        except Exception as e:
            current_app.logger.error(f"Error processing receipt {receipt_id}: {e}")
            receipt.status = RecognitionStatus.FAILED

        db.session.commit()

    @staticmethod
    def trigger_recognition(receipt_id):
        # 使用后台线程处理，避免阻塞API
        from flask import current_app
        import copy

        # 保存当前的应用配置
        app_config = copy.deepcopy(current_app.config)

        def background_task():
            # 重新创建Flask app实例
            from flask import Flask
            from app.database import db, ma

            # 创建临时app实例
            temp_app = Flask(__name__)
            temp_app.config.update(app_config)

            # 初始化数据库
            db.init_app(temp_app)
            ma.init_app(temp_app)

            with temp_app.app_context():
                ReceiptService._process_recognition_task_internal(receipt_id)

        thread = threading.Thread(target=background_task)
        thread.daemon = True  # 设置为守护线程
        thread.start()

    @staticmethod
    def _process_recognition_task_internal(receipt_id):
        """内部识别任务处理，已在app_context中"""
        receipt = Receipt.query.get(receipt_id)
        if not receipt:
            return

        # 1. 更新状态为正在处理
        receipt.status = RecognitionStatus.PROCESSING
        db.session.commit()

        # 2. 调用AI服务
        ai_service = AIService()
        image_full_path = None
        if receipt.image_filename:
            image_full_path = FileService.get_image_path(receipt.image_filename)

        try:
            ai_data = ai_service.recognize_receipt(
                text_description=receipt.text_description,
                image_path=image_full_path,
            )

            # 3. 根据AI结果更新数据库
            if ai_data:
                ReceiptService.update_receipt_from_ai(receipt, ai_data)
                receipt.status = RecognitionStatus.SUCCESS
            else:
                receipt.status = RecognitionStatus.FAILED

        except Exception as e:
            current_app.logger.error(f"Error processing receipt {receipt_id}: {e}")
            receipt.status = RecognitionStatus.FAILED

        db.session.commit()

    @staticmethod
    def create_receipt(data, image_file=None):
        """创建新的小票记录

        Args:
            data: 小票数据
            image_file: 上传的图片文件

        Returns:
            Receipt: 创建的小票对象
        """
        filename = None
        if image_file:
            # 从配置获取压缩参数
            compress = current_app.config.get("IMAGE_COMPRESSION_ENABLED", True)
            quality = current_app.config.get("IMAGE_COMPRESSION_QUALITY", 80)
            max_width = current_app.config.get("IMAGE_MAX_WIDTH", 1920)
            max_height = current_app.config.get("IMAGE_MAX_HEIGHT", 1080)

            filename = FileService.save_image_with_md5(
                image_file,
                compress=compress,
                quality=quality,
                max_size=(max_width, max_height),
            )
            if not filename:
                raise ValueError("Failed to save image file")

        new_receipt = Receipt(
            name=data.get("name", "未命名小票"),
            text_description=data.get("text_description"),
            notes=data.get("notes"),
            transaction_time=(
                convert_local_to_utc(
                    datetime.fromisoformat(data.get("transaction_time"))
                )
                if data.get("transaction_time")
                else None
            ),
            image_filename=filename,
            store_name=data.get("store_name"),
            store_category=data.get("store_category"),
        )

        db.session.add(new_receipt)
        db.session.commit()

        # 如果需要AI识别，则触发后台任务
        if new_receipt.status == RecognitionStatus.PENDING:
            ReceiptService.trigger_recognition(new_receipt.id)

        return new_receipt

    @staticmethod
    def get_all_receipts(args):
        query = Receipt.query

        # 搜索 - 支持 search 和 q 参数
        search_value = args.get("search") or args.get("q")
        if search_value:
            search_term = f"%{search_value}%"
            query = query.filter(
                or_(
                    Receipt.name.ilike(search_term),
                    Receipt.notes.ilike(search_term),
                    Receipt.text_description.ilike(search_term),
                    Receipt.store_name.ilike(search_term),
                )
            )

        # 状态筛选
        if status_str := args.get("status"):
            try:
                status_enum = RecognitionStatus(status_str)
                query = query.filter(Receipt.status == status_enum)
            except ValueError:
                pass  # 或者返回错误

        # 排序
        sort_by = args.get("sort_by", "created_at")
        order = args.get("order", "desc")
        sort_field = getattr(Receipt, sort_by, Receipt.created_at)

        if order == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # 分页
        page = args.get("page", 1, type=int)
        per_page = args.get("per_page", 20, type=int)
        paginated_query = query.paginate(page=page, per_page=per_page, error_out=False)

        return paginated_query.items, paginated_query

    @staticmethod
    def update_receipt_from_ai(receipt, ai_data):
        # 更新店铺信息
        if store_name := ai_data.get("store_name"):
            receipt.store_name = store_name

        if store_category := ai_data.get("store_category"):
            receipt.store_category = store_category

        # 更新小票名称（使用AI生成的名称）
        if ai_name := ai_data.get("name"):
            receipt.name = ai_name

        # 更新备注信息
        if notes := ai_data.get("notes"):
            receipt.notes = notes

        # 更新交易时间
        if transaction_time_str := ai_data.get("transaction_time"):
            try:
                # 新格式是 "YYYY-MM-DD HH:MM:SS"，需要转换为datetime
                local_time = datetime.strptime(
                    transaction_time_str, "%Y-%m-%d %H:%M:%S"
                )
                # 将AI识别的当地时间转换为UTC存储
                receipt.transaction_time = convert_local_to_utc(local_time)
            except ValueError:
                # 如果格式不匹配，尝试其他格式作为兼容
                try:
                    local_time = datetime.strptime(
                        transaction_time_str, "%Y-%m-%d %H:%M"
                    )
                    receipt.transaction_time = convert_local_to_utc(local_time)
                except ValueError:
                    try:
                        local_time = datetime.fromisoformat(transaction_time_str)
                        receipt.transaction_time = convert_local_to_utc(local_time)
                    except ValueError:
                        pass  # 格式错误，忽略

        # 清空旧商品并添加新商品
        Item.query.filter_by(receipt_id=receipt.id).delete()

        if items := ai_data.get("items"):
            for item_data in items:
                new_item = Item()
                new_item.receipt_id = receipt.id
                new_item.name_ja = item_data.get("name_ja")
                new_item.name_zh = item_data.get("name_zh")
                new_item.price_jpy = item_data.get("price_jpy")
                new_item.price_cny = item_data.get("price_cny")
                new_item.category_1 = item_data.get("category_1")
                new_item.category_2 = item_data.get("category_2")
                new_item.category_3 = item_data.get("category_3")

                # 处理特价信息
                special_info = item_data.get("special_info")
                # 当特价信息不为否时原样设置，否则设为空
                if special_info is None or special_info == "否":
                    new_item.special_info = None
                else:
                    new_item.special_info = special_info
                # 设置是否特价商品：当special_info不为空字符串或null时为1，其他时候为0
                new_item.is_special_offer = bool(
                    special_info is not None
                    and special_info != ""
                    and special_info != "否"
                )

                db.session.add(new_item)
        db.session.commit()


class ItemService:
    @staticmethod
    def create_item(data):
        """创建新的商品项目"""
        new_item = Item()

        # 直接使用AI标准字段名
        ai_fields = [
            "name_ja",
            "name_zh",
            "category_1",
            "category_2",
            "category_3",
            "price_jpy",
            "price_cny",
            "special_info",
            "notes",
            "receipt_id",
        ]

        for field in ai_fields:
            if field in data:
                setattr(new_item, field, data[field])

        # 处理特价商品标志
        if "is_special_offer" in data:
            new_item.is_special_offer = data["is_special_offer"]
        else:
            # 根据special_info自动判断
            special_info = data.get("special_info")
            new_item.is_special_offer = bool(
                special_info is not None and special_info != "" and special_info != "否"
            )

        db.session.add(new_item)

        # 更新对应小票的最后修改时间
        if new_item.receipt_id:
            receipt = Receipt.query.get(new_item.receipt_id)
            if receipt:
                receipt.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        return new_item

    @staticmethod
    def update_item(item_id, data):
        """更新商品项目"""
        item = Item.query.get_or_404(item_id)

        # 更新AI标准字段
        ai_fields = [
            "name_zh",
            "name_ja",
            "price_cny",
            "price_jpy",
            "category_1",
            "category_2",
            "category_3",
            "special_info",
            "notes",
        ]

        for field in ai_fields:
            if field in data:
                setattr(item, field, data[field])

        # 处理特价商品标志
        if "is_special_offer" in data:
            item.is_special_offer = data["is_special_offer"]
        elif "special_info" in data:
            # 如果更新了special_info，重新计算is_special_offer
            special_info = data["special_info"]
            item.is_special_offer = bool(
                special_info is not None and special_info != "" and special_info != "否"
            )

        # 更新对应小票的最后修改时间
        if item.receipt:
            item.receipt.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        return item

    @staticmethod
    def get_all_items(args):
        query = Item.query.join(Receipt)

        # 搜索
        if search := args.get("search"):
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Item.name_ja.ilike(search_term),
                    Item.name_zh.ilike(search_term),
                    Item.notes.ilike(search_term),
                )
            )

        # 特价筛选
        if "is_special_price" in args:
            is_special = args.get("is_special_price", "").lower() == "true"
            if is_special:
                # 筛选特价商品：直接使用is_special_offer字段
                query = query.filter(Item.is_special_offer == True)
            else:
                # 筛选非特价商品：直接使用is_special_offer字段
                query = query.filter(Item.is_special_offer == False)

        # 分类筛选
        if category_filter := args.get("category_filter"):
            category_term = f"%{category_filter}%"
            query = query.filter(
                or_(
                    Item.category_1.ilike(category_term),
                    Item.category_2.ilike(category_term),
                    Item.category_3.ilike(category_term),
                )
            )

        # 排序
        sort_by = args.get("sort_by", "created_at")
        order = args.get("order", "desc")

        # 根据排序字段选择正确的字段
        if sort_by == "created_at":
            sort_field = Receipt.created_at
        elif sort_by == "transaction_time":
            sort_field = Receipt.transaction_time
        elif sort_by == "updated_at":
            sort_field = Receipt.updated_at
        elif sort_by == "price_jpy":
            sort_field = Item.price_jpy
        elif sort_by == "price_cny":
            sort_field = Item.price_cny
        elif sort_by == "name_zh":
            sort_field = Item.name_zh
        else:
            sort_field = Receipt.created_at

        if order == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # 分页
        page = args.get("page", 1, type=int)
        per_page = args.get("per_page", 12, type=int)
        paginated_query = query.paginate(page=page, per_page=per_page, error_out=False)

        return paginated_query.items, paginated_query


class ExportService:
    """导出服务"""

    @staticmethod
    def get_export_records(args):
        """
        获取导出记录，将小票和商品信息组装成扁平化记录

        Args:
            args: 查询参数，包含分页、时间范围等筛选条件

        Returns:
            tuple: (记录列表, 分页信息)
        """
        # 创建联合查询
        query = db.session.query(Receipt, Item).join(
            Item, Receipt.id == Item.receipt_id
        )

        # 时间范围筛选
        if start_date := args.get("start_date"):
            try:
                start_datetime = datetime.fromisoformat(start_date)
                query = query.filter(Receipt.transaction_time >= start_datetime)
            except ValueError:
                pass

        if end_date := args.get("end_date"):
            try:
                end_datetime = datetime.fromisoformat(end_date)
                query = query.filter(Receipt.transaction_time <= end_datetime)
            except ValueError:
                pass

        # 店铺筛选
        if store_name := args.get("store_name"):
            query = query.filter(Receipt.store_name.ilike(f"%{store_name}%"))

        if store_category := args.get("store_category"):
            query = query.filter(Receipt.store_category.ilike(f"%{store_category}%"))

        # 商品分类筛选
        if category := args.get("category"):
            category_term = f"%{category}%"
            query = query.filter(
                or_(
                    Item.category_1.ilike(category_term),
                    Item.category_2.ilike(category_term),
                    Item.category_3.ilike(category_term),
                )
            )

        # 特价商品筛选
        if "is_special_offer" in args:
            is_special = args.get("is_special_offer", "").lower() == "true"
            query = query.filter(Item.is_special_offer == is_special)

        # 状态筛选
        if status_str := args.get("status"):
            try:
                status_enum = RecognitionStatus(status_str)
                query = query.filter(Receipt.status == status_enum)
            except ValueError:
                pass

        # 搜索
        if search := args.get("search"):
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Receipt.name.ilike(search_term),
                    Receipt.store_name.ilike(search_term),
                    Item.name_ja.ilike(search_term),
                    Item.name_zh.ilike(search_term),
                )
            )

        # 排序
        sort_by = args.get("sort_by", "transaction_time")
        order = args.get("order", "desc")

        if sort_by == "transaction_time":
            sort_field = Receipt.transaction_time
        elif sort_by == "created_at":
            sort_field = Receipt.created_at
        elif sort_by == "receipt_name":
            sort_field = Receipt.name
        elif sort_by == "store_name":
            sort_field = Receipt.store_name
        elif sort_by == "price_jpy":
            sort_field = Item.price_jpy
        else:
            sort_field = Receipt.transaction_time

        if order == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # 分页
        page = args.get("page", 1, type=int)
        per_page = args.get("per_page", None, type=int)

        # 如果没有指定每页记录数，则不做限制
        if per_page is None:
            per_page = 999999  # 设置一个很大的数值表示无限制

        # 计算偏移量
        offset = (page - 1) * per_page

        # 获取总记录数
        total = query.count()

        # 应用分页
        results = query.offset(offset).limit(per_page).all()

        # 创建分页信息对象
        class PaginationInfo:
            def __init__(self, page, per_page, total, items):
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.items = items

        pagination = PaginationInfo(page, per_page, total, results)

        # 将查询结果转换为扁平化记录
        export_records = []
        for receipt, item in results:
            record = {
                # 小票信息
                "receipt_id": receipt.id,
                "receipt_name": receipt.name,
                "store_name": receipt.store_name,
                "store_category": receipt.store_category,
                "transaction_time": receipt.transaction_time,
                "receipt_created_at": receipt.created_at,
                "receipt_status": receipt.status.value if receipt.status else None,
                "receipt_notes": receipt.notes,
                # 商品信息
                "item_id": item.id,
                "item_name_ja": item.name_ja,
                "item_name_zh": item.name_zh,
                "price_jpy": item.price_jpy,
                "price_cny": item.price_cny,
                "category_1": item.category_1,
                "category_2": item.category_2,
                "category_3": item.category_3,
                "special_info": item.special_info,
                "is_special_offer": item.is_special_offer,
                "item_notes": item.notes,
            }
            export_records.append(record)

        return export_records, pagination
