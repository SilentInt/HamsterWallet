# app/resources.py
from datetime import datetime, timezone
from flask import request, jsonify, current_app
from flask_restful import Resource, reqparse
from .models import db, Receipt, Item
from .services import convert_local_to_utc
from .schemas import (
    receipt_schema,
    receipts_schema,
    item_schema,
    items_schema,
    export_records_schema,
)
from .services import (
    ReceiptService,
    ItemService,
    ExportService,
    AnalyticsService,
    DataMiningService,
)


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
                local_time = datetime.fromisoformat(
                    transaction_time_str.replace("T", " ")
                )
                # 将用户输入的当地时间转换为UTC存储
                receipt.transaction_time = convert_local_to_utc(local_time)
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

    def post(self):
        data = request.get_json()
        new_item = ItemService.create_item(data)
        return item_schema.dump(new_item), 201


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

        # 更新对应小票的最后修改时间
        if item.receipt:
            item.receipt.updated_at = datetime.now(timezone.utc)

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
                    "export_time": datetime.now(timezone.utc).isoformat(),
                    "total_records": len(export_records),
                    "has_more": pagination.page < pagination.pages,
                },
            }

            return response

        except Exception as e:
            return {"message": f"导出失败: {str(e)}"}, 500


class AnalyticsDashboardResource(Resource):
    """分析仪表盘资源"""

    def get(self):
        """
        获取消费总览数据

        查询参数:
        - start_date: 开始日期 (ISO格式)
        - end_date: 结束日期 (ISO格式)
        """
        try:
            dashboard_data = AnalyticsService.get_dashboard_overview(request.args)
            return dashboard_data
        except Exception as e:
            return {"message": f"获取仪表盘数据失败: {str(e)}"}, 500


class AnalyticsTrendResource(Resource):
    """消费趋势分析资源"""

    def get(self):
        """
        获取消费趋势数据

        查询参数:
        - start_date: 开始日期 (ISO格式)
        - end_date: 结束日期 (ISO格式)
        """
        try:
            trend_data = AnalyticsService.get_spending_trend(request.args)
            return {"data": trend_data}
        except Exception as e:
            return {"message": f"获取趋势数据失败: {str(e)}"}, 500


class AnalyticsDailyItemsResource(Resource):
    """每日商品列表资源"""

    def get(self, date):
        """
        获取指定日期的商品列表

        路径参数:
        - date: 日期 (YYYY-MM-DD)
        """
        try:
            items_data = AnalyticsService.get_daily_items(date, request.args)
            return {"data": items_data}
        except Exception as e:
            return {"message": f"获取每日商品数据失败: {str(e)}"}, 500


class AnalyticsCategoryResource(Resource):
    """分类分析资源"""

    def get(self):
        """
        获取分类支出分析数据

        查询参数:
        - start_date: 开始日期 (ISO格式)
        - end_date: 结束日期 (ISO格式)
        - category_level: 分类层级 (1, 2, 3)
        - parent_category: 父级分类名称
        """
        try:
            category_data = AnalyticsService.get_category_analysis(request.args)
            return category_data
        except Exception as e:
            return {"message": f"获取分类分析数据失败: {str(e)}"}, 500


class AnalyticsCategoryItemsResource(Resource):
    """分类商品列表资源"""

    def get(self, category):
        """
        获取指定分类的商品列表

        路径参数:
        - category: 分类名称

        查询参数:
        - category_level: 分类层级 (1, 2, 3)
        - start_date: 开始日期 (ISO格式)
        - end_date: 结束日期 (ISO格式)
        """
        try:
            category_level = request.args.get("category_level", "1")
            items_data = AnalyticsService.get_category_items(
                category, category_level, request.args
            )
            return {"data": items_data}
        except Exception as e:
            return {"message": f"获取分类商品数据失败: {str(e)}"}, 500


class DataMiningCategoryTreeResource(Resource):
    """数据挖掘分类树资源"""

    def get(self):
        """
        获取分类树结构数据

        查询参数:
        - start_date: 开始日期 (ISO格式)
        - end_date: 结束日期 (ISO格式)
        """
        try:
            tree_data = DataMiningService.get_category_tree(request.args)
            return {"data": tree_data}
        except Exception as e:
            return {"message": f"获取分类树数据失败: {str(e)}"}, 500


