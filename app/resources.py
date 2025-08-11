# app/resources.py
from datetime import datetime
from flask import request, jsonify
from flask_restful import Resource, reqparse
from .models import db, Receipt, Item
from .schemas import (
    receipt_schema,
    receipts_schema,
    item_schema,
    items_schema,
    export_records_schema,
)
from .services import ReceiptService, ItemService, ExportService


class ReceiptListResource(Resource):
    def get(self):
        receipts, pagination = ReceiptService.get_all_receipts(request.args)
        response = {
            "data": receipts_schema.dump(receipts),
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_pages": pagination.pages,
                "total_items": pagination.total,
            },
        }
        return response

    def post(self):
        # 使用 request.form 获取文本字段, request.files 获取文件
        data = request.form
        image_file = request.files.get("image")

        # 校验：必须提供图片或文字描述
        if not image_file and not data.get("text_description"):
            return {"message": "创建小票需要提供图片或文字描述"}, 400

        new_receipt = ReceiptService.create_receipt(data, image_file)
        return receipt_schema.dump(new_receipt), 201


class ReceiptResource(Resource):
    def get(self, receipt_id):
        receipt = Receipt.query.get_or_404(receipt_id)
        return receipt_schema.dump(receipt)

    def put(self, receipt_id):
        receipt = Receipt.query.get_or_404(receipt_id)
        data = request.get_json()
        # 更新允许手动修改的字段
        receipt.name = data.get("name", receipt.name)
        receipt.notes = data.get("notes", receipt.notes)
        receipt.text_description = data.get(
            "text_description", receipt.text_description
        )
        receipt.store_name = data.get("store_name", receipt.store_name)
        receipt.store_category = data.get("store_category", receipt.store_category)

        # 处理交易时间
        if transaction_time_str := data.get("transaction_time"):
            try:
                receipt.transaction_time = datetime.fromisoformat(
                    transaction_time_str.replace("T", " ")
                )
            except ValueError:
                # 如果格式错误，保持原值
                pass

        db.session.commit()
        return receipt_schema.dump(receipt)

    def delete(self, receipt_id):
        receipt = Receipt.query.get_or_404(receipt_id)
        db.session.delete(receipt)
        db.session.commit()
        return "", 204


class ReceiptRecognizeResource(Resource):
    def post(self, receipt_id):
        from .models import RecognitionStatus

        receipt = Receipt.query.get_or_404(receipt_id)
        receipt.status = RecognitionStatus.PENDING
        db.session.commit()
        ReceiptService.trigger_recognition(receipt.id)
        return {"message": "已加入重新识别队列"}, 202


class ReceiptItemListResource(Resource):
    def post(self, receipt_id):
        Receipt.query.get_or_404(receipt_id)
        data = request.get_json()
        data["receipt_id"] = receipt_id

        new_item = ItemService.create_item(data)
        return item_schema.dump(new_item), 201


class ItemListResource(Resource):
    def get(self):
        items, pagination = ItemService.get_all_items(request.args)
        response = {
            "data": items_schema.dump(items),
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_pages": pagination.pages,
                "total_items": pagination.total,
            },
        }
        return response


class ItemResource(Resource):
    def get(self, item_id):
        """获取单个商品项目"""
        item = Item.query.get_or_404(item_id)
        return item_schema.dump(item)

    def put(self, item_id):
        data = request.get_json()
        updated_item = ItemService.update_item(item_id, data)
        return item_schema.dump(updated_item)

    def delete(self, item_id):
        item = Item.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        return "", 204


class ExportResource(Resource):
    """导出资源，提供小票和商品组合数据的导出接口"""

    def get(self):
        """
        获取导出数据

        查询参数:
        - page: 页码，默认1
        - per_page: 每页记录数，不指定则导出所有记录
        - start_date: 开始日期 (ISO格式)
        - end_date: 结束日期 (ISO格式)
        - store_name: 店铺名称筛选
        - store_category: 店铺分类筛选
        - category: 商品分类筛选
        - is_special_offer: 是否特价商品 (true/false)
        - status: 小票状态筛选
        - search: 搜索关键词
        - sort_by: 排序字段 (transaction_time/created_at/receipt_name/store_name/price_jpy)
        - order: 排序方向 (asc/desc)
        """

        # 参数验证
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", None, type=int)

        # 如果没有指定每页记录数，则不做限制（获取所有记录）
        if per_page is None:
            per_page = 999999  # 设置一个很大的数值表示无限制

        try:
            export_records, pagination = ExportService.get_export_records(request.args)

            response = {
                "data": export_records_schema.dump(export_records),
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total_pages": pagination.pages,
                    "total_items": pagination.total,
                },
                "export_info": {
                    "export_time": datetime.utcnow().isoformat(),
                    "total_records": len(export_records),
                    "has_more": pagination.page < pagination.pages,
                },
            }

            return response

        except Exception as e:
            return {"message": f"导出失败: {str(e)}"}, 500
