# app/category_api.py
from flask import Blueprint, request, jsonify
from .category_models import Category
from .database import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_

category_bp = Blueprint("category_api", __name__, url_prefix="/api/category")


@category_bp.route("/parent-options", methods=["GET"])
def get_parent_options():
    """获取父分类选项"""
    try:
        level = request.args.get("level", type=int)
        if not level or level <= 1:
            return jsonify({"success": False, "message": "无效的级别"})

        # 获取可作为父分类的分类列表
        parent_level = level - 1
        categories = Category.query.filter_by(level=parent_level).all()

        category_list = []
        for category in categories:
            category_data = {
                "id": category.id,
                "name": category.name,
                "level": category.level,
            }

            # 如果是三级分类，显示完整路径
            if level == 3 and category.parent:
                category_data["name"] = f"{category.parent.name} > {category.name}"

            category_list.append(category_data)

        return jsonify({"success": True, "categories": category_list})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@category_bp.route("/statistics", methods=["GET"])
def get_category_statistics():
    """获取分类统计信息"""
    try:
        level1_count = Category.query.filter_by(level=1).count()
        level2_count = Category.query.filter_by(level=2).count()
        level3_count = Category.query.filter_by(level=3).count()
        total_count = Category.query.count()

        return jsonify(
            {
                "success": True,
                "data": {
                    "level1_count": level1_count,
                    "level2_count": level2_count,
                    "level3_count": level3_count,
                    "total_count": total_count,
                },
            }
        )
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"获取统计信息失败: {str(e)}"}),
            500,
        )


@category_bp.route("/list", methods=["GET"])
def get_categories():
    """获取分类列表"""
    try:
        level = request.args.get("level", type=int)
        parent_id = request.args.get("parent_id", type=int)

        query = Category.query

        if level:
            query = query.filter_by(level=level)
        if parent_id:
            query = query.filter_by(parent_id=parent_id)

        categories = query.order_by("name").all()

        return jsonify(
            {"success": True, "data": [category.to_dict() for category in categories]}
        )
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"获取分类列表失败: {str(e)}"}),
            500,
        )


@category_bp.route("/tree", methods=["GET"])
def get_category_tree():
    """获取分类树结构"""
    try:
        root_categories = Category.get_roots()
        tree = [category.to_tree_dict() for category in root_categories]

        return jsonify({"success": True, "data": tree})
    except Exception as e:
        return jsonify({"success": False, "message": f"获取分类树失败: {str(e)}"}), 500


@category_bp.route("/<int:category_id>", methods=["GET"])
def get_category(category_id):
    """获取单个分类详情"""
    try:
        category = Category.query.get(category_id)
        if not category:
            return jsonify({"success": False, "message": "分类不存在"}), 404

        result = category.to_dict()

        # 添加父分类信息
        if category.parent:
            result["parent"] = category.parent.to_dict()

        # 添加子分类信息
        children = (
            Category.query.filter_by(parent_id=category_id).order_by("name").all()
        )
        result["children"] = [child.to_dict() for child in children]

        return jsonify({"success": True, "data": result})
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"获取分类详情失败: {str(e)}"}),
            500,
        )


@category_bp.route("", methods=["POST"])
def create_category():
    """创建新分类"""
    try:
        data = request.get_json()

        name = data.get("name", "").strip()
        level = data.get("level", 1)
        parent_id = data.get("parent_id")

        if not name:
            return jsonify({"success": False, "message": "分类名称不能为空"}), 400

        # 验证级别
        if level not in [1, 2, 3]:
            return jsonify({"success": False, "message": "分类级别必须为1、2或3"}), 400

        # 验证父分类
        if level > 1:
            if not parent_id:
                return (
                    jsonify(
                        {"success": False, "message": f"{level}级分类必须指定父分类"}
                    ),
                    400,
                )

            parent = Category.query.get(parent_id)
            if not parent:
                return jsonify({"success": False, "message": "父分类不存在"}), 400

            if parent.level != level - 1:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"{level}级分类的父分类必须是{level-1}级分类",
                        }
                    ),
                    400,
                )
        elif level == 1 and parent_id:
            return jsonify({"success": False, "message": "一级分类不能有父分类"}), 400

        # 检查同级分类名称是否重复
        existing = Category.query.filter_by(
            name=name, level=level, parent_id=parent_id
        ).first()
        if existing:
            return jsonify({"success": False, "message": "该级别下已存在同名分类"}), 400

        # 创建分类
        category = Category(name=name, level=level, parent_id=parent_id)
        db.session.add(category)
        db.session.commit()

        return (
            jsonify(
                {"success": True, "message": "分类创建成功", "data": category.to_dict()}
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"创建分类失败: {str(e)}"}), 500


