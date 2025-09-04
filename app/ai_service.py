# app/ai_service.py
import base64
import json
from openai import OpenAI
from flask import current_app
from .category_service import CategoryService


class AIService:
    """处理与OpenAI交互的服务"""

    def __init__(self):
        self.client = None  # 延迟初始化
        # 移除硬编码的分类定义，改为从数据库动态获取

    def _get_category_structure_with_ids(self):
        """获取三级层级分类结构，供AI识别使用"""
        try:
            from .category_models import Category

            # 获取所有分类
            all_categories = Category.query.all()
            if not all_categories:
                return {}

            # 构建三级层级结构
            result = {}

            # 获取所有一级分类
            level1_categories = [cat for cat in all_categories if cat.level == 1]

            for level1 in level1_categories:
                level1_data = {"name": level1.name, "children": {}}

                # 获取该一级分类下的所有二级分类
                level2_categories = [
                    cat
                    for cat in all_categories
                    if cat.parent_id == level1.id and cat.level == 2
                ]

                for level2 in level2_categories:
                    level2_data = {"name": level2.name, "children": []}

                    # 获取该二级分类下的所有三级分类
                    level3_categories = [
                        cat
                        for cat in all_categories
                        if cat.parent_id == level2.id and cat.level == 3
                    ]

                    for level3 in level3_categories:
                        level2_data["children"].append(
                            {"id": level3.id, "name": level3.name}
                        )

                    # 只有当二级分类有三级子分类时才添加
                    if level2_data["children"]:
                        level1_data["children"][level2.name] = level2_data

                # 只有当一级分类有二级子分类时才添加
                if level1_data["children"]:
                    result[level1.name] = level1_data

            return result
        except Exception as e:
            current_app.logger.warning(f"从数据库获取分类结构失败: {e}")
            return {}

    def _get_client(self):
        """获取OpenAI客户端，延迟初始化"""
        if self.client is None:
            api_key = current_app.config.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            base_url = current_app.config.get(
                "OPENAI_API_BASE_URL", "https://x666.me/v1"
            )
            self.client = OpenAI(base_url=base_url, api_key=api_key)
            self.model_name = current_app.config.get("AI_MODEL_NAME", "gemini-2.5-pro")
            self.temperature = current_app.config.get("OPENAI_TEMPERATURE", 0.1)
        return self.client

    def _encode_image(self, image_path):
        """将图片文件编码为base64字符串"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _format_categories_for_prompt(self, category_structure):
        """将分类结构格式化为三级层级提示词格式
        格式：
        # 一级分类名称
        ## 二级分类名称
        三级分类名称[ID] 三级分类名称[ID] ...
        """
        if not category_structure:
            return "暂无分类定义"

        formatted_lines = []

        for level1_name, level1_data in category_structure.items():
            # 添加一级分类 (# 标题)
            formatted_lines.append(f"# {level1_name}")

            for level2_name, level2_data in level1_data["children"].items():
                # 添加二级分类 (## 标题)
                formatted_lines.append(f"## {level2_name}")

                # 添加三级分类，格式：名称[ID] 名称[ID] ...
                level3_items = []
                for level3 in level2_data["children"]:
                    level3_items.append(f"{level3['name']}[{level3['id']}]")

                if level3_items:
                    formatted_lines.append(" ".join(level3_items))

        return "\n".join(formatted_lines)

    def _build_prompt(self):
        """构建AI识别小票的精简提示词"""
        from .settings_service import SettingsService

        category_structure = self._get_category_structure_with_ids()
        print(
            "Category Structure for AI Prompt:",
            len(str(category_structure)),
            "characters",
        )

        # 获取设定中的prompt模板，如果没有则使用默认的
        settings = SettingsService.get_settings()
        prompt_template = settings.get(
            "receipt_prompt", SettingsService.get_default_prompt()
        )

        # 格式化分类列表
        categories_text = self._format_categories_for_prompt(category_structure)

        # 安全地替换模板中的分类占位符，避免format()的转义问题
        return prompt_template.replace("{categories}", categories_text)

    def recognize_receipt(self, text_description=None, image_path=None):
        """识别小票内容

        Args:
            text_description: 文字描述
            image_path: 图片路径

        Returns:
            dict: AI识别结果，失败时返回None
        """
        if not image_path and not text_description:
            raise ValueError("必须提供图片或文本描述")

        prompt = self._build_prompt()

        try:
            client = self._get_client()

            if image_path:
                base64_image = self._encode_image(image_path)
                messages = [
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": prompt}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                            {"type": "text", "text": text_description or ""},
                        ],
                    },
                ]
            else:
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text_description},
                ]
            print("AI Prompt:", prompt)

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,  # type: ignore
                temperature=self.temperature,
            )

            response_content = response.choices[0].message.content
            if response_content is None or response_content.strip() == "":
                current_app.logger.error("OpenAI API returned empty response")
                return None

            print("AI Response:", response_content)

            # 清理和解析JSON
            json_str = response_content.strip().lstrip("```json").rstrip("```")

            # 检查清理后的字符串是否为空
            if not json_str.strip():
                current_app.logger.error("Cleaned JSON string is empty")
                return None

            # print("Extracted JSON String:", json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as json_error:
                current_app.logger.error(f"JSON解析失败: {json_error}")
                current_app.logger.error(f"原始响应: {response_content}")
                current_app.logger.error(f"清理后的JSON: {json_str}")
                return None

        except Exception as e:
            current_app.logger.error(f"OpenAI API call failed: {e}")
            return None

    def _build_batch_category_prompt(self, items: list):
        """构建批量分类的提示词"""
        from .settings_service import SettingsService

        category_structure = self._get_category_structure_with_ids()

        # 获取设定中的批量分类prompt模板
        settings = SettingsService.get_settings()
        prompt_template = settings.get("category_prompt", "")

        # 格式化分类列表
        categories_text = self._format_categories_for_prompt(category_structure)

        # 构建商品列表文本
        items_text = ""
        for _, item in enumerate(items, 1):
            chinese_name = item.get("chinese_name", "").strip()
            japanese_name = item.get("japanese_name", "").strip()

            item_info = f"ID:{item['id']} - {chinese_name}"
            if japanese_name and japanese_name != chinese_name:
                item_info += f" ({japanese_name})"
            items_text += item_info + "\n"

        # 安全地替换模板中的占位符，避免format()的转义问题
        full_prompt = prompt_template
        full_prompt = full_prompt.replace("{categories}", categories_text)
        full_prompt = full_prompt.replace("{items}", items_text.strip())

        return full_prompt

    def categorize_items_batch(self, items: list) -> dict:
        """批量对多个商品进行分类

        Args:
            items: 商品列表，每个商品包含 {'id': int, 'chinese_name': str, 'japanese_name': str}

        Returns:
            dict: 包含成功标志和分类结果列表
        """
        try:
            client = self._get_client()

            # 构建完整的提示词
            prompt = self._build_batch_category_prompt(items)

            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )

            result_text = response.choices[0].message.content
            print("AI Batch Categorization Response:", result_text)
            if not result_text:
                current_app.logger.warning("AI返回了空响应")
                return {"success": False, "error": "AI返回了空响应"}

            result_text = result_text.strip()

            # 尝试解析JSON响应
            try:
                # 清理可能的markdown代码块
                cleaned_text = result_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()

                result = json.loads(cleaned_text)

                results = []
                # 检查是否有results字段
                if "results" in result:
                    results = result.get("results", [])

                # 验证结果完整性和格式
                valid_results = []
                for item_result in results:
                    if not isinstance(item_result, dict):
                        continue

                    item_id = item_result.get("item_id")
                    category_id = item_result.get("category_id")

                    if item_id is None or category_id is None:
                        current_app.logger.warning(f"结果格式不完整：{item_result}")
                        continue

                    # 确保ID是整数
                    try:
                        item_id = int(item_id)
                        category_id = int(category_id)
                    except (ValueError, TypeError):
                        current_app.logger.warning(
                            f"ID格式错误：item_id={item_id}, category_id={category_id}"
                        )
                        continue

                    # 如果没有category_name，尝试从数据库查询
                    category_name = item_result.get("category_name", "")
                    if not category_name:
                        try:
                            from .category_models import Category

                            category = Category.query.get(category_id)
                            category_name = (
                                category.name
                                if category
                                else f"未知分类({category_id})"
                            )
                        except Exception:
                            category_name = f"分类ID:{category_id}"

                    valid_results.append(
                        {
                            "item_id": item_id,
                            "category_id": category_id,
                            "category_name": category_name,
                            "reason": item_result.get("reason", ""),
                        }
                    )

                # 验证结果完整性
                if len(valid_results) != len(items):
                    current_app.logger.warning(
                        f"AI返回的有效结果数量不匹配：期望{len(items)}，实际{len(valid_results)}"
                    )

                return {"success": True, "results": valid_results}
            except json.JSONDecodeError:
                current_app.logger.warning(f"AI返回的不是有效JSON: {result_text}")
                return {
                    "success": False,
                    "error": "AI返回格式错误",
                    "raw_response": result_text,
                }

        except Exception as e:
            current_app.logger.error(f"AI批量分类失败: {e}")
            return {"success": False, "error": str(e)}
