# app/services.py
import os
import threading
import copy
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, and_
from flask import current_app

from .models import db, Receipt, Item, RecognitionStatus, ComparisonGroup, DurableGood
from .category_models import Category
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

    @staticmethod
    def batch_create_and_recognize(image_files, task_name=None):
        """
        批量上传图片并创建识别任务
        Args:
            image_files: 多个图片文件对象列表
            task_name: 可选任务名称
        Returns:
            dict: 包含每个小票的ID、名称、状态
        """
        results = []
        for idx, image_file in enumerate(image_files):
            data = {
                "name": f"批量小票_{task_name or ''}_{idx+1}",
                "text_description": None,
                "notes": None,
                "transaction_time": None,
                "store_name": None,
                "store_category": None,
            }
            try:
                receipt = ReceiptService.create_receipt(data, image_file)
                results.append(
                    {
                        "id": receipt.id,
                        "name": receipt.name,
                        "status": receipt.status.name,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "id": None,
                        "name": data["name"],
                        "status": "FAILED",
                        "error": str(e),
                    }
                )
        return {"receipts": results, "task_name": task_name}

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
        page = int(args.get("page", 1))
        per_page = int(args.get("per_page", 20))
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
                new_item.category_id = item_data.get("category_id")

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
            "category_id",
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
        db.session.flush()  # 获得item.id

        # 处理耐用品信息
        if "is_durable" in data and data["is_durable"]:
            durable_info = DurableGood()
            durable_info.item_id = new_item.id

            # 设置耐用品的开始和结束日期
            if "durable_start_date" in data and data["durable_start_date"]:
                durable_info.start_date = datetime.strptime(
                    data["durable_start_date"], "%Y-%m-%d"
                ).date()
            if "durable_end_date" in data and data["durable_end_date"]:
                durable_info.end_date = datetime.strptime(
                    data["durable_end_date"], "%Y-%m-%d"
                ).date()

            db.session.add(durable_info)

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
            "category_id",
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

        # 处理耐用品信息
        if "is_durable" in data:
            is_durable = data["is_durable"]
            if is_durable:
                # 创建或更新耐用品信息
                if not item.durable_info:
                    item.durable_info = DurableGood()
                    item.durable_info.item_id = item.id

                # 更新耐用品的开始和结束日期
                if "durable_start_date" in data and data["durable_start_date"]:
                    item.durable_info.start_date = datetime.strptime(
                        data["durable_start_date"], "%Y-%m-%d"
                    ).date()
                if "durable_end_date" in data and data["durable_end_date"]:
                    item.durable_info.end_date = datetime.strptime(
                        data["durable_end_date"], "%Y-%m-%d"
                    ).date()
            else:
                # 删除耐用品信息
                if item.durable_info:
                    db.session.delete(item.durable_info)
                    item.durable_info = None

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
        is_special_offer = args.get("is_special_offer")
        if is_special_offer and is_special_offer.strip():  # 只有当参数不为空时才筛选
            is_special = is_special_offer.lower() == "true"
            if is_special:
                # 筛选特价商品：直接使用is_special_offer字段
                query = query.filter(Item.is_special_offer == True)
            else:
                # 筛选非特价商品：直接使用is_special_offer字段
                query = query.filter(Item.is_special_offer == False)

        # 耐用品筛选
        is_durable = args.get("is_durable")
        if is_durable and is_durable.strip():  # 只有当参数不为空时才筛选
            is_durable_flag = is_durable.lower() == "true"
            if is_durable_flag:
                # 筛选耐用品：有 durable_info 关联记录
                query = query.join(DurableGood, Item.id == DurableGood.item_id)
            else:
                # 筛选非耐用品：没有 durable_info 关联记录
                query = query.outerjoin(
                    DurableGood, Item.id == DurableGood.item_id
                ).filter(DurableGood.id == None)

        # 分类筛选 - 支持搜索三级分类中的任意一级
        if category_filter := args.get("category_filter"):
            category_term = f"%{category_filter}%"

            # 查找所有匹配的分类（任意级别）
            matching_categories = Category.query.filter(
                Category.name.ilike(category_term)
            ).all()

            if matching_categories:
                # 收集所有相关的分类ID（包括匹配分类及其所有后代）
                category_ids = set()

                for category in matching_categories:
                    # 添加匹配的分类本身
                    category_ids.add(category.id)

                    # 添加所有后代分类
                    descendants = category.get_descendants()
                    for desc in descendants:
                        category_ids.add(desc.id)

                # 筛选属于这些分类的商品
                query = query.filter(Item.category_id.in_(list(category_ids)))

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
        page = int(args.get("page", 1))
        per_page = int(args.get("per_page", 12))
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

        # 商品分类筛选 - 支持搜索三级分类中的任意一级
        if category := args.get("category"):
            category_term = f"%{category}%"

            # 查找所有匹配的分类（任意级别）
            matching_categories = Category.query.filter(
                Category.name.ilike(category_term)
            ).all()

            if matching_categories:
                # 收集所有相关的分类ID（包括匹配分类及其所有后代）
                category_ids = set()

                for category_obj in matching_categories:
                    # 添加匹配的分类本身
                    category_ids.add(category_obj.id)

                    # 添加所有后代分类
                    descendants = category_obj.get_descendants()
                    for desc in descendants:
                        category_ids.add(desc.id)

                # 筛选属于这些分类的商品
                query = query.filter(Item.category_id.in_(list(category_ids)))

        # 特价商品筛选
        is_special_offer = args.get("is_special_offer")
        if is_special_offer and is_special_offer.strip():  # 只有当参数不为空时才筛选
            is_special = is_special_offer.lower() == "true"
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
        page = int(args.get("page", 1))
        per_page = args.get("per_page")
        if per_page is not None:
            per_page = int(per_page)

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
            # 获取分类路径
            category_path = ""
            category_id = None
            if item.category:
                category_path = " > ".join(item.category.get_full_path_list())
                category_id = item.category.id

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
                "category_id": category_id,
                "category_path": category_path,
                "special_info": item.special_info,
                "is_special_offer": item.is_special_offer,
                "item_notes": item.notes,
            }
            export_records.append(record)

        return export_records, pagination


