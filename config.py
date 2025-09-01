# config.py
import os
import json
import shutil
import zipfile
import tempfile
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))


class ConfigManager:
    """统一配置管理器"""

    SETTINGS_FILE = os.path.join(basedir, "settings.json")

    @classmethod
    def get_default_settings(cls):
        """获取默认设定"""
        return {
            # AI API 设定
            "api_key": "",
            "api_base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o-mini",
            "temperature": 0.1,
            # AI Prompt 设定
            "receipt_prompt": cls.get_default_prompt(),
            "category_prompt": "请根据商品名称判断其所属的分类。",
            # 系统设定
            "image_compression_enabled": True,
            "image_compression_quality": 80,
            "image_max_width": 1920,
            "image_max_height": 1080,
            # 时区设定
            "user_timezone": "Asia/Shanghai",
        }

    @classmethod
    def load_settings(cls):
        """加载设定"""
        default_settings = cls.get_default_settings()

        if os.path.exists(cls.SETTINGS_FILE):
            try:
                with open(cls.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    # 合并默认设定和用户设定
                    for key, value in default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
            except Exception:
                pass

        return default_settings

    @classmethod
    def save_settings(cls, settings):
        """保存设定"""
        try:
            current_settings = cls.load_settings()
            current_settings.update(settings)

            with open(cls.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(current_settings, f, ensure_ascii=False, indent=2)
            return True, "设定保存成功"
        except Exception as e:
            return False, f"保存设定失败: {str(e)}"

    @classmethod
    def get_default_prompt(cls):
        """获取默认的AI提示词模板"""
        return """分析小票图像并返回JSON格式数据，包含以下字段：

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
{categories}"""


class Config:
    """Flask应用配置类"""

    SECRET_KEY = "a-hard-to-guess-string"

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "hamster.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    # MAX_CONTENT_LENGTH = None  # 去除文件大小限制

    def __init__(self):
        """初始化配置"""
        self.load_from_settings()

    def load_from_settings(self):
        """从设定文件加载配置"""
        settings = ConfigManager.load_settings()

        # AI API 配置
        self.OPENAI_API_KEY = settings.get("api_key", "")
        self.OPENAI_API_BASE_URL = settings.get(
            "api_base_url", "https://api.openai.com/v1"
        )
        self.AI_MODEL_NAME = settings.get("model_name", "gpt-4o-mini")
        self.OPENAI_TEMPERATURE = settings.get("temperature", 0.1)

        # 图片压缩配置
        self.IMAGE_COMPRESSION_ENABLED = settings.get("image_compression_enabled", True)
        self.IMAGE_COMPRESSION_QUALITY = settings.get("image_compression_quality", 80)
        self.IMAGE_MAX_WIDTH = settings.get("image_max_width", 1920)
        self.IMAGE_MAX_HEIGHT = settings.get("image_max_height", 1080)

    @classmethod
    def create_instance(cls):
        """创建配置实例"""
        return cls()
