#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端重构部署脚本
用于将重构后的前端代码应用到现有项目中
"""

import os
import shutil
import sys
from pathlib import Path


class FrontendRefactorDeployer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backup_frontend"

    def backup_original(self):
        """备份原始文件"""
        print("📦 备份原始文件...")

        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)

        self.backup_dir.mkdir(exist_ok=True)

        # 备份原始base.html
        original_base = self.project_root / "app" / "templates" / "base.html"
        if original_base.exists():
            shutil.copy2(original_base, self.backup_dir / "base.html.bak")
            print(f"✅ 已备份 {original_base}")

        # 备份原始static目录（如果存在）
        original_static = self.project_root / "app" / "static"
        if original_static.exists():
            shutil.copytree(
                original_static, self.backup_dir / "static_original", dirs_exist_ok=True
            )
            print(f"✅ 已备份 {original_static}")

        print("📦 备份完成！")

    def create_static_structure(self):
        """创建静态文件目录结构"""
        print("📁 创建静态文件目录结构...")

        static_dir = self.project_root / "app" / "static"

        # 创建目录结构
        dirs_to_create = [
            static_dir / "css",
            static_dir / "js" / "utils",
            static_dir / "js" / "components",
            static_dir / "images",
            static_dir / "fonts",
        ]

        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建目录: {dir_path}")

        print("📁 目录结构创建完成！")

    def check_dependencies(self):
        """检查依赖是否正确引入"""
        print("🔍 检查依赖...")

        base_new = self.project_root / "app" / "templates" / "base_new.html"
        if not base_new.exists():
            print("❌ base_new.html 不存在")
            return False

        # 检查CSS文件是否存在
        css_files = [
            "variables.css",
            "layout.css",
            "components.css",
            "filter.css",
            "animations.css",
        ]
        css_dir = self.project_root / "app" / "static" / "css"

        for css_file in css_files:
            if not (css_dir / css_file).exists():
                print(f"❌ CSS文件不存在: {css_file}")
                return False
            print(f"✅ CSS文件存在: {css_file}")

        # 检查JS文件是否存在
        js_files = {
            "app.js": "js",
            "common.js": "js/utils",
            "toast.js": "js/components",
            "modal.js": "js/components",
            "filter.js": "js/components",
            "image-viewer.js": "js/components",
            "list-loader.js": "js/components",
        }

        js_dir = self.project_root / "app" / "static"

        for js_file, sub_dir in js_files.items():
            if not (js_dir / sub_dir / js_file).exists():
                print(f"❌ JS文件不存在: {sub_dir}/{js_file}")
                return False
            print(f"✅ JS文件存在: {sub_dir}/{js_file}")

        print("🔍 依赖检查完成！")
        return True

    def update_flask_routes(self):
        """更新Flask路由以支持静态文件"""
        print("🔧 检查Flask静态文件配置...")

        app_py = self.project_root / "app" / "__init__.py"

        if app_py.exists():
            with open(app_py, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否已经配置了静态文件路由
            if "static_folder" not in content:
                print("💡 建议在Flask应用配置中添加静态文件支持:")
                print(
                    "   app = Flask(__name__, static_folder='static', static_url_path='/static')"
                )
            else:
                print("✅ Flask静态文件配置已存在")

    def create_migration_guide(self):
        """创建迁移指南"""
        print("📝 创建迁移指南...")

        guide_content = """# 前端重构迁移指南

## 快速开始

### 1. 使用新的base模板
将现有模板的继承从：
```jinja2
{% extends "base.html" %}
```
改为：
```jinja2
{% extends "base_new.html" %}
```

### 2. 更新CSS类名
- `.btn` → `.btn-ios`
- `.card` → `.card-ios`
- `.form-control` → `.form-control-ios`
- `.modal` → `.modal-ios`
- `.badge` → `.badge-ios`

### 3. 使用新的JavaScript组件
```javascript
// 显示Toast
Toast.success('操作成功！');

// 显示确认对话框
const confirmed = await Modal.confirm({
    title: '确认删除',
    message: '确定要删除吗？'
});

// 初始化筛选器
new Filter('.filter-section', {
    autoSubmit: true,
    debounceDelay: 800
});
```

### 4. 事件处理
将内联onclick改为数据属性：
```html
<!-- 旧方式 -->
<button onclick="deleteItem(123)">删除</button>

<!-- 新方式 -->
<button data-action="delete" data-item-id="123">删除</button>
```

### 5. 图片预览
```html
<!-- 自动启用预览 -->
<img src="image.jpg" alt="图片" />

<!-- 禁用预览 -->
<img src="image.jpg" alt="图片" data-no-preview />
```

## 完整示例页面
参考 `receipt_list_new.html` 了解完整的实现方式。

## 常见问题

### Q: 如何保持原有样式？
A: 重构后的样式是基于原有设计的改进版本，视觉效果基本一致。

### Q: 旧页面会受影响吗？
A: 不会，旧页面继续使用原有的base.html，新页面使用base_new.html。

### Q: 如何调试新的JavaScript组件？
A: 打开浏览器开发者工具，在Console中可以访问 `window.HamsterWalletApp`。

## 性能优化建议

1. 启用Gzip压缩
2. 设置适当的缓存头
3. 考虑使用CDN
4. 压缩CSS和JavaScript文件

## 联系支持
如有问题，请参考 FRONTEND_REFACTOR_SUMMARY.md 文档。
"""

        guide_path = self.project_root / "MIGRATION_GUIDE.md"
        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(guide_content)

        print(f"📝 迁移指南已创建: {guide_path}")

    def deploy(self):
        """执行部署"""
        print("🚀 开始前端重构部署...")
        print("=" * 50)

        try:
            # 1. 备份原始文件
            self.backup_original()
            print()

            # 2. 创建目录结构
            self.create_static_structure()
            print()

            # 3. 检查依赖
            if not self.check_dependencies():
                print("❌ 依赖检查失败，请确保所有文件都已正确创建")
                return False
            print()

            # 4. 更新Flask配置提示
            self.update_flask_routes()
            print()

            # 5. 创建迁移指南
            self.create_migration_guide()
            print()

            print("🎉 前端重构部署完成！")
            print()
            print("📋 后续步骤:")
            print("1. 重启Flask应用")
            print("2. 访问 /static/css/variables.css 确认静态文件可访问")
            print("3. 创建新页面时使用 base_new.html 模板")
            print("4. 参考 MIGRATION_GUIDE.md 进行页面迁移")
            print("5. 如有问题，原始文件已备份到 backup_frontend/ 目录")

            return True

        except Exception as e:
            print(f"❌ 部署失败: {str(e)}")
            return False


def main():
    if len(sys.argv) != 2:
        print("使用方法: python deploy_refactor.py <项目根目录>")
        print("示例: python deploy_refactor.py /path/to/HamsterWallet")
        sys.exit(1)

    project_root = sys.argv[1]

    if not os.path.exists(project_root):
        print(f"❌ 项目目录不存在: {project_root}")
        sys.exit(1)

    deployer = FrontendRefactorDeployer(project_root)
    success = deployer.deploy()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
