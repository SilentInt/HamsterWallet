# app/category_frontend.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .category_models import Category
from .database import db

category_frontend_bp = Blueprint("category_frontend", __name__, url_prefix="/category")


@category_frontend_bp.route("/")
def category_management():
    """分类管理主页面"""
    try:
        # 获取分类树结构
        root_categories = Category.get_roots()
        category_tree = [category.to_tree_dict() for category in root_categories]

        # 获取统计信息
        level1_count = Category.query.filter_by(level=1).count()
        level2_count = Category.query.filter_by(level=2).count()
        level3_count = Category.query.filter_by(level=3).count()
        total_count = Category.query.count()

        stats = {
            "level1_count": level1_count,
            "level2_count": level2_count,
            "level3_count": level3_count,
            "total_count": total_count,
        }

        # 获取所有分类用于模态框选择
        all_categories = Category.query.order_by("level", "name").all()

        return render_template(
            "category.html",
            category_tree=category_tree,
            stats=stats,
            all_categories=all_categories,
        )
    except Exception as e:
        flash(f"加载分类管理页面失败: {str(e)}", "error")
        return render_template(
            "category.html", category_tree=[], stats={}, all_categories=[]
        )


@category_frontend_bp.route("/api/category/<int:category_id>")
def get_category_api(category_id):
    """获取单个分类信息API（用于编辑模态框）"""
    try:
        category = Category.query.get(category_id)
        if not category:
            return jsonify({"success": False, "message": "分类不存在"}), 404

        # 获取可选的父分类
        # 获取所有一级和二级分类，但排除自己和可能导致循环引用的分类
        def is_descendant_of(potential_parent_id, category_id):
            """检查potential_parent_id是否是category_id的后代分类（避免循环引用）"""
            potential_parent = Category.query.get(potential_parent_id)
            while potential_parent:
                if potential_parent.id == category_id:
                    return True
                potential_parent = potential_parent.parent
            return False

        parent_categories = []

        # 获取一级分类
        level1_categories = (
            Category.query.filter_by(level=1)
            .filter(Category.id != category_id)
            .order_by("name")
            .all()
        )
        for cat in level1_categories:
            if not is_descendant_of(cat.id, category_id):
                parent_categories.append(cat)

        # 获取二级分类
        level2_categories = (
            Category.query.filter_by(level=2)
            .filter(Category.id != category_id)
            .order_by("name")
            .all()
        )
        for cat in level2_categories:
            if not is_descendant_of(cat.id, category_id):
                parent_categories.append(cat)

        return jsonify(
            {
                "success": True,
                "data": {
                    "category": category.to_dict(),
                    "parent_categories": [cat.to_dict() for cat in parent_categories],
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@category_frontend_bp.route("/api/parent-categories/<int:level>")
def get_parent_categories_api(level):
    """获取指定级别的父分类列表API"""
    try:
        if level <= 1:
            return jsonify({"success": True, "data": []})

        parent_level = level - 1
        parent_categories = (
            Category.query.filter_by(level=parent_level).order_by("name").all()
        )

        return jsonify(
            {"success": True, "data": [cat.to_dict() for cat in parent_categories]}
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@category_frontend_bp.route("/api/children/<int:parent_id>")
def get_children_api(parent_id):
    """获取子分类API（用于动态加载）"""
    try:
        children = Category.query.filter_by(parent_id=parent_id).order_by("name").all()
        return jsonify(
            {"success": True, "data": [child.to_dict() for child in children]}
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
