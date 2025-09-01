# app/__init__.py
import os
from flask import Flask
from flask_restful import Api

from config import Config
from .database import db, ma
from .frontend import frontend_bp
from .category_api import category_bp
from .category_frontend import category_frontend_bp
from .settings_api import settings_bp
from .resources import (
    ReceiptListResource,
    ReceiptResource,
    ReceiptRecognizeResource,
    ReceiptBatchUploadResource,
    ReceiptItemListResource,
    ItemListResource,
    ItemResource,
    ExportResource,
    AnalyticsDashboardResource,
    AnalyticsTrendResource,
    AnalyticsDailyItemsResource,
    AnalyticsCategoryResource,
    AnalyticsCategoryItemsResource,
    DataMiningCategoryTreeResource,
    DataMiningComparisonResource,
    DataMiningGroupResource,
    DataMiningGroupDetailResource,
)


def create_app(config_class=Config):
    # 创建配置实例并从设定文件加载
    config_instance = config_class.create_instance()

    app = Flask(__name__)
    app.config.from_object(config_instance)

    # 确保上传目录存在
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    # 初始化扩展
    db.init_app(app)
    ma.init_app(app)
    api = Api(app)

    # 注册 Blueprint
    app.register_blueprint(frontend_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(category_frontend_bp)
    app.register_blueprint(settings_bp)

    # 添加 CLI 命令
    @app.cli.command("init-db")
    def init_db_command():
        """清除现有数据并创建新表。"""
        with app.app_context():
            db.drop_all()
            db.create_all()
            print("数据库已初始化。")

    # 注册 API 资源
    # 获取小票列表
    api.add_resource(ReceiptListResource, "/api/receipts")
    # 批量上传小票
    api.add_resource(ReceiptBatchUploadResource, "/api/receipts/batch_upload")
    # 获取小票详情
    api.add_resource(ReceiptResource, "/api/receipts/<int:receipt_id>")
    # 重新处理小票
    api.add_resource(
        ReceiptRecognizeResource, "/api/receipts/<int:receipt_id>/reprocess"
    )
    # 获取小票下的商品列表
    api.add_resource(ReceiptItemListResource, "/api/receipts/<int:receipt_id>/items")
    # 商品列表
    api.add_resource(ItemListResource, "/api/items")
    # 单个商品详情
    api.add_resource(ItemResource, "/api/items/<int:item_id>")
    # 导出接口
    api.add_resource(ExportResource, "/api/export")

    # 数据分析接口
    api.add_resource(AnalyticsDashboardResource, "/api/analytics/dashboard")
    api.add_resource(AnalyticsTrendResource, "/api/analytics/trend")
    api.add_resource(
        AnalyticsDailyItemsResource, "/api/analytics/daily/<string:date>/items"
    )
    api.add_resource(AnalyticsCategoryResource, "/api/analytics/category")
    api.add_resource(
        AnalyticsCategoryItemsResource,
        "/api/analytics/category/<string:category>/items",
    )

    # 数据挖掘API
    api.add_resource(DataMiningCategoryTreeResource, "/api/data-mining/category-tree")
    api.add_resource(DataMiningComparisonResource, "/api/data-mining/comparison")
    api.add_resource(DataMiningGroupResource, "/api/data-mining/groups")
    api.add_resource(
        DataMiningGroupDetailResource, "/api/data-mining/groups/<int:group_id>"
    )

    return app
