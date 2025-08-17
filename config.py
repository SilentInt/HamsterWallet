# config.py
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "a-hard-to-guess-string"

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "hamster.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # 图片压缩配置
    IMAGE_COMPRESSION_ENABLED = True  # 是否启用图片压缩
    IMAGE_COMPRESSION_QUALITY = 80  # JPEG压缩质量 (1-100)
    IMAGE_MAX_WIDTH = 1920  # 最大宽度
    IMAGE_MAX_HEIGHT = 1080  # 最大高度

    # OpenAI API 配置
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_API_BASE_URL = os.environ.get(
        "OPENAI_API_BASE_URL", "https://api.openai.com/v1"
    )
    MODULE_NAME = os.environ.get("MODULE_NAME", "gpt-4o-mini")
    OPENAI_TEMPERATURE = float(
        os.environ.get("OPENAI_TEMPERATURE", "0.1")
    )  # AI模型温度设置
