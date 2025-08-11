# app/file_service.py
import os
import hashlib
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image
import io


class ImageCompressionService:
    """图片压缩服务"""

    @staticmethod
    def compress_image(image_content, quality=80, max_size=(1920, 1080)):
        """压缩图片

        Args:
            image_content: 图片内容（bytes）
            quality: JPEG压缩质量 (1-100)
            max_size: 最大尺寸 (width, height)

        Returns:
            bytes: 压缩后的图片内容
        """
        try:
            # 从bytes创建PIL图片对象
            image = Image.open(io.BytesIO(image_content))

            # 转换为RGB模式（处理RGBA等格式）
            if image.mode in ("RGBA", "LA", "P"):
                # 创建白色背景
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(
                    image, mask=image.split()[-1] if image.mode == "RGBA" else None
                )
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # 计算缩放比例
            original_width, original_height = image.size
            max_width, max_height = max_size

            if original_width > max_width or original_height > max_height:
                ratio = min(max_width / original_width, max_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 保存为JPEG格式
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue()

        except Exception as e:
            current_app.logger.error(f"Error compressing image: {e}")
            return image_content  # 返回原始内容


class FileService:
    """处理文件相关操作的服务"""

    @staticmethod
    def save_image_with_md5(
        image_file, compress=True, quality=80, max_size=(1920, 1080)
    ):
        """使用MD5值保存图片文件，支持压缩

        Args:
            image_file: 上传的图片文件对象
            compress: 是否压缩图片
            quality: JPEG压缩质量 (1-100)
            max_size: 最大尺寸 (width, height)

        Returns:
            str: 保存后的文件名，失败时返回None
        """
        if not image_file:
            return None

        try:
            # 读取文件内容
            image_content = image_file.read()

            # 如果启用压缩，先压缩图片
            if compress:
                image_content = ImageCompressionService.compress_image(
                    image_content, quality, max_size
                )

            # 计算压缩后内容的MD5
            md5_hash = hashlib.md5(image_content).hexdigest()
            filename = f"{md5_hash}.jpg"

            # 保存文件
            upload_folder = current_app.config.get("UPLOAD_FOLDER")
            if not upload_folder:
                raise ValueError("UPLOAD_FOLDER not configured")

            # 确保上传目录存在
            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, filename)

            # 直接写入压缩后的内容
            with open(file_path, "wb") as f:
                f.write(image_content)

            return filename

        except Exception as e:
            current_app.logger.error(f"Error saving image file: {e}")
            return None

    @staticmethod
    def get_image_path(filename):
        """获取图片的完整路径

        Args:
            filename: 图片文件名

        Returns:
            str: 图片的完整路径
        """
        if not filename:
            return None

        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if not upload_folder:
            return None

        return os.path.join(upload_folder, filename)

    @staticmethod
    def delete_image(filename):
        """删除图片文件

        Args:
            filename: 要删除的文件名

        Returns:
            bool: 删除成功返回True，失败返回False
        """
        if not filename:
            return True

        try:
            file_path = FileService.get_image_path(filename)
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            current_app.logger.error(f"Error deleting image file {filename}: {e}")
            return False
