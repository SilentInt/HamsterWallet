# app/category_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from .database import db
from .category_models import Category


class CategoryService:
    """分类服务类"""

    @staticmethod
    def get_category_tree() -> List[Dict[str, Any]]:
        """获取分类树结构"""
        try:
            # 获取一级分类
            level1_categories = Category.query.filter_by(level=1).order_by("name").all()

            tree = []
            for cat1 in level1_categories:
                cat1_dict = cat1.to_dict()
                cat1_dict["children"] = []

                # 获取二级分类
                level2_categories = (
                    Category.query.filter_by(parent_id=cat1.id, level=2)
                    .order_by("name")
                    .all()
                )
                for cat2 in level2_categories:
                    cat2_dict = cat2.to_dict()
                    cat2_dict["children"] = []

                    # 获取三级分类
                    level3_categories = (
                        Category.query.filter_by(parent_id=cat2.id, level=3)
                        .order_by("name")
                        .all()
                    )
                    for cat3 in level3_categories:
                        cat2_dict["children"].append(cat3.to_dict())

                    cat1_dict["children"].append(cat2_dict)

                tree.append(cat1_dict)

            return tree

        except Exception as e:
            print(f"获取分类树失败: {str(e)}")
            return []

    @staticmethod
    def get_category_statistics() -> Dict[str, int]:
        """获取分类统计信息"""
        try:
            level1_count = Category.query.filter_by(level=1).count()
            level2_count = Category.query.filter_by(level=2).count()
            level3_count = Category.query.filter_by(level=3).count()
            total_count = Category.query.count()

            return {
                "level1_count": level1_count,
                "level2_count": level2_count,
                "level3_count": level3_count,
                "total_count": total_count,
            }

        except Exception as e:
            print(f"获取分类统计失败: {str(e)}")
            return {
                "level1_count": 0,
                "level2_count": 0,
                "level3_count": 0,
                "total_count": 0,
            }

    @staticmethod
    def create_category(
        name: str, level: int, parent_id: Optional[int] = None
    ) -> Category:
        """创建分类"""
        try:
            # 验证级别
            if level < 1 or level > 3:
                raise ValueError("分类级别必须在1-3之间")

            # 验证父分类
            if level > 1:
                if not parent_id:
                    raise ValueError("二级和三级分类必须指定父分类")

                parent = Category.query.get(parent_id)
                if not parent:
                    raise ValueError("父分类不存在")

                if parent.level != level - 1:
                    raise ValueError("父分类级别不正确")

            # 检查同级分类名称是否重复
            existing = Category.query.filter_by(
                name=name, level=level, parent_id=parent_id
            ).first()

            if existing:
                raise ValueError("该级别下已存在同名分类")

            # 创建分类
            category = Category(name=name, level=level, parent_id=parent_id)
            db.session.add(category)
            db.session.commit()

            return category

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_category(
        category_id: int, name: str, parent_id: Optional[int] = None
    ) -> Category:
        """更新分类"""
        try:
            category = Category.query.get(category_id)
            if not category:
                raise ValueError("分类不存在")

            # 如果要改变父分类
            if parent_id != category.parent_id:
                if parent_id:
                    parent = Category.query.get(parent_id)
                    if not parent:
                        raise ValueError("父分类不存在")

                    new_level = parent.level + 1
                    if new_level > 3:
                        raise ValueError("分类层级不能超过3级")

                    # 验证更新后不会导致子分类超过3级限制
                    category.validate_level_change(new_level)

                    # 检查是否会造成循环引用
                    if CategoryService._is_ancestor(category_id, parent_id):
                        raise ValueError("不能将分类设置为自己或子分类的子分类")

                    category.parent_id = parent_id
                    category.level = new_level
                    # 递归更新所有子分类的层级
                    category.update_children_levels()
                else:
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
                raise ValueError("该级别下已存在同名分类")

            category.name = name
            db.session.commit()

            return category

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete_category(category_id: int, cascade: bool = False) -> bool:
        """删除分类

        Args:
            category_id: 分类ID
            cascade: 是否级联删除子分类，默认为False
        """
        try:
            category = Category.query.get(category_id)
            if not category:
                raise ValueError("分类不存在")

            if cascade:
                # 级联删除：使用模型的删除方法
                deleted_count = category.delete_with_descendants()
                db.session.commit()
                print(f"级联删除了 {deleted_count} 个分类")
                return True
            else:
                # 非级联删除：检查是否有子分类
                children_count = Category.query.filter_by(parent_id=category_id).count()
                if children_count > 0:
                    raise ValueError(
                        "不能删除有子分类的分类，请使用级联删除或先删除子分类"
                    )

                # 这里应该检查是否有关联的商品，暂时跳过

                db.session.delete(category)
                db.session.commit()
                return True

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_parent_options(level: int) -> List[Category]:
        """获取父分类选项"""
        try:
            if level <= 1:
                return []

            parent_level = level - 1
            return Category.query.filter_by(level=parent_level).order_by("name").all()

        except Exception as e:
            print(f"获取父分类选项失败: {str(e)}")
            return []

    @staticmethod
    def _is_ancestor(category_id: int, potential_ancestor_id: int) -> bool:
        """检查是否是祖先分类（避免循环引用）"""
        category = Category.query.get(category_id)
        while category and category.parent_id:
            if category.parent_id == potential_ancestor_id:
                return True
            category = category.parent
        return False

    @staticmethod
    def get_category_by_id(category_id: int) -> Optional[Category]:
        """根据ID获取分类"""
        try:
            return Category.query.get(category_id)
        except Exception as e:
            print(f"获取分类失败: {str(e)}")
            return None

    @staticmethod
    def get_categories_by_level(level: int) -> List[Category]:
        """根据级别获取分类列表"""
        try:
            return Category.query.filter_by(level=level).order_by("name").all()
        except Exception as e:
            print(f"获取分类列表失败: {str(e)}")
            return []
