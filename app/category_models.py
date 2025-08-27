# app/category_models.py
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship, backref
from .database import db


class Category(db.Model):
    """统一的分类模型，支持三级分类结构"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="分类名称")
    level = Column(Integer, nullable=False, comment="分类级别：1-一级，2-二级，3-三级")
    parent_id = Column(
        Integer, ForeignKey("categories.id"), nullable=True, comment="父分类ID"
    )

    # 自引用关系
    parent = relationship(
        "Category", remote_side=[id], backref=backref("children", lazy="dynamic")
    )

    # 表约束
    __table_args__ = (
        db.Index("idx_category_level", "level"),
        db.Index("idx_category_parent", "parent_id"),
        {"comment": "统一分类表"},
    )

    def __init__(self, name, level, parent_id=None, path=None, description=None):
        self.name = name
        self.level = level
        self.parent_id = parent_id
        self.description = description

    def get_ancestors(self) -> List["Category"]:
        """获取所有祖先分类"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def get_descendants(self) -> List["Category"]:
        """获取所有后代分类"""
        descendants = []
        children_query = Category.query.filter_by(parent_id=self.id)
        for child in children_query:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def delete_with_descendants(self) -> int:
        """删除自己及所有后代分类

        Returns:
            int: 删除的分类数量
        """
        from .database import db

        deleted_count = 0

        # 先获取所有后代分类
        descendants = self.get_descendants()

        # 按层级从深到浅删除（先删子类，再删父类）
        # 按level倒序排列，确保先删除深层分类
        level_groups = {}
        for desc in descendants:
            level = desc.level
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(desc)

        # 从最深层级开始删除
        for level in sorted(level_groups.keys(), reverse=True):
            for category in level_groups[level]:
                db.session.delete(category)
                deleted_count += 1

        # 最后删除自己
        db.session.delete(self)
        deleted_count += 1

        return deleted_count

    def is_root(self) -> bool:
        """判断是否为根节点"""
        return self.parent_id is None

    def get_full_path_list(self):
        """获取完整路径列表"""
        path_list = []
        for ancestor in self.get_ancestors():
            path_list.append(ancestor.name)
        path_list.append(self.name)
        return path_list

    @classmethod
    def get_hierarchy_for_ai(cls):
        """获取用于AI的层次结构"""

        def build_hierarchy(categories):
            result = []
            for category in categories:
                node = {
                    "name": category.name,
                    "path": category.path,
                    "level": category.level,
                }
                # 获取子分类
                children_query = (
                    cls.query.filter_by(parent_id=category.id).order_by(cls.name).all()
                )
                if children_query:
                    node["children"] = build_hierarchy(children_query)
                result.append(node)
            return result

        # 获取所有一级分类
        root_categories = cls.query.filter_by(level=1).order_by(cls.name).all()
        return build_hierarchy(root_categories)

    @classmethod
    def get_by_level(cls, level):
        """获取指定级别的所有分类"""
        return cls.query.filter_by(level=level).order_by(cls.name).all()

    @classmethod
    def get_roots(cls):
        """获取所有根分类"""
        return cls.query.filter_by(level=1).order_by(cls.name).all()

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "parent_id": self.parent_id,
            "is_root": self.is_root(),
        }

    def to_tree_dict(self):
        """转换为树形字典"""
        result = self.to_dict()
        # 查询子分类
        from sqlalchemy import and_

        children_query = (
            db.session.query(self.__class__)
            .filter(and_(self.__class__.parent_id == self.id))
            .order_by(self.__class__.name)
            .all()
        )
        if children_query:
            result["children"] = [child.to_tree_dict() for child in children_query]
        return result

    def __repr__(self):
        return f'<Category(id={self.id}, name="{self.name}", level={self.level}")>'

    def __str__(self):
        return f"{self.name} (Level {self.level})"