class DataMiningComparisonResource(Resource):
    """数据挖掘对比分析资源"""

    def post(self):
        """
        提交分类选择并获取对比数据

        请求体格式:
        {
            "selections": [
                {
                    "name": "选择名称",
                    "categories": [
                        {
                            "name": "分类名称",
                            "path": ["一级分类", "二级分类", "三级分类"]
                        }
                    ]
                }
            ],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
        """
        try:
            data = request.get_json()
            if not data or "selections" not in data:
                return {"message": "请求数据格式错误"}, 400

            selections = data["selections"]
            args = {
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
            }

            comparison_data = DataMiningService.get_categories_comparison_data(
                selections, args
            )
            return {"data": comparison_data}
        except Exception as e:
            return {"message": f"获取对比数据失败: {str(e)}"}, 500


class DataMiningGroupResource(Resource):
    """数据挖掘对比组管理资源"""

    def get(self):
        """获取所有保存的对比组"""
        try:
            groups = DataMiningService.get_all_comparison_groups()
            return {"success": True, "data": groups}
        except Exception as e:
            current_app.logger.error(f"获取对比组失败: {str(e)}")
            return {"success": False, "message": "获取对比组失败"}, 500

    def post(self):
        """
        保存新的对比组

        请求体格式:
        {
            "name": "对比组名称",
            "categories": [分类数组]
        }
        """
        try:
            data = request.get_json()
            if not data:
                return {"success": False, "message": "请求数据不能为空"}, 400

            name = data.get("name", "").strip()
            categories = data.get("categories", [])

            # 验证数据
            if not name:
                return {"success": False, "message": "对比组名称不能为空"}, 400
            if not categories:
                return {"success": False, "message": "至少需要选择一个分类"}, 400

            # 保存对比组
            group_data = DataMiningService.save_comparison_group(name, categories)
            return {
                "success": True,
                "message": "对比组保存成功",
                "data": group_data,
            }, 201

        except ValueError as e:
            return {"success": False, "message": str(e)}, 400
        except Exception as e:
            current_app.logger.error(f"保存对比组失败: {str(e)}")
            return {"success": False, "message": "保存对比组失败"}, 500


class DataMiningGroupDetailResource(Resource):
    """数据挖掘对比组详情资源"""

    def put(self, group_id):
        """
        更新对比组

        请求体格式:
        {
            "name": "新名称",
            "categories": [新分类数组]  // 可选
        }
        """
        try:
            data = request.get_json()
            if not data:
                return {"success": False, "message": "请求数据不能为空"}, 400

            # 过滤空值和无效数据
            update_data = {}

            if "name" in data:
                name = data["name"].strip() if data["name"] else ""
                if name:
                    update_data["name"] = name
                else:
                    return {"success": False, "message": "对比组名称不能为空"}, 400

            if "categories" in data:
                categories = data["categories"]
                if categories:
                    update_data["categories"] = categories
                else:
                    return {"success": False, "message": "至少需要选择一个分类"}, 400

            if not update_data:
                return {"success": False, "message": "没有提供要更新的数据"}, 400

            # 更新对比组
            group_data = DataMiningService.update_comparison_group(
                group_id, **update_data
            )
            return {"success": True, "message": "对比组更新成功", "data": group_data}

        except ValueError as e:
            return {"success": False, "message": str(e)}, 400
        except Exception as e:
            current_app.logger.error(f"更新对比组失败: {str(e)}")
            return {"success": False, "message": "更新对比组失败"}, 500

    def delete(self, group_id):
        """删除对比组"""
        try:
            success = DataMiningService.delete_comparison_group(group_id)
            if success:
                return {"success": True, "message": "对比组删除成功"}
            else:
                return {"success": False, "message": "对比组不存在"}, 404
        except Exception as e:
            current_app.logger.error(f"删除对比组失败: {str(e)}")
            return {"success": False, "message": "删除对比组失败"}, 500