class AnalyticsService:
    """数据分析服务"""

    @staticmethod
    def get_dashboard_overview(args):
        """
        获取消费总览仪表盘数据

        Returns:
            dict: 包含总支出、小票数量、商品数量、使用天数、日均开销、折扣商品占比
        """
        from sqlalchemy import func
        from datetime import datetime, timedelta

        # 基础查询条件
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        use_amortization = args.get("durable_amortization") == "true"

        # 确保日期参数是字符串类型
        if start_date is not None and not isinstance(start_date, str):
            start_date = str(start_date)
        if end_date is not None and not isinstance(end_date, str):
            end_date = str(end_date)

        receipt_query = Receipt.query.filter(
            Receipt.status == RecognitionStatus.SUCCESS
        )
        item_query = (
            db.session.query(Item)
            .join(Receipt)
            .filter(Receipt.status == RecognitionStatus.SUCCESS)
        )

        if start_date and isinstance(start_date, str):
            try:
                start_datetime = datetime.fromisoformat(start_date)
                receipt_query = receipt_query.filter(
                    Receipt.transaction_time >= start_datetime
                )
                item_query = item_query.filter(
                    Receipt.transaction_time >= start_datetime
                )
            except (ValueError, TypeError):
                pass

        if end_date and isinstance(end_date, str):
            try:
                end_datetime = datetime.fromisoformat(end_date)
                receipt_query = receipt_query.filter(
                    Receipt.transaction_time <= end_datetime
                )
                item_query = item_query.filter(Receipt.transaction_time <= end_datetime)
            except (ValueError, TypeError):
                pass

        # 总支出（日元和人民币）
        if use_amortization:
            # 使用均摊模式，需要获取所有商品数据进行计算
            items_query = (
                db.session.query(Item)
                .join(Receipt)
                .filter(Receipt.status == RecognitionStatus.SUCCESS)
            )
            
            if start_date and isinstance(start_date, str):
                try:
                    start_datetime = datetime.fromisoformat(start_date)
                    items_query = items_query.filter(Receipt.transaction_time >= start_datetime)
                except (ValueError, TypeError):
                    pass
                    
            if end_date and isinstance(end_date, str):
                try:
                    end_datetime = datetime.fromisoformat(end_date)
                    items_query = items_query.filter(Receipt.transaction_time <= end_datetime)
                except (ValueError, TypeError):
                    pass
                    
            items = items_query.all()
            amortized_spending = AnalyticsService._get_amortized_spending_for_date_range(
                items, start_date, end_date, use_amortization
            )
            total_jpy = amortized_spending['jpy']
            total_cny = amortized_spending['cny']
        else:
            # 传统模式，直接查询价格总和
            total_spending_jpy = (
                db.session.query(func.sum(Item.price_jpy))
                .join(Receipt)
                .filter(Receipt.status == RecognitionStatus.SUCCESS)
            )
            total_spending_cny = (
                db.session.query(func.sum(Item.price_cny))
                .join(Receipt)
                .filter(Receipt.status == RecognitionStatus.SUCCESS)
            )

            if start_date and isinstance(start_date, str):
                try:
                    start_datetime = datetime.fromisoformat(start_date)
                    total_spending_jpy = total_spending_jpy.filter(
                        Receipt.transaction_time >= start_datetime
                    )
                    total_spending_cny = total_spending_cny.filter(
                        Receipt.transaction_time >= start_datetime
                    )
                except (ValueError, TypeError):
                    pass

            if end_date and isinstance(end_date, str):
                try:
                    end_datetime = datetime.fromisoformat(end_date)
                    total_spending_jpy = total_spending_jpy.filter(
                        Receipt.transaction_time <= end_datetime
                    )
                    total_spending_cny = total_spending_cny.filter(
                        Receipt.transaction_time <= end_datetime
                    )
                except (ValueError, TypeError):
                    pass

            total_jpy = total_spending_jpy.scalar() or 0
            total_cny = total_spending_cny.scalar() or 0

        # 小票数量
        receipt_count = receipt_query.count()

        # 商品数量
        item_count = item_query.count()

        # 时间跨度（根据交易时间计算最早和最晚的交易时间差）
        # 如果指定了时间范围（开始或结束日期任一），计算该范围内的交易时间跨度
        # 如果没有指定任何时间范围，使用所有数据的范围
        if start_date or end_date:
            # 有指定时间范围，计算该范围内的交易时间跨度
            date_range = db.session.query(
                func.min(Receipt.transaction_time), func.max(Receipt.transaction_time)
            ).filter(Receipt.status == RecognitionStatus.SUCCESS)

            if start_date and isinstance(start_date, str):
                try:
                    start_datetime = datetime.fromisoformat(start_date)
                    date_range = date_range.filter(
                        Receipt.transaction_time >= start_datetime
                    )
                except (ValueError, TypeError):
                    pass

            if end_date and isinstance(end_date, str):
                try:
                    end_datetime = datetime.fromisoformat(end_date)
                    date_range = date_range.filter(
                        Receipt.transaction_time <= end_datetime
                    )
                except (ValueError, TypeError):
                    pass

            result = date_range.first()
            min_date, max_date = result if result else (None, None)
        else:
            # 没有指定任何时间范围，使用所有数据的范围
            result = (
                db.session.query(
                    func.min(Receipt.transaction_time),
                    func.max(Receipt.transaction_time),
                )
                .filter(Receipt.status == RecognitionStatus.SUCCESS)
                .first()
            )
            min_date, max_date = result if result else (None, None)

        time_span = 0
        if min_date and max_date:
            # 计算实际的天数差异
            time_span = (max_date.date() - min_date.date()).days + 1

        # 日均开销
        daily_avg_jpy = total_jpy / time_span if time_span > 0 else 0
        daily_avg_cny = total_cny / time_span if time_span > 0 else 0

        # 折扣商品占比
        special_item_count = item_query.filter(Item.is_special_offer == True).count()
        discount_ratio = (
            (special_item_count / item_count * 100) if item_count > 0 else 0
        )

        return {
            "total_spending": {
                "jpy": round(total_jpy, 2) if total_jpy else 0,
                "cny": round(total_cny, 2) if total_cny else 0,
            },
            "receipt_count": receipt_count,
            "item_count": item_count,
            "time_span": time_span,
            "daily_average": {
                "jpy": round(daily_avg_jpy, 2) if daily_avg_jpy else 0,
                "cny": round(daily_avg_cny, 2) if daily_avg_cny else 0,
            },
            "discount_ratio": round(discount_ratio, 2),
        }

    @staticmethod
    def get_spending_trend(args):
        """
        获取消费趋势数据

        Returns:
            dict: 包含每日消费数据和对应的商品列表
        """
        from sqlalchemy import func
        from datetime import datetime, date

        start_date = args.get("start_date")
        end_date = args.get("end_date")
        use_amortization = args.get("durable_amortization") == "true"

        # 确保日期参数是字符串类型
        if start_date is not None and not isinstance(start_date, str):
            start_date = str(start_date)
        if end_date is not None and not isinstance(end_date, str):
            end_date = str(end_date)

        # 构建查询 - 获取所有相关的商品数据
        query = (
            db.session.query(Receipt, Item)
            .join(Item)
            .filter(
                Receipt.status == RecognitionStatus.SUCCESS,
                Receipt.transaction_time.isnot(None),  # 排除空值
            )
        )

        if start_date and isinstance(start_date, str):
            try:
                start_datetime = datetime.fromisoformat(start_date)
                query = query.filter(Receipt.transaction_time >= start_datetime)
            except (ValueError, TypeError):
                pass

        if end_date and isinstance(end_date, str):
            try:
                end_datetime = datetime.fromisoformat(end_date)
                query = query.filter(Receipt.transaction_time <= end_datetime)
            except (ValueError, TypeError):
                pass

        # 商品分类筛选
        # 商品分类筛选 - 支持搜索三级分类中的任意一级
        if category := args.get("category"):
            category_term = f"%{category}%"

            # 查找所有匹配的分类（任意级别）
            matching_categories = Category.query.filter(
                Category.name.ilike(category_term)
            ).all()

            if matching_categories:
                # 收集所有相关的分类ID（包括匹配分类及其所有后代）
                category_ids = set()

                for category_obj in matching_categories:
                    # 添加匹配的分类本身
                    category_ids.add(category_obj.id)

                    # 添加所有后代分类
                    descendants = category_obj.get_descendants()
                    for desc in descendants:
                        category_ids.add(desc.id)

                # 筛选属于这些分类的商品
                query = query.filter(Item.category_id.in_(list(category_ids)))

        # 店铺筛选
        if store_name := args.get("store_name"):
            query = query.filter(Receipt.store_name.ilike(f"%{store_name}%"))

        if store_category := args.get("store_category"):
            query = query.filter(Receipt.store_category.ilike(f"%{store_category}%"))

        # 特价商品筛选
        is_special_offer = args.get("is_special_offer")
        if is_special_offer and is_special_offer.strip():  # 只有当参数不为空时才筛选
            is_special = is_special_offer.lower() == "true"
            query = query.filter(Item.is_special_offer == is_special)

        # 获取所有数据
        results = query.all()

        # 在Python中进行日期分组
        daily_data = {}
        
        if use_amortization:
            # 均摊模式：需要考虑耐用品的分摊
            # 首先按日期分组收集商品
            items_by_date = {}
            for receipt, item in results:
                if receipt.transaction_time:
                    date_key = receipt.transaction_time.date()
                    if date_key not in items_by_date:
                        items_by_date[date_key] = []
                    items_by_date[date_key].append(item)
            
            # 为每个日期计算均摊成本
            for date_key, items in items_by_date.items():
                total_jpy = 0
                total_cny = 0
                
                for item in items:
                    amortized_jpy, amortized_cny = AnalyticsService._calculate_amortized_cost(item, date_key)
                    # 确保返回值不为None
                    total_jpy += amortized_jpy or 0
                    total_cny += amortized_cny or 0
                
                daily_data[date_key] = {
                    "total_jpy": total_jpy,
                    "total_cny": total_cny,
                    "item_count": len(items),
                }
        else:
            # 传统模式：直接使用原始价格
            for receipt, item in results:
                if receipt.transaction_time:
                    date_key = receipt.transaction_time.date()
                    if date_key not in daily_data:
                        daily_data[date_key] = {
                            "total_jpy": 0,
                            "total_cny": 0,
                            "item_count": 0,
                        }

                    daily_data[date_key]["total_jpy"] += item.price_jpy or 0
                    daily_data[date_key]["total_cny"] += item.price_cny or 0
                    daily_data[date_key]["item_count"] += 1

        # 转换为前端需要的格式
        trend_data = []
        for date_key in sorted(daily_data.keys()):
            data = daily_data[date_key]
            trend_data.append(
                {
                    "date": date_key.isoformat(),
                    "spending": {
                        "jpy": round(data["total_jpy"], 2),
                        "cny": round(data["total_cny"], 2),
                    },
                    "item_count": data["item_count"],
                }
            )

        return trend_data

    @staticmethod
    def get_daily_items(date, args=None):
        """
        获取指定日期的商品列表

        Args:
            date: 日期字符串 (YYYY-MM-DD)
            args: 额外的查询参数

        Returns:
            list: 当日商品列表
        """
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return []

        use_amortization = args and args.get("durable_amortization") == "true"

        if use_amortization:
            # 在均摊模式下，需要考虑所有耐用品（不仅仅是当日购买的）
            # 获取所有可能在当日产生均摊成本的耐用品
            durable_items = []
            
            # 1. 获取当日购买的所有商品（包括耐用品和常规商品）
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            daily_query = (
                db.session.query(Item)
                .join(Receipt)
                .filter(
                    Receipt.status == RecognitionStatus.SUCCESS,
                    Receipt.transaction_time.is_not(None),
                    Receipt.transaction_time >= start_datetime,
                    Receipt.transaction_time <= end_datetime,
                )
            )
            
            daily_items = daily_query.all()
            
            # 2. 获取所有在当日有均摊成本的耐用品（不限购买日期）
            all_durable_query = (
                db.session.query(Item)
                .join(Receipt)
                .join(DurableGood, Item.id == DurableGood.item_id)
                .filter(
                    Receipt.status == RecognitionStatus.SUCCESS,
                    DurableGood.start_date <= target_date,
                    DurableGood.end_date >= target_date,
                )
            )
            
            all_durable_items = all_durable_query.all()
            
            # 合并并去重商品列表
            item_ids = set()
            combined_items = []
            
            # 添加当日购买的商品
            for item in daily_items:
                if item.id not in item_ids:
                    combined_items.append(item)
                    item_ids.add(item.id)
            
            # 添加有均摊成本的耐用品
            for item in all_durable_items:
                if item.id not in item_ids:
                    combined_items.append(item)
                    item_ids.add(item.id)
                    
            items = combined_items
        else:
            # 常规模式下，只查询当日购买的商品
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())

            query = (
                db.session.query(Item)
                .join(Receipt)
                .filter(
                    Receipt.status == RecognitionStatus.SUCCESS,
                    Receipt.transaction_time.is_not(None),
                    Receipt.transaction_time >= start_datetime,
                    Receipt.transaction_time <= end_datetime,
                )
            )

            items = query.all()

        # 转换为字典格式
        items_data = []
        for item in items:
            # 计算显示价格（根据是否使用均摊模式）
            is_amortized = False
            daily_cost_jpy = None
            daily_cost_cny = None
            amortization_info = None
            
            if use_amortization and item.durable_info:
                # 耐用品在均摊模式下的处理
                durable_info = item.durable_info
                if (durable_info.start_date and durable_info.end_date and 
                    durable_info.start_date <= target_date <= durable_info.end_date):
                    
                    # 在均摊期间内
                    total_days = (durable_info.end_date - durable_info.start_date).days + 1
                    daily_cost_jpy = (item.price_jpy or 0) / total_days
                    daily_cost_cny = (item.price_cny or 0) / total_days
                    
                    display_jpy, display_cny = daily_cost_jpy, daily_cost_cny
                    is_amortized = True
                    
                    amortization_info = {
                        "total_days": total_days,
                        "start_date": durable_info.start_date.isoformat(),
                        "end_date": durable_info.end_date.isoformat(),
                        "daily_cost_jpy": round(daily_cost_jpy, 2),
                        "daily_cost_cny": round(daily_cost_cny, 2),
                    }
                else:
                    # 不在均摊期间内，成本为0
                    display_jpy, display_cny = 0, 0
                    is_amortized = True
            else:
                # 常规商品或非均摊模式
                display_jpy, display_cny = item.price_jpy or 0, item.price_cny or 0
                
            # 获取分类层级信息
            category_info = {}
            if item.category:
                ancestors = item.category.get_ancestors()
                category_info = {
                    "category_1": ancestors[0].name if len(ancestors) > 0 else None,
                    "category_2": ancestors[1].name if len(ancestors) > 1 else None,
                    "category_3": item.category.name,
                    "category_id": item.category.id,
                }
            else:
                category_info = {
                    "category_1": None,
                    "category_2": None,
                    "category_3": None,
                    "category_id": None,
                }

            item_data = {
                "id": item.id,
                "receipt_id": item.receipt_id,
                "name_ja": item.name_ja,
                "name_zh": item.name_zh,
                "price_jpy": display_jpy or 0,
                "price_cny": display_cny or 0,
                "original_price_jpy": item.price_jpy or 0,  # 保留原始价格用于参考
                "original_price_cny": item.price_cny or 0,
                "is_amortized": is_amortized,  # 标记是否为均摊价格
                "is_durable": bool(item.durable_info),  # 标记是否为耐用品
                **category_info,
                "special_info": item.special_info,
                "is_special_offer": item.is_special_offer,
                "notes": item.notes,
                "receipt_name": item.receipt.name if item.receipt else None,
                "store_name": item.receipt.store_name if item.receipt else None,
                "transaction_time": (
                    item.receipt.transaction_time.isoformat()
                    if item.receipt and item.receipt.transaction_time
                    else None
                ),
            }
            
            # 添加均摊信息（如果有的话）
            if amortization_info:
                item_data["amortization_info"] = amortization_info
                
            items_data.append(item_data)

        # 按价格从大到小排序
        items_data.sort(key=lambda x: x["price_jpy"] or 0, reverse=True)

        return items_data

    @staticmethod
    def get_category_analysis(args):
        """
        获取分类支出分析数据

        Returns:
            dict: 包含分类统计和层级结构
        """
        from sqlalchemy import func

        start_date = args.get("start_date")
        end_date = args.get("end_date")
        category_level = args.get("category_level", "1")  # 默认显示一级分类
        parent_category = args.get("parent_category")  # 父级分类名称

        # 确保日期参数是字符串类型
        if start_date is not None and not isinstance(start_date, str):
            start_date = str(start_date)
        if end_date is not None and not isinstance(end_date, str):
            end_date = str(end_date)

        # 基础查询
        query = (
            db.session.query(Item)
            .join(Receipt)
            .filter(Receipt.status == RecognitionStatus.SUCCESS)
        )

        # 日期筛选
        if start_date and isinstance(start_date, str):
            try:
                start_datetime = datetime.fromisoformat(start_date)
                query = query.filter(Receipt.transaction_time >= start_datetime)
            except (ValueError, TypeError):
                pass

        if end_date and isinstance(end_date, str):
            try:
                end_datetime = datetime.fromisoformat(end_date)
                query = query.filter(Receipt.transaction_time <= end_datetime)
            except (ValueError, TypeError):
                pass

        # 根据层级和父分类进行筛选
        if category_level == "1":
            # 一级分类统计
            level1_categories = Category.query.filter_by(level=1).all()
            category_stats = []

            for cat in level1_categories:
                # 获取该一级分类下的所有商品（包括子分类）
                descendant_ids = [cat.id]
                for child in cat.children:
                    descendant_ids.append(child.id)
                    for grandchild in child.children:
                        descendant_ids.append(grandchild.id)

                cat_query = query.filter(Item.category_id.in_(descendant_ids))
                total_jpy = (
                    cat_query.with_entities(func.sum(Item.price_jpy)).scalar() or 0
                )
                total_cny = (
                    cat_query.with_entities(func.sum(Item.price_cny)).scalar() or 0
                )
                item_count = cat_query.count()

                if item_count > 0:  # 只包含有商品的分类
                    category_stats.append(
                        {
                            "category": cat.name,
                            "total_jpy": total_jpy,
                            "total_cny": total_cny,
                            "item_count": item_count,
                        }
                    )

        elif category_level == "2" and parent_category:
            # 二级分类统计
            parent_cat = Category.query.filter_by(name=parent_category, level=1).first()
            if parent_cat:
                level2_categories = Category.query.filter_by(
                    parent_id=parent_cat.id, level=2
                ).all()
                category_stats = []

                for cat in level2_categories:
                    # 获取该二级分类下的所有商品（包括子分类）
                    descendant_ids = [cat.id]
                    for child in cat.children:
                        descendant_ids.append(child.id)

                    cat_query = query.filter(Item.category_id.in_(descendant_ids))
                    total_jpy = (
                        cat_query.with_entities(func.sum(Item.price_jpy)).scalar() or 0
                    )
                    total_cny = (
                        cat_query.with_entities(func.sum(Item.price_cny)).scalar() or 0
                    )
                    item_count = cat_query.count()

                    if item_count > 0:
                        category_stats.append(
                            {
                                "category": cat.name,
                                "total_jpy": total_jpy,
                                "total_cny": total_cny,
                                "item_count": item_count,
                            }
                        )
            else:
                category_stats = []

        elif category_level == "3" and parent_category:
            # 三级分类统计
            parent_cat = Category.query.filter_by(name=parent_category, level=2).first()
            if parent_cat:
                level3_categories = Category.query.filter_by(
                    parent_id=parent_cat.id, level=3
                ).all()
                category_stats = []

                for cat in level3_categories:
                    cat_query = query.filter(Item.category_id == cat.id)
                    total_jpy = (
                        cat_query.with_entities(func.sum(Item.price_jpy)).scalar() or 0
                    )
                    total_cny = (
                        cat_query.with_entities(func.sum(Item.price_cny)).scalar() or 0
                    )
                    item_count = cat_query.count()

                    if item_count > 0:
                        category_stats.append(
                            {
                                "category": cat.name,
                                "total_jpy": total_jpy,
                                "total_cny": total_cny,
                                "item_count": item_count,
                            }
                        )
            else:
                category_stats = []
        else:
            category_stats = []

        # 转换为前端需要的格式
        categories = []
        total_jpy = sum(row["total_jpy"] for row in category_stats)
        total_cny = sum(row["total_cny"] for row in category_stats)

        for row in category_stats:
            category_total_jpy = row["total_jpy"]
            category_total_cny = row["total_cny"]

            categories.append(
                {
                    "category": row["category"],
                    "spending": {
                        "jpy": round(category_total_jpy, 2),
                        "cny": round(category_total_cny, 2),
                    },
                    "item_count": row["item_count"],
                    "percentage": (
                        round(category_total_jpy / total_jpy * 100, 2)
                        if total_jpy > 0
                        else 0
                    ),
                }
            )

        # 按金额排序
        categories.sort(key=lambda x: x["spending"]["jpy"], reverse=True)

        return {
            "categories": categories,
            "total_spending": {"jpy": round(total_jpy, 2), "cny": round(total_cny, 2)},
            "category_level": category_level,
            "parent_category": parent_category,
        }

    @staticmethod
    def get_category_items(category, category_level="1", args=None):
        """
        获取指定分类的商品列表

        Args:
            category: 分类名称
            category_level: 分类层级 (1, 2, 3)
            args: 额外的查询参数

        Returns:
            list: 分类商品列表
        """
        start_date = args.get("start_date") if args else None
        end_date = args.get("end_date") if args else None

        # 确保日期参数是字符串类型
        if start_date is not None and not isinstance(start_date, str):
            start_date = str(start_date)
        if end_date is not None and not isinstance(end_date, str):
            end_date = str(end_date)

        # 构建查询
        query = (
            db.session.query(Item)
            .join(Receipt)
            .filter(Receipt.status == RecognitionStatus.SUCCESS)
        )

        if start_date and isinstance(start_date, str):
            try:
                start_datetime = datetime.fromisoformat(start_date)
                query = query.filter(Receipt.transaction_time >= start_datetime)
            except (ValueError, TypeError):
                pass

        if end_date and isinstance(end_date, str):
            try:
                end_datetime = datetime.fromisoformat(end_date)
                query = query.filter(Receipt.transaction_time <= end_datetime)
            except (ValueError, TypeError):
                pass

        # 根据分类层级筛选
        if category_level == "1":
            # 查找一级分类
            cat = Category.query.filter_by(name=category, level=1).first()
            if cat:
                # 获取该一级分类下的所有商品（包括子分类）
                descendant_ids = [cat.id]
                for child in cat.children:
                    descendant_ids.append(child.id)
                    for grandchild in child.children:
                        descendant_ids.append(grandchild.id)
                query = query.filter(Item.category_id.in_(descendant_ids))
            else:
                return []  # 分类不存在
        elif category_level == "2":
            # 查找二级分类
            cat = Category.query.filter_by(name=category, level=2).first()
            if cat:
                # 获取该二级分类下的所有商品（包括子分类）
                descendant_ids = [cat.id]
                for child in cat.children:
                    descendant_ids.append(child.id)
                query = query.filter(Item.category_id.in_(descendant_ids))
            else:
                return []
        elif category_level == "3":
            # 查找三级分类
            cat = Category.query.filter_by(name=category, level=3).first()
            if cat:
                query = query.filter(Item.category_id == cat.id)
            else:
                return []

        items = query.all()

        # 转换为字典格式
        items_data = []
        for item in items:
            # 获取分类层级信息
            category_info = {}
            if item.category:
                ancestors = item.category.get_ancestors()
                category_info = {
                    "category_1": ancestors[0].name if len(ancestors) > 0 else None,
                    "category_2": ancestors[1].name if len(ancestors) > 1 else None,
                    "category_3": item.category.name,
                    "category_id": item.category.id,
                }
            else:
                category_info = {
                    "category_1": None,
                    "category_2": None,
                    "category_3": None,
                    "category_id": None,
                }

            items_data.append(
                {
                    "id": item.id,
                    "receipt_id": item.receipt_id,
                    "name_ja": item.name_ja,
                    "name_zh": item.name_zh,
                    "price_jpy": item.price_jpy,
                    "price_cny": item.price_cny,
                    **category_info,
                    "special_info": item.special_info,
                    "is_special_offer": item.is_special_offer,
                    "notes": item.notes,
                    "receipt_name": item.receipt.name if item.receipt else None,
                    "store_name": item.receipt.store_name if item.receipt else None,
                    "transaction_time": (
                        item.receipt.transaction_time.isoformat()
                        if item.receipt and item.receipt.transaction_time
                        else None
                    ),
                }
            )

        # 按价格从大到小排序
        items_data.sort(key=lambda x: x["price_jpy"] or 0, reverse=True)

        return items_data

    @staticmethod
    def _calculate_amortized_cost(item, target_date):
        """
        计算耐用品在指定日期的均摊成本
        
        Args:
            item: 商品对象
            target_date: 目标日期
            
        Returns:
            tuple: (均摊后的日元价格, 均摊后的人民币价格)
        """
        # 如果不是耐用品，返回原价格（确保不为None）
        if not item.durable_info:
            return item.price_jpy or 0, item.price_cny or 0
            
        durable_info = item.durable_info
        
        # 如果没有设置时间范围，返回原价格（确保不为None）
        if not durable_info.start_date or not durable_info.end_date:
            return item.price_jpy or 0, item.price_cny or 0
            
        # 计算总使用天数
        total_days = (durable_info.end_date - durable_info.start_date).days + 1
        if total_days <= 0:
            return item.price_jpy or 0, item.price_cny or 0
            
        # 检查目标日期是否在使用期间内
        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            elif isinstance(target_date, datetime):
                target_date = target_date.date()
        except (ValueError, TypeError):
            # 日期解析失败，返回原价格
            return item.price_jpy or 0, item.price_cny or 0
            
        if target_date < durable_info.start_date or target_date > durable_info.end_date:
            # 不在使用期间内，成本为0
            return 0, 0
            
        # 计算每日均摊成本
        daily_jpy = (item.price_jpy or 0) / total_days
        daily_cny = (item.price_cny or 0) / total_days
        
        return daily_jpy, daily_cny

    @staticmethod
    def _get_amortized_spending_for_date_range(items, start_date, end_date, use_amortization=False):
        """
        计算指定日期范围内的均摊支出
        
        Args:
            items: 商品列表
            start_date: 开始日期
            end_date: 结束日期
            use_amortization: 是否使用均摊模式
            
        Returns:
            dict: {'jpy': 总日元支出, 'cny': 总人民币支出}
        """
        if not use_amortization:
            # 不使用均摊模式，直接返回原始价格总和
            total_jpy = sum(item.price_jpy or 0 for item in items)
            total_cny = sum(item.price_cny or 0 for item in items)
            return {'jpy': total_jpy, 'cny': total_cny}
            
        # 使用均摊模式
        total_jpy = 0
        total_cny = 0
        
        # 解析日期 - 如果没有提供日期范围，则不进行均摊计算
        if not start_date or not end_date:
            # 没有日期范围，返回原始价格总和
            total_jpy = sum(item.price_jpy or 0 for item in items)
            total_cny = sum(item.price_cny or 0 for item in items)
            return {'jpy': total_jpy, 'cny': total_cny}
            
        # 转换日期格式
        try:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            elif isinstance(start_date, datetime):
                start_date = start_date.date()
                
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            elif isinstance(end_date, datetime):
                end_date = end_date.date()
        except (ValueError, TypeError):
            # 日期解析失败，返回原始价格总和
            total_jpy = sum(item.price_jpy or 0 for item in items)
            total_cny = sum(item.price_cny or 0 for item in items)
            return {'jpy': total_jpy, 'cny': total_cny}
            
        for item in items:
            if not item.durable_info:
                # 非耐用品，直接计入成本
                total_jpy += item.price_jpy or 0
                total_cny += item.price_cny or 0
            else:
                # 耐用品，计算期间内的均摊成本
                durable_info = item.durable_info
                
                if not durable_info.start_date or not durable_info.end_date:
                    # 没有设置时间范围，按原价计算
                    total_jpy += item.price_jpy or 0
                    total_cny += item.price_cny or 0
                    continue
                    
                # 计算重叠期间
                overlap_start = max(start_date, durable_info.start_date)
                overlap_end = min(end_date, durable_info.end_date)
                
                if overlap_start <= overlap_end:
                    # 有重叠期间
                    overlap_days = (overlap_end - overlap_start).days + 1
                    total_use_days = (durable_info.end_date - durable_info.start_date).days + 1
                    
                    if total_use_days > 0:
                        # 计算重叠期间的均摊成本
                        daily_jpy = (item.price_jpy or 0) / total_use_days
                        daily_cny = (item.price_cny or 0) / total_use_days
                        
                        total_jpy += daily_jpy * overlap_days
                        total_cny += daily_cny * overlap_days
                        
        return {'jpy': total_jpy, 'cny': total_cny}


