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

    def _get_category_structure(self):
        """获取当前的分类结构，优先从数据库获取，如果数据库为空则使用默认结构"""
        try:
            from .category_models import Category

            categories = Category.get_hierarchy_for_ai()
            if categories:
                return categories
        except Exception as e:
            current_app.logger.warning(f"从数据库获取分类失败，使用默认分类: {e}")

        # 如果数据库中没有分类或获取失败，返回空结构
        return []

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
            self.model_name = current_app.config.get("MODULE_NAME", "gemini-2.5-pro")
            self.temperature = current_app.config.get("OPENAI_TEMPERATURE", 0.1)
        return self.client

    def _encode_image(self, image_path):
        """将图片文件编码为base64字符串"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _build_prompt(self):
        """构建AI识别的提示词"""
        category_structure = self._get_category_structure()

        return f"""
# 角色
你是一个专业的数据处理助手，擅长从图片中提取信息并将其结构化。

# 任务
分析提供的日本购物小票图片，提取关键信息，并按照指定的JSON格式和内容要求进行处理和输出。处理过程中，商品分类的选择必须严格遵循提供的商品分类定义表。

# 输入
一张日本购物小票的图片。

# 输出要求
**严格按照以下要求输出一个单独的JSON对象。不要包含任何markdown代码块（例如 ```json ... ```）或其他任何解释性文字或注释。**

# JSON结构和字段处理详细说明

## 顶层字段:
1.  **`store_name`** (string):
    *   准确提取小票上打印的店铺完整名称。
2.  **`store_category`** (string):
    *   根据店铺名称和售卖商品，判断店铺的主要分类。
    *   从以下列表中选择最匹配的一项：["便利店", "药妆店", "商超", "家具店", "电器店", "百货商店", "餐饮店", "专卖店", "其他"] (如果都不严格匹配但接近某一类，请选择最接近的；如果完全不匹配，请选择"其他")。
3.  **`notes`** (string):
    *   仔细查找小票上可能存在的任何备注信息（打印或手写）。
    *   如果找到，提取原文并将其翻译成**中文**。
    *   如果没有备注信息，则此字段值应为空字符串 `""`。
4.  **`name`** (string):
    *   根据小票内容生成一个简洁明了、方便用户识别的小票名称。
    *   **格式严格遵循**: "YYYY-MM-DD_购物目的简述_店铺名简写"
    *   **日期**: 使用小票上的购买日期。
    *   **购物目的简述**: 基于购买的主要商品类型或购物行为进行概括，例如 "采购食材", "购买药品", "日常用品补货", "购买电器"。
    *   **店铺名简写**: 使用店铺名称的关键部分或易于识别的缩写。
    *   **示例**: "2025-04-08_采购菜品_吴服町"
5.  **`transaction_time`** (string):
    *   提取小票上的购买日期和时间。
    *   **格式严格遵循**: "YYYY-MM-DD HH:MM:SS" (24小时制)。
6.  **`items`** (array):
    *   一个包含小票上所有购买商品的数组，数组中的每个元素都是一个代表单个商品的JSON对象。
    *   详细信息见下一节。

## `items` 数组内对象字段:
对于 `items` 数组中的每一个商品对象，包含以下字段：

1.  **`name_ja`** (string):
    *   准确提取商品在小票上显示的日文名称，包括括号内的规格、重量等信息（如果存在）。
2.  **`name_zh`** (string):
    *   基于 `name_ja`、`store_category` 等上下文信息，推断或翻译成**符合中文习惯的、具体的商品名称**。
    *   **重点**: 只标注商品是什么，**省略品牌信息**，但**保留必要的规格、数量或重量信息** (例如 "香蕉(500g)", "牛奶(1L)", "牙膏")。
    *   力求准确、自然。
3.  **`category_1`** (string):
    *   **必须**从文末提供的 **商品分类定义表** 中的一级分类中选择**最匹配**的一项。
4.  **`category_2`** (string):
    *   基于选择的 `category_1`，从 **商品分类定义表** 中对应 `category_1` 下的二级分类中选择**最匹配**的一项。
5.  **`category_3`** (string):
    *   基于选择的 `category_2`，从 **商品分类定义表** 中对应 `category_2` 下的三级分类中选择**最匹配**的一项。
    *   **此字段的值必须严格来自于商品分类定义表中列出的三级分类名称。不允许生成列表中未包含的词语。**
6.  **`price_jpy`** (number or string):
    *   计算并提取该商品（考虑数量）的**最终含税日元价格**。
    *   **注意**: 仔细判断小票上的价格是**税抜 (税前)** 还是 **税込 (税后)**，并正确计算包含消费税的总价。如果小票列出了多个相同商品，确保计算的是**总价**。
    *   输出为数值或字符串格式皆可 (例如 438 或 "438")。
7.  **`price_cny`** (number or string):
    *   根据**当前大致汇率** (如果无法获取实时汇率，可基于近期汇率估算或由用户后续处理)，将 `price_jpy` 换算成人民币价格。
    *   结果保留两位小数。
    *   输出为数值或字符串格式皆可 (例如 21.90 或 "21.90")。如果无法估算，可留空或填0。
8.  **`special_info`** (string):
    *   判断该商品是否为特价商品。
    *   检查商品行是否包含 "特売", "特価", "割引", "値引" 等明确表示折扣的字样，或者价格旁边有折扣标记。
    *   如果识别到具体的折扣比例 (例如 `20%引き`)，则填入折扣信息，格式为 **"-20%"**。
    *   如果仅能判断是特价但无法识别具体比例，则填 **"是"**。
    *   如果没有任何特价标识，则填 **"否"**。

# 商品分类定义表
**请严格按照此表选择 `category_1`, `category_2`, 和 `category_3`。**

{str(category_structure) if category_structure else "暂无分类定义，请联系管理员配置分类结构。"}
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

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,  # type: ignore
                temperature=self.temperature,
            )

            response_content = response.choices[0].message.content
            if response_content is None:
                current_app.logger.error("OpenAI API returned empty response")
                return None
            # print("AI Response:", response_content)

            # 清理和解析JSON
            json_str = response_content.strip().lstrip("```json").rstrip("```")
            # print("Extracted JSON String:", json_str)
            return json.loads(json_str)

        except Exception as e:
            current_app.logger.error(f"OpenAI API call failed: {e}")
            return None
