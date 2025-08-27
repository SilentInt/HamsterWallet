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
        """获取精简的分类结构，供AI识别使用"""
        try:
            from .category_models import Category

            # 获取所有分类
            all_categories = Category.query.all()
            if not all_categories:
                return []

            # 构建精简的扁平化结构，只包含三级分类
            level3_categories = [cat for cat in all_categories if cat.level == 3]

            # 按一级分类分组
            result = {}
            for level3 in level3_categories:
                # 获取二级分类
                level2 = next(
                    (cat for cat in all_categories if cat.id == level3.parent_id), None
                )
                if not level2:
                    continue

                # 获取一级分类
                level1 = next(
                    (cat for cat in all_categories if cat.id == level2.parent_id), None
                )
                if not level1:
                    continue

                # 按一级分类分组
                if level1.name not in result:
                    result[level1.name] = []

                # 添加三级分类信息，包含完整路径但格式简洁
                result[level1.name].append(
                    {
                        "id": level3.id,
                        "name": level3.name,
                        "path": f"{level1.name} > {level2.name} > {level3.name}",
                    }
                )

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
        """将分类结构格式化为紧凑的提示词格式"""
        if not category_structure:
            return "暂无分类定义"

        formatted_lines = []
        for level1_name, categories in category_structure.items():
            formatted_lines.append(f"\n【{level1_name}】")
            for cat in categories:
                formatted_lines.append(f"  {cat['name']} (ID:{cat['id']})")

        return "".join(formatted_lines)

    def _build_prompt(self):
        """构建AI识别小票的精简提示词"""
        category_structure = self._get_category_structure_with_ids()
        print(
            "Category Structure for AI Prompt:",
            len(str(category_structure)),
            "characters",
        )

        return f"""分析小票图像并返回JSON格式数据，包含以下字段：

**输出格式：仅返回JSON对象，不要包含markdown代码块或其他文字**

## JSON字段说明：
- `store_name`: 店铺名称
- `store_category`: 店铺类型 ["便利店","药妆店","商超","家具店","电器店","百货商店","餐饮店","专卖店","其他"]
- `notes`: 小票备注(翻译成中文，无备注则为空字符串)
- `name`: 小票标识，格式"YYYY-MM-DD_购物描述_店铺简称"
- `transaction_time`: 交易时间，格式"YYYY-MM-DD HH:MM:SS"
- `items`: 商品数组，每个商品包含：
  - `name_ja`: 日文商品名(原文)
  - `name_zh`: 中文商品名(翻译，省略品牌保留规格)
  - `category_1`: 一级分类名称
  - `category_2`: 二级分类名称  
  - `category_3`: 三级分类名称(必须从下方列表选择)
  - `category_id`: 三级分类ID(数字)
  - `price_jpy`: 含税日元价格(数字)
  - `price_cny`: 人民币价格(数字，保留2位小数)
  - `special_info`: 特价信息("-20%"/"是"/"否")

日元汇率按1日元=0.05人民币计算，价格四舍五入到分。

## 可用分类列表：
{self._format_categories_for_prompt(category_structure)}
"""

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
                # temperature=self.temperature,
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
