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
                # 级联删除：检查所有要删除的分类是否被商品引用
                from .models import Item

                # 获取所有要删除的分类（包括自己和所有后代）
                all_categories_to_delete = [category] + category.get_descendants()
                category_ids_to_delete = [cat.id for cat in all_categories_to_delete]

                # 检查这些分类是否被商品引用
                referenced_categories = []
                for cat in all_categories_to_delete:
                    item_count = Item.query.filter_by(category_id=cat.id).count()
                    if item_count > 0:
                        referenced_categories.append(
                            {
                                "name": cat.name,
                                "level": cat.level,
                                "item_count": item_count,
                            }
                        )

                if referenced_categories:
                    # 构建错误消息
                    error_details = []
                    for ref_cat in referenced_categories:
                        error_details.append(
                            f"'{ref_cat['name']}'({ref_cat['item_count']}个商品)"
                        )

                    raise ValueError(
                        f"无法级联删除，以下分类被商品引用：{', '.join(error_details)}。"
                        f"请先使用分类合并功能处理这些商品。"
                    )

                # 如果没有商品引用，执行级联删除
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

                # 检查是否有关联的商品
                from .models import Item

                item_count = Item.query.filter_by(category_id=category_id).count()
                if item_count > 0:
                    raise ValueError(
                        f"不能删除被{item_count}个商品引用的分类，请先修改商品分类或使用分类合并功能"
                    )

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

    @staticmethod
    def get_category_usage_info(category_id: int) -> Dict[str, Any]:
        """获取分类使用信息，包括关联的商品数量和子分类数量"""
        try:
            category = Category.query.get(category_id)
            if not category:
                return {"error": "分类不存在"}

            from .models import Item

            # 统计直接关联的商品数量
            direct_items_count = Item.query.filter_by(category_id=category_id).count()

            # 统计子分类数量
            children_count = Category.query.filter_by(parent_id=category_id).count()

            # 获取所有后代分类的ID
            descendants = category.get_descendants()
            descendant_ids = [desc.id for desc in descendants]

            # 统计后代分类关联的商品数量
            descendant_items_count = 0
            if descendant_ids:
                descendant_items_count = Item.query.filter(
                    Item.category_id.in_(descendant_ids)
                ).count()

            total_items_count = direct_items_count + descendant_items_count

            return {
                "category_name": category.name,
                "direct_items_count": direct_items_count,
                "children_count": children_count,
                "descendant_categories_count": len(descendants),
                "descendant_items_count": descendant_items_count,
                "total_items_count": total_items_count,
                "can_delete": direct_items_count == 0 and children_count == 0,
            }
        except Exception as e:
            return {"error": f"获取分类使用信息失败: {str(e)}"}

    @staticmethod
    def merge_categories(
        source_category_id: int, target_category_id: int, delete_source: bool = True
    ) -> Dict[str, Any]:
        """合并分类：将源分类的所有商品和子分类迁移到目标分类

        Args:
            source_category_id: 源分类ID（将被合并的分类）
            target_category_id: 目标分类ID（合并到的分类）
            delete_source: 是否删除源分类，默认为True

        Returns:
            Dict: 合并结果信息
        """
        try:
            # 验证分类存在
            source_category = Category.query.get(source_category_id)
            target_category = Category.query.get(target_category_id)

            if not source_category:
                raise ValueError("源分类不存在")
            if not target_category:
                raise ValueError("目标分类不存在")

            if source_category_id == target_category_id:
                raise ValueError("不能将分类合并到自己")

            # 检查层级兼容性
            if source_category.level != target_category.level:
                raise ValueError("只能合并同级别的分类")

            from .models import Item

            # 1. 迁移所有关联的商品
            items_to_migrate = Item.query.filter_by(
                category_id=source_category_id
            ).all()
            migrated_items_count = len(items_to_migrate)

            for item in items_to_migrate:
                item.category_id = target_category_id
                db.session.add(item)

            # 2. 迁移子分类
            child_categories = Category.query.filter_by(
                parent_id=source_category_id
            ).all()
            migrated_children_count = len(child_categories)

            for child in child_categories:
                child.parent_id = target_category_id
                db.session.add(child)

            # 提交子分类和商品的迁移
            db.session.commit()

            # 3. 删除源分类（如果指定）
            if delete_source:
                # 再次确认没有子分类引用源分类
                remaining_children = Category.query.filter_by(
                    parent_id=source_category_id
                ).count()
                if remaining_children > 0:
                    raise ValueError(
                        f"无法删除源分类，仍有 {remaining_children} 个子分类引用它"
                    )

                # 确认没有商品引用源分类
                remaining_items = Item.query.filter_by(
                    category_id=source_category_id
                ).count()
                if remaining_items > 0:
                    raise ValueError(
                        f"无法删除源分类，仍有 {remaining_items} 个商品引用它"
                    )

                db.session.delete(source_category)
                db.session.commit()

            return {
                "success": True,
                "source_category_name": source_category.name,
                "target_category_name": target_category.name,
                "migrated_items_count": migrated_items_count,
                "migrated_children_count": migrated_children_count,
                "source_deleted": delete_source,
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def batch_update_items_category(
        item_ids: List[int], new_category_id: int
    ) -> Dict[str, Any]:
        """批量更新商品的分类

        Args:
            item_ids: 商品ID列表
            new_category_id: 新的分类ID

        Returns:
            Dict: 更新结果信息
        """
        try:
            # 验证新分类存在
            new_category = Category.query.get(new_category_id)
            if not new_category:
                raise ValueError("目标分类不存在")

            from .models import Item

            # 获取要更新的商品
            items_to_update = Item.query.filter(Item.id.in_(item_ids)).all()
            found_item_ids = [item.id for item in items_to_update]

            # 检查是否有不存在的商品ID
            missing_item_ids = [
                item_id for item_id in item_ids if item_id not in found_item_ids
            ]

            # 更新商品分类
            updated_count = 0
            for item in items_to_update:
                old_category_id = item.category_id
                item.category_id = new_category_id
                db.session.add(item)
                updated_count += 1

            db.session.commit()

            return {
                "success": True,
                "updated_count": updated_count,
                "missing_item_ids": missing_item_ids,
                "new_category_name": new_category.name,
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
