# app/settings_service.py
import os
import shutil
import zipfile
import tempfile
from datetime import datetime
from flask import current_app
from .database import db
from .models import Receipt, Item
from .category_models import Category


class SettingsService:
    """系统设定服务 - 使用统一的ConfigManager"""

    @staticmethod
    def get_settings():
        """获取当前设定"""
        from config import ConfigManager

        return ConfigManager.load_settings()

    @staticmethod
    def save_ai_settings(settings):
        """保存AI设定"""
        try:
            from config import ConfigManager

            # 只保存AI相关设定
            ai_settings = {
                "api_key": settings.get("api_key", ""),
                "api_base_url": settings.get("api_base_url", ""),
                "model_name": settings.get("model_name", ""),
                "temperature": settings.get("temperature", 0.1),
            }

            success, message = ConfigManager.save_settings(ai_settings)

            if success:
                # 更新当前应用配置（运行时使用）
                current_app.config["OPENAI_API_KEY"] = ai_settings["api_key"]
                current_app.config["OPENAI_API_BASE_URL"] = ai_settings["api_base_url"]
                current_app.config["AI_MODEL_NAME"] = ai_settings["model_name"]
                current_app.config["OPENAI_TEMPERATURE"] = ai_settings["temperature"]

            return success, message

        except Exception as e:
            return False, f"保存AI设定失败: {str(e)}"

    @staticmethod
    def save_prompt_settings(settings):
        """保存Prompt设定"""
        try:
            from config import ConfigManager

            # 只保存Prompt相关设定
            prompt_settings = {
                "receipt_prompt": settings.get("receipt_prompt", ""),
                "category_prompt": settings.get("category_prompt", ""),
            }

            return ConfigManager.save_settings(prompt_settings)

        except Exception as e:
            return False, f"保存Prompt设定失败: {str(e)}"

    @staticmethod
    def get_default_prompt():
        """获取默认Prompt"""
        from config import ConfigManager

        return ConfigManager.get_default_prompt()

    @staticmethod
    def get_system_info():
        """获取系统信息"""
        try:
            # 统计数据
            receipt_count = Receipt.query.count()
            item_count = Item.query.count()

            # 计算存储使用情况
            upload_folder = current_app.config.get("UPLOAD_FOLDER", "")
            storage_usage = "未知"

            if upload_folder and os.path.exists(upload_folder):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(upload_folder):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if os.path.exists(fp):
                            total_size += os.path.getsize(fp)

                # 转换为可读格式
                if total_size > 1024 * 1024 * 1024:  # GB
                    storage_usage = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
                elif total_size > 1024 * 1024:  # MB
                    storage_usage = f"{total_size / (1024 * 1024):.2f} MB"
                elif total_size > 1024:  # KB
                    storage_usage = f"{total_size / 1024:.2f} KB"
                else:
                    storage_usage = f"{total_size} B"

            return {
                "receipt_count": receipt_count,
                "item_count": item_count,
                "storage_usage": storage_usage,
                "upload_path": upload_folder,
            }

        except Exception as e:
            upload_folder = current_app.config.get("UPLOAD_FOLDER", "")
            return {
                "receipt_count": 0,
                "item_count": 0,
                "storage_usage": "计算错误",
                "upload_path": upload_folder,
            }

    @staticmethod
    def create_backup(options):
        """创建系统备份"""
        try:
            from config import ConfigManager

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"hamster_backup_{timestamp}"
            temp_dir = tempfile.mkdtemp()
            backup_dir = os.path.join(temp_dir, backup_name)
            os.makedirs(backup_dir, exist_ok=True)

            # 备份数据库
            if options.get("include_database", True):
                db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "").replace(
                    "sqlite:///", ""
                )
                if db_path and os.path.exists(db_path):
                    shutil.copy2(db_path, os.path.join(backup_dir, "hamster.db"))

            # 备份图片文件
            if options.get("include_images", True):
                upload_folder = current_app.config.get("UPLOAD_FOLDER", "")
                if upload_folder and os.path.exists(upload_folder):
                    images_dir = os.path.join(backup_dir, "uploads")
                    shutil.copytree(upload_folder, images_dir)

            # 备份设定
            if options.get("include_settings", True):
                settings_dir = os.path.join(backup_dir, "settings")
                os.makedirs(settings_dir, exist_ok=True)

                # 备份设定文件
                if os.path.exists(ConfigManager.SETTINGS_FILE):
                    shutil.copy2(
                        ConfigManager.SETTINGS_FILE,
                        os.path.join(settings_dir, "settings.json"),
                    )

            # 创建压缩包
            backup_zip = os.path.join(temp_dir, f"{backup_name}.zip")
            with zipfile.ZipFile(backup_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(backup_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, backup_dir)
                        zipf.write(file_path, arcname)

            return True, backup_zip, backup_name

        except Exception as e:
            return False, None, f"备份失败: {str(e)}"

    @staticmethod
    def restore_from_backup(backup_file):
        """从备份恢复数据"""
        try:
            from config import ConfigManager

            temp_dir = tempfile.mkdtemp()

            # 解压备份文件
            with zipfile.ZipFile(backup_file, "r") as zipf:
                zipf.extractall(temp_dir)

            # 查找解压后的文件
            extracted_items = os.listdir(temp_dir)
            if not extracted_items:
                return False, "备份文件为空"

            backup_root = temp_dir
            if len(extracted_items) == 1 and os.path.isdir(
                os.path.join(temp_dir, extracted_items[0])
            ):
                backup_root = os.path.join(temp_dir, extracted_items[0])

            # 恢复数据库
            db_backup = os.path.join(backup_root, "hamster.db")
            if os.path.exists(db_backup):
                db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "").replace(
                    "sqlite:///", ""
                )
                if db_path:
                    # 备份当前数据库
                    if os.path.exists(db_path):
                        shutil.copy2(db_path, f"{db_path}.backup")
                    shutil.copy2(db_backup, db_path)

            # 恢复图片文件
            uploads_backup = os.path.join(backup_root, "uploads")
            if os.path.exists(uploads_backup):
                upload_folder = current_app.config.get("UPLOAD_FOLDER", "")
                if upload_folder:
                    # 备份当前上传文件夹
                    if os.path.exists(upload_folder):
                        shutil.move(upload_folder, f"{upload_folder}.backup")
                    shutil.copytree(uploads_backup, upload_folder)

            # 恢复设定
            settings_backup = os.path.join(backup_root, "settings")
            if os.path.exists(settings_backup):
                # 恢复设定文件
                settings_file_backup = os.path.join(settings_backup, "settings.json")
                if os.path.exists(settings_file_backup):
                    shutil.copy2(settings_file_backup, ConfigManager.SETTINGS_FILE)

            # 清理临时文件
            shutil.rmtree(temp_dir)

            return True, "恢复成功"

        except Exception as e:
            return False, f"恢复失败: {str(e)}"
