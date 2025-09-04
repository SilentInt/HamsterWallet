# app/batch_category_frontend.py
from flask import Blueprint, render_template

batch_category_frontend_bp = Blueprint("batch_category_frontend", __name__)


@batch_category_frontend_bp.route("/batch-category")
def batch_category_page():
    """分类重识别页面"""
    return render_template("batch_category.html")