@category_bp.route("/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    """更新分类"""
    try:
        category = Category.query.get(category_id)
        if not category:
            return jsonify({"success": False, "message": "分类不存在"}), 404

        data = request.get_json()
        name = data.get("name", "").strip()
        parent_id = data.get("parent_id")

        if not name:
            return jsonify({"success": False, "message": "分类名称不能为空"}), 400

        # 如果要改变父分类
        if parent_id != category.parent_id:
            # 验证父分类
            if parent_id:
                parent = Category.query.get(parent_id)
                if not parent:
                    return jsonify({"success": False, "message": "父分类不存在"}), 400

                # 计算新的级别
                new_level = parent.level + 1
                if new_level > 3:
                    return (
                        jsonify({"success": False, "message": "分类层级不能超过3级"}),
                        400,
                    )

                # 验证更新后不会导致子分类超过3级限制
                try:
                    category.validate_level_change(new_level)
                except ValueError as ve:
                    return jsonify({"success": False, "message": str(ve)}), 400

                # 检查是否会造成循环引用
                if parent_id == category_id or _is_ancestor(category_id, parent_id):
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "不能将分类设置为自己或子分类的子分类",
                            }
                        ),
                        400,
                    )

                category.parent_id = parent_id
                category.level = new_level
                # 递归更新所有子分类的层级
                category.update_children_levels()
            else:
                # 设置为顶级分类
                category.parent_id = None
                category.level = 1
                # 递归更新所有子分类的层级
                category.update_children_levels()

        # 检查同级分类名称是否重复（排除自己）
        existing = Category.query.filter(
            and_(
                getattr(Category, "name") == name,
                getattr(Category, "level") == category.level,
                getattr(Category, "parent_id") == category.parent_id,
                getattr(Category, "id") != category_id,
            )
        ).first()

        if existing:
            return jsonify({"success": False, "message": "该级别下已存在同名分类"}), 400

        # 更新分类名称
        category.name = name
        db.session.commit()

        return jsonify(
            {"success": True, "message": "分类更新成功", "data": category.to_dict()}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"更新分类失败: {str(e)}"}), 500


def _is_ancestor(category_id, potential_ancestor_id):
    """检查是否是祖先分类（避免循环引用）"""
    category = Category.query.get(category_id)
    while category and category.parent_id:
        if category.parent_id == potential_ancestor_id:
            return True
        category = category.parent
    return False


@category_bp.route("/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    """删除分类"""
    try:
        category = Category.query.get(category_id)
        if not category:
            return jsonify({"success": False, "message": "分类不存在"}), 404

        # 获取请求参数，检查是否级联删除
        cascade = request.args.get("cascade", "false").lower() == "true"

        # 检查是否有子分类
        children_count = Category.query.filter_by(parent_id=category_id).count()

        if children_count > 0 and not cascade:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"该分类下还有{children_count}个子分类，请选择级联删除或先删除子分类",
                        "has_children": True,
                        "children_count": children_count,
                    }
                ),
                400,
            )

        # 使用CategoryService进行删除
        from .category_service import CategoryService

        if cascade:
            # 级联删除
            CategoryService.delete_category(category_id, cascade=True)
            message = f"成功删除分类 '{category.name}' 及其所有子分类"
        else:
            # 普通删除
            CategoryService.delete_category(category_id, cascade=False)
            message = f"成功删除分类 '{category.name}'"

        return jsonify({"success": True, "message": message})

    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"删除分类失败: {str(e)}"}), 500
