# app/schemas.py
from .database import ma
from .models import Receipt, Item, DurableGood
from .category_models import Category
from marshmallow import fields, Schema


class CategorySchema(ma.SQLAlchemyAutoSchema):
    """分类 Schema"""

    class Meta:
        model = Category
        load_instance = True
        include_fk = True


class DurableGoodSchema(ma.SQLAlchemyAutoSchema):
    """耐用品 Schema"""

    class Meta:
        model = DurableGood
        load_instance = True
        include_fk = True


class ItemSchema(ma.SQLAlchemyAutoSchema):
    """商品 Schema"""
    category = fields.Nested(CategorySchema, allow_none=True)
    category_path = fields.Method("get_category_path")
    durable_info = fields.Nested(DurableGoodSchema, allow_none=True)

    class Meta:
        model = Item
        load_instance = True
        include_fk = True

    def get_category_path(self, obj):
        """获取分类路径"""
        if obj.category:
            return " > ".join(obj.category.get_full_path_list())
        return None


class ReceiptSchema(ma.SQLAlchemyAutoSchema):
    status = fields.Method("get_status_str")
    items = fields.Nested(ItemSchema, many=True)

    class Meta:
        model = Receipt
        load_instance = True
        include_fk = True
        include_relationships = True

    def get_status_str(self, obj):
        return obj.status.value if obj.status else None


class ExportRecordSchema(Schema):
    """导出记录的 Schema，包含小票和商品的组合信息"""

    # 小票信息
    receipt_id = fields.Integer()
    receipt_name = fields.String()
    store_name = fields.String()
    store_category = fields.String()
    transaction_time = fields.DateTime()
    receipt_created_at = fields.DateTime()
    receipt_status = fields.String()
    receipt_notes = fields.String()

    # 商品信息
    item_id = fields.Integer()
    item_name_ja = fields.String()
    item_name_zh = fields.String()
    price_jpy = fields.Float()
    price_cny = fields.Float()
    category_id = fields.Integer()
    category_path = fields.String()
    special_info = fields.String()
    is_special_offer = fields.Boolean()
    item_notes = fields.String()


# 实例化 Schema
receipt_schema = ReceiptSchema()
receipts_schema = ReceiptSchema(many=True, exclude=("items",))  # 列表视图不包含商品详情
item_schema = ItemSchema()
items_schema = ItemSchema(many=True)
export_record_schema = ExportRecordSchema()
export_records_schema = ExportRecordSchema(many=True)
