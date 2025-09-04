# app/settings_api.py
import os
import tempfile
from flask import Blueprint, jsonify, request, send_file
from .settings_service import SettingsService

settings_bp = Blueprint("settings_api", __name__, url_prefix="/api")


@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    """获取当前设定"""
    try:
        settings = SettingsService.get_settings()
        return jsonify({"success": True, "data": settings})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings_bp.route("/settings/ai", methods=["POST"])
def save_ai_settings():
    """保存AI设定"""
    try:
        data = request.get_json()
        success, message = SettingsService.save_ai_settings(data)

        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings_bp.route("/settings/prompt", methods=["POST"])
def save_prompt_settings():
    """保存Prompt设定"""
    try:
        data = request.get_json()
        success, message = SettingsService.save_prompt_settings(data)

        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings_bp.route("/settings/timezone", methods=["POST"])
def save_timezone_settings():
    """保存时区设定"""
    try:
        data = request.get_json()
        success, message = SettingsService.save_timezone_settings(data)

        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings_bp.route("/system-info", methods=["GET"])
def get_system_info():
    """获取系统信息"""
    try:
        info = SettingsService.get_system_info()
        return jsonify({"success": True, "data": info})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings_bp.route("/backup", methods=["POST"])
def create_backup():
    """创建备份"""
    try:
        data = request.get_json() or {}
        success, backup_file_path, backup_id = SettingsService.create_backup(data)

        if success and backup_file_path:
            # 直接返回文件给用户下载，而不是返回下载链接
            return send_file(
                backup_file_path,
                as_attachment=True,
                download_name=f"{backup_id}.zip",
                mimetype="application/zip"
            )
        else:
            return jsonify({
                "success": False,
                "message": backup_id or "备份创建失败"  # backup_id可能是错误消息
            }), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# 备份下载路由已移除，现在直接在创建备份时返回文件


@settings_bp.route("/restore", methods=["POST"])
def restore_backup():
    """从备份恢复"""
    try:
        if "backup_file" not in request.files:
            return jsonify({"success": False, "message": "未找到备份文件"}), 400

        backup_file = request.files["backup_file"]
        if backup_file.filename == "":
            return jsonify({"success": False, "message": "未选择文件"}), 400

        # 保存上传的文件到临时位置
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        backup_file.save(temp_file.name)
        temp_file.close()

        try:
            success, message = SettingsService.restore_from_backup(temp_file.name)

            return jsonify({"success": success, "message": message})
        finally:
            # 清理临时文件
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings_bp.route("/settings/default-prompt", methods=["GET"])
def get_default_prompt():
    """获取默认的prompt"""
    try:
        default_prompt = SettingsService.get_default_prompt()
        return jsonify({"success": True, "prompt": default_prompt})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings_bp.route("/settings/default-batch-category-prompt", methods=["GET"])
def get_default_batch_category_prompt():
    """获取默认的批量分类prompt"""
    try:
        default_prompt = SettingsService.get_default_batch_category_prompt()
        return jsonify({"success": True, "prompt": default_prompt})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