class DataMiningService:
    """数据挖掘服务"""

    @staticmethod
    def get_category_tree(args):
        """
        获取分类树结构数据

        Returns:
            dict: 包含层级分类结构
        """
        from sqlalchemy import func

        start_date = args.get("start_date")
        end_date = args.get("end_date")

        # 确保日期参数是字符串类型
        if start_date is not None and not isinstance(start_date, str):
            start_date = str(start_date)
        if end_date is not None and not isinstance(end_date, str):
            end_date = str(end_date)

        # 基础查询
        query = (
            db.session.query(Item)
            .join(Receipt)
            .filter(Receipt.status == RecognitionStatus.SUCCESS)
        )

        if start_date and isinstance(start_date, str):
            try:
                start_datetime = datetime.fromisoformat(start_date)
                query = query.filter(Receipt.transaction_time >= start_datetime)
            except (ValueError, TypeError):
                pass

        if end_date and isinstance(end_date, str):
            try:
                end_datetime = datetime.fromisoformat(end_date)
                query = query.filter(Receipt.transaction_time <= end_datetime)
            except (ValueError, TypeError):
                pass

        # 获取所有分类数据
        items = query.all()

        # 构建分类树
        category_tree = {}

        for item in items:
            if not item.category:
                # 如果没有分类，归入"未分类"
                cat1 = cat2 = cat3 = "未分类"
                path = ["未分类"]
            else:
                ancestors = item.category.get_ancestors()
                cat1 = ancestors[0].name if len(ancestors) > 0 else "未分类"
                cat2 = ancestors[1].name if len(ancestors) > 1 else "未分类"
                cat3 = item.category.name
                path = [cat1, cat2, cat3]

            if cat1 not in category_tree:
                category_tree[cat1] = {
                    "name": cat1,
                    "level": 1,
                    "path": [cat1],
                    "total_cny": 0,
                    "item_count": 0,
                    "children": {},
                }

            if cat2 not in category_tree[cat1]["children"]:
                category_tree[cat1]["children"][cat2] = {
                    "name": cat2,
                    "level": 2,
                    "path": [cat1, cat2],
                    "total_cny": 0,
                    "item_count": 0,
                    "children": {},
                }

            if cat3 not in category_tree[cat1]["children"][cat2]["children"]:
                category_tree[cat1]["children"][cat2]["children"][cat3] = {
                    "name": cat3,
                    "level": 3,
                    "path": [cat1, cat2, cat3],
                    "total_cny": 0,
                    "item_count": 0,
                    "children": {},
                }

            # 累加金额和数量
            price_cny = item.price_cny or 0
            category_tree[cat1]["total_cny"] += price_cny
            category_tree[cat1]["item_count"] += 1
            category_tree[cat1]["children"][cat2]["total_cny"] += price_cny
            category_tree[cat1]["children"][cat2]["item_count"] += 1
            category_tree[cat1]["children"][cat2]["children"][cat3][
                "total_cny"
            ] += price_cny
            category_tree[cat1]["children"][cat2]["children"][cat3]["item_count"] += 1

        # 转换为列表格式
        def convert_to_list(tree_dict):
            result = []
            for key, value in tree_dict.items():
                node = {
                    "name": value["name"],
                    "level": value["level"],
                    "path": value["path"],
                    "total_cny": round(value["total_cny"], 2),
                    "item_count": value["item_count"],
                    "id": "_".join(value["path"]),  # 生成唯一ID
                    "children": (
                        convert_to_list(value["children"]) if value["children"] else []
                    ),
                }
                result.append(node)

            # 按金额排序
            result.sort(key=lambda x: x["total_cny"], reverse=True)
            return result

        return convert_to_list(category_tree)

    @staticmethod
    def get_categories_comparison_data(category_selections, args):
        """
        获取多个分类选择的对比数据

        Args:
            category_selections: 分类选择列表，每个元素包含名称和路径列表
            args: 查询参数

        Returns:
            dict: 包含时间序列对比数据
        """
        from sqlalchemy import func
        from datetime import datetime

        start_date = args.get("start_date")
        end_date = args.get("end_date")

        # 确保日期参数是字符串类型
        if start_date is not None and not isinstance(start_date, str):
            start_date = str(start_date)
        if end_date is not None and not isinstance(end_date, str):
            end_date = str(end_date)

        comparison_data = []

        for selection in category_selections:
            selection_name = selection.get("name", "未命名选择")
            categories = selection.get("categories", [])

            if not categories:
                continue

            # 构建查询
            query = (
                db.session.query(Receipt, Item)
                .join(Item)
                .filter(
                    Receipt.status == RecognitionStatus.SUCCESS,
                    Receipt.transaction_time.isnot(None),
                )
            )

            if start_date and isinstance(start_date, str):
                try:
                    start_datetime = datetime.fromisoformat(start_date)
                    query = query.filter(Receipt.transaction_time >= start_datetime)
                except (ValueError, TypeError):
                    pass

            if end_date and isinstance(end_date, str):
                try:
                    end_datetime = datetime.fromisoformat(end_date)
                    query = query.filter(Receipt.transaction_time <= end_datetime)
                except (ValueError, TypeError):
                    pass

            # 构建分类筛选条件
            category_filters = []
            for category in categories:
                path = category.get("path", [])
                if len(path) == 1:
                    # 一级分类
                    cat = Category.query.filter_by(name=path[0], level=1).first()
                    if cat:
                        # 获取该一级分类下的所有商品（包括子分类）
                        descendant_ids = [cat.id]
                        for child in cat.children:
                            descendant_ids.append(child.id)
                            for grandchild in child.children:
                                descendant_ids.append(grandchild.id)
                        category_filters.append(Item.category_id.in_(descendant_ids))
                elif len(path) == 2:
                    # 二级分类
                    level1_cat = Category.query.filter_by(name=path[0], level=1).first()
                    if level1_cat:
                        level2_cat = Category.query.filter_by(
                            name=path[1], level=2, parent_id=level1_cat.id
                        ).first()
                        if level2_cat:
                            # 获取该二级分类下的所有商品（包括子分类）
                            descendant_ids = [level2_cat.id]
                            for child in level2_cat.children:
                                descendant_ids.append(child.id)
                            category_filters.append(
                                Item.category_id.in_(descendant_ids)
                            )
                elif len(path) == 3:
                    # 三级分类
                    level1_cat = Category.query.filter_by(name=path[0], level=1).first()
                    if level1_cat:
                        level2_cat = Category.query.filter_by(
                            name=path[1], level=2, parent_id=level1_cat.id
                        ).first()
                        if level2_cat:
                            level3_cat = Category.query.filter_by(
                                name=path[2], level=3, parent_id=level2_cat.id
                            ).first()
                            if level3_cat:
                                category_filters.append(
                                    Item.category_id == level3_cat.id
                                )

            if category_filters:
                query = query.filter(or_(*category_filters))

            # 获取数据并按日期分组
            results = query.all()
            daily_data = {}

            for receipt, item in results:
                if receipt.transaction_time:
                    date_key = receipt.transaction_time.date()
                    if date_key not in daily_data:
                        daily_data[date_key] = {
                            "total_cny": 0,
                            "item_count": 0,
                            "items": [],
                        }

                    daily_data[date_key]["total_cny"] += item.price_cny or 0
                    daily_data[date_key]["item_count"] += 1
                    daily_data[date_key]["items"].append(
                        {
                            "id": item.id,
                            "receipt_id": item.receipt_id,
                            "name_ja": item.name_ja,
                            "name_zh": item.name_zh,
                            "price_cny": item.price_cny,
                            "category_1": item.category_1,
                            "category_2": item.category_2,
                            "category_3": item.category_3,
                            "special_info": item.special_info,
                            "is_special_offer": item.is_special_offer,
                            "receipt_name": receipt.name,
                            "store_name": receipt.store_name,
                        }
                    )

            # 转换为时间序列数据
            time_series = []
            for date_key in sorted(daily_data.keys()):
                data = daily_data[date_key]
                time_series.append(
                    {
                        "date": date_key.isoformat(),
                        "total_cny": round(data["total_cny"], 2),
                        "item_count": data["item_count"],
                        "items": sorted(
                            data["items"],
                            key=lambda x: x["price_cny"] or 0,
                            reverse=True,
                        ),
                    }
                )

            comparison_data.append(
                {
                    "name": selection_name,
                    "categories": categories,
                    "time_series": time_series,
                    "total_amount": sum(point["total_cny"] for point in time_series),
                    "total_items": sum(point["item_count"] for point in time_series),
                }
            )

        return comparison_data

    @staticmethod
    def save_comparison_group(name, categories):
        """
        保存对比组

        Args:
            name: 对比组名称
            categories: 分类列表

        Returns:
            dict: 保存的对比组信息
        """
        import json

        # 验证输入
        if not name or not name.strip():
            raise ValueError("对比组名称不能为空")

        if not categories:
            raise ValueError("至少需要选择一个分类")

        # 创建新的对比组
        comparison_group = ComparisonGroup(
            name=name.strip(),
            categories_data=json.dumps(categories, ensure_ascii=False),
        )

        db.session.add(comparison_group)
        db.session.commit()

        return {
            "id": comparison_group.id,
            "name": comparison_group.name,
            "categories": categories,
            "created_at": comparison_group.created_at.isoformat(),
            "updated_at": comparison_group.updated_at.isoformat(),
        }

    @staticmethod
    def get_all_comparison_groups():
        """
        获取所有保存的对比组

        Returns:
            list: 对比组列表
        """
        import json

        groups = ComparisonGroup.query.order_by(ComparisonGroup.updated_at.desc()).all()

        result = []
        for group in groups:
            try:
                categories = json.loads(group.categories_data)
                result.append(
                    {
                        "id": group.id,
                        "name": group.name,
                        "categories": categories,
                        "created_at": group.created_at.isoformat(),
                        "updated_at": group.updated_at.isoformat(),
                    }
                )
            except (json.JSONDecodeError, TypeError):
                # 数据损坏的对比组跳过，但记录错误
                current_app.logger.warning(f"对比组 {group.id} 的数据格式错误")
                continue

        return result

    @staticmethod
    def update_comparison_group(group_id, **kwargs):
        """
        更新对比组

        Args:
            group_id: 对比组ID
            **kwargs: 要更新的字段

        Returns:
            dict: 更新后的对比组信息
        """
        import json

        group = ComparisonGroup.query.get_or_404(group_id)

        # 更新名称
        if "name" in kwargs:
            name = kwargs["name"]
            if not name or not name.strip():
                raise ValueError("对比组名称不能为空")
            group.name = name.strip()

        # 更新分类
        if "categories" in kwargs:
            categories = kwargs["categories"]
            if not categories:
                raise ValueError("至少需要选择一个分类")
            group.categories_data = json.dumps(categories, ensure_ascii=False)

        db.session.commit()

        # 返回更新后的数据
        categories = json.loads(group.categories_data)
        return {
            "id": group.id,
            "name": group.name,
            "categories": categories,
            "created_at": group.created_at.isoformat(),
            "updated_at": group.updated_at.isoformat(),
        }

    @staticmethod
    def delete_comparison_group(group_id):
        """
        删除对比组

        Args:
            group_id: 对比组ID

        Returns:
            bool: 是否删除成功
        """
        group = ComparisonGroup.query.get(group_id)
        if not group:
            return False

        db.session.delete(group)
        db.session.commit()
        return True
