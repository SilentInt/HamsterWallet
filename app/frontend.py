# app/frontend.py
from flask import (
    render_template,
    Blueprint,
    jsonify,
    current_app,
    request,
    send_from_directory,
    redirect,
)
from .models import Receipt, Item
from .services import ReceiptService, ItemService, ExportService
import os

frontend_bp = Blueprint("frontend", __name__)


@frontend_bp.route("/")
def index():
    """重定向到小票列表页面"""
    return redirect("/receipts")


@frontend_bp.route("/receipts")
def receipt_list():
    """小票列表展示页"""
    receipts, pagination = ReceiptService.get_all_receipts(request.args)
    return render_template(
        "receipt_list.html", receipts=receipts, pagination=pagination
    )


@frontend_bp.route("/receipts_new")
def receipt_list_new():
    """小票列表展示页"""
    receipts, pagination = ReceiptService.get_all_receipts(request.args)
    return render_template(
        "receipt_list_new.html", receipts=receipts, pagination=pagination
    )


@frontend_bp.route("/test_refactor")
def test_refactor():
    receipts, pagination = ReceiptService.get_all_receipts(request.args)
    return render_template(
        "test_refactor.html", receipts=receipts, pagination=pagination
    )


@frontend_bp.route("/receipts/<int:receipt_id>")
def receipt_detail(receipt_id):
    """小票详情编辑页"""
    receipt = Receipt.query.get_or_404(receipt_id)
    return render_template("receipt_detail.html", receipt=receipt)


@frontend_bp.route("/items")
def item_list():
    """商品列表页"""
    items, pagination = ItemService.get_all_items(request.args)
    return render_template("item_list.html", items=items, pagination=pagination)


@frontend_bp.route("/report")
def report():
    """数据分析报告页"""
    return render_template("report.html")


@frontend_bp.route("/analytics")
def analytics():
    """数据报告页"""
    return render_template("analytics.html")


@frontend_bp.route("/data-mining")
def data_mining():
    """数据挖掘页"""
    return render_template("data_mining.html")


@frontend_bp.route("/config")
def get_config():
    """提供前端配置信息"""
    return jsonify(
        {
            "upload_folder": current_app.config.get("UPLOAD_FOLDER"),
            "max_content_length": current_app.config.get("MAX_CONTENT_LENGTH"),
            "debug": current_app.debug,
        }
    )


@frontend_bp.route("/static/uploads/<filename>")
def uploaded_file(filename):
    """提供上传的图片文件访问"""
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        return "Upload folder not configured", 404
    return send_from_directory(upload_folder, filename)
