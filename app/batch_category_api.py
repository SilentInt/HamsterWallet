# app/batch_category_api.py
from flask import Blueprint, request, jsonify, current_app, g
from .models import Item
from .category_models import Category
from .database import db
from .ai_service import AIService
import threading
import time
from datetime import datetime
from sqlalchemy import text
import logging
from werkzeug.local import LocalProxy

batch_category_bp = Blueprint(
    "batch_category_api", __name__, url_prefix="/api/batch-category"
)


# 全局任务状态
class TaskStatus:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    APPLYING = "APPLYING"


# 全局任务状态管理
current_task = {
    "status": TaskStatus.IDLE,
    "total_items": 0,
    "processed_items": 0,
    "total_batches": 0,
    "current_batch_index": 0,
    "success_count": 0,
    "skipped_count": 0,
    "failed_count": 0,
    "applied_count": 0,
    "results_ready": False,
    "error_message": None,
    "results": [],  # 存储结果
    "batch_size": 50,
}

task_lock = threading.Lock()


def reset_task():
    """重置任务状态"""
    global current_task
    current_task.update(
        {
            "status": TaskStatus.IDLE,
            "total_items": 0,
            "processed_items": 0,
            "total_batches": 0,
            "current_batch_index": 0,
            "success_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "applied_count": 0,
            "results_ready": False,
            "error_message": None,
            "results": [],
            "batch_size": 50,
        }
    )


@batch_category_bp.route("/task", methods=["GET"])
def get_task_status():
    """获取当前任务状态和摘要"""
    with task_lock:
        return jsonify(
            {
                "success": True,
                "data": {
                    "status": current_task["status"],
                    "total_items": current_task["total_items"],
                    "processed_items": current_task["processed_items"],
                    "total_batches": current_task["total_batches"],
                    "current_batch_index": current_task["current_batch_index"],
                    "success_count": current_task["success_count"],
                    "skipped_count": current_task["skipped_count"],
                    "failed_count": current_task["failed_count"],
                    "applied_count": current_task["applied_count"],
                    "results_ready": current_task["results_ready"],
                    "error_message": current_task["error_message"],
                },
            }
        )


@batch_category_bp.route("/task", methods=["POST"])
def start_task():
    """启动新的批量分类任务"""
    try:
        data = request.get_json()
        batch_size = data.get("batch_size", 50)

        with task_lock:
            # 检查是否有任务正在运行
            if current_task["status"] in [TaskStatus.RUNNING, TaskStatus.APPLYING]:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "已有任务正在运行，请等待完成或先停止当前任务",
                        }
                    ),
                    409,
                )

            # 重置任务状态
            reset_task()
            current_task["status"] = TaskStatus.RUNNING
            current_task["batch_size"] = batch_size

        # 启动后台任务
        # 获取真正的应用实例，而不是代理对象
        import copy

        app_config = copy.deepcopy(current_app.config)

        # 将应用实例通过import方式获取
        def get_app():
            from run import app

            return app

        thread = threading.Thread(
            target=_process_batch_task, args=(get_app, batch_size)
        )
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "message": "批量分类任务已启动"}), 202

    except Exception as e:
        logging.error(f"启动批量任务失败: {str(e)}")
        return jsonify({"success": False, "message": f"启动任务失败: {str(e)}"}), 500


@batch_category_bp.route("/task/results", methods=["GET"])
def get_task_results():
    """获取任务结果，一次性返回全部"""
    try:
        with task_lock:
            # 允许在任务运行时或停止时查看已完成的结果
            if current_task["status"] == TaskStatus.IDLE:
                return (
                    jsonify({"success": False, "message": "当前没有任务结果"}),
                    400,
                )

            # 一次性返回所有结果
            return jsonify(
                {
                    "success": True,
                    "data": current_task["results"],
                    "meta": {
                        "total_results": len(current_task["results"]),
                        "task_status": current_task["status"],
                    },
                }
            )

    except Exception as e:
        logging.error(f"获取结果失败: {str(e)}")
        return jsonify({"success": False, "message": f"获取结果失败: {str(e)}"}), 500


@batch_category_bp.route("/task/results/available", methods=["GET"])
def get_available_results():
    """获取当前可查看的结果概览"""
    try:
        with task_lock:
            if current_task["status"] == TaskStatus.IDLE:
                return jsonify({"success": False, "message": "当前没有任务结果"}), 400

            total_results = len(current_task["results"])
            completed_batches = (
                (total_results + current_task["batch_size"] - 1)
                // current_task["batch_size"]
                if total_results > 0
                else 0
            )

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "total_results": total_results,
                        "completed_batches": completed_batches,
                        "batch_size": current_task["batch_size"],
                        "task_status": current_task["status"],
                        "has_results": total_results > 0,
                        "can_view_results": total_results > 0,
                    },
                }
            )

    except Exception as e:
        logging.error(f"获取可用结果失败: {str(e)}")
        return (
            jsonify({"success": False, "message": f"获取可用结果失败: {str(e)}"}),
            500,
        )


@batch_category_bp.route("/task/restart", methods=["POST"])
def restart_task():
    """重新开始任务"""
    try:
        data = request.get_json()
        batch_size = data.get("batch_size", 50)

        with task_lock:
            if current_task["status"] in [TaskStatus.RUNNING, TaskStatus.APPLYING]:
                return (
                    jsonify(
                        {"success": False, "message": "任务正在运行中，请先停止任务"}
                    ),
                    409,
                )

            # 完全重置任务状态
            reset_task()
            current_task["status"] = TaskStatus.RUNNING
            current_task["batch_size"] = batch_size

        # 启动新任务
        def get_app():
            from run import app

            return app

        thread = threading.Thread(
            target=_process_batch_task, args=(get_app, batch_size)
        )
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "message": "任务已重新开始"}), 202

    except Exception as e:
        logging.error(f"重新开始任务失败: {str(e)}")
        return (
            jsonify({"success": False, "message": f"重新开始任务失败: {str(e)}"}),
            500,
        )


@batch_category_bp.route("/task/results/summary", methods=["GET"])
def get_results_summary():
    """获取结果汇总统计"""
    try:
        with task_lock:
            if current_task["status"] not in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.STOPPED,
            ]:
                return (
                    jsonify(
                        {"success": False, "message": "任务尚未完成，无法获取统计"}
                    ),
                    400,
                )

            # 统计分类变更情况
            category_changes = {}
            for result in current_task["results"]:
                old_cat = result["old_category"]
                new_cat = result["new_category"]

                change_key = f"{old_cat} → {new_cat}"
                if change_key not in category_changes:
                    category_changes[change_key] = 0
                category_changes[change_key] += 1

            # 排序并取前10个变更类型
            sorted_changes = sorted(
                category_changes.items(), key=lambda x: x[1], reverse=True
            )[:10]

            summary = {
                "total_changes": len(current_task["results"]),
                "applied_changes": current_task["applied_count"],
                "pending_changes": len(
                    [r for r in current_task["results"] if not r["is_applied"]]
                ),
                "category_changes": sorted_changes,
                "success_rate": (
                    current_task["success_count"] / max(current_task["total_items"], 1)
                )
                * 100,
                "processing_stats": {
                    "total_items": current_task["total_items"],
                    "success_count": current_task["success_count"],
                    "skipped_count": current_task["skipped_count"],
                    "failed_count": current_task["failed_count"],
                },
            }

            return jsonify({"success": True, "data": summary})

    except Exception as e:
        logging.error(f"获取统计失败: {str(e)}")
        return jsonify({"success": False, "message": f"获取统计失败: {str(e)}"}), 500


@batch_category_bp.route("/task/results/preview", methods=["GET"])
def preview_results():
    """预览将要应用的结果（前N条）"""
    try:
        limit = request.args.get("limit", 20, type=int)

        with task_lock:
            if current_task["status"] not in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.STOPPED,
            ]:
                return (
                    jsonify(
                        {"success": False, "message": "任务尚未完成，无法预览结果"}
                    ),
                    400,
                )

            # 获取未应用的结果
            unapplied_results = [
                r for r in current_task["results"] if not r["is_applied"]
            ]
            preview_results = unapplied_results[:limit]

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "preview": preview_results,
                        "total_unapplied": len(unapplied_results),
                        "preview_count": len(preview_results),
                    },
                }
            )

    except Exception as e:
        logging.error(f"预览结果失败: {str(e)}")
        return jsonify({"success": False, "message": f"预览结果失败: {str(e)}"}), 500


@batch_category_bp.route("/task/apply/partial", methods=["POST"])
def apply_partial_results():
    """应用部分分类结果"""
    try:
        data = request.get_json()
        item_ids = data.get("item_ids", [])  # 要应用的商品ID列表

        if not item_ids:
            return jsonify({"success": False, "message": "请选择要应用的商品"}), 400

        with task_lock:
            if current_task["status"] != TaskStatus.COMPLETED:
                return (
                    jsonify(
                        {"success": False, "message": "任务尚未完成，无法应用结果"}
                    ),
                    400,
                )

        # 应用指定的商品分类
        success_count = 0
        error_count = 0

        try:
            for result in current_task["results"]:
                if result["item_id"] in item_ids and not result["is_applied"]:
                    try:
                        item = Item.query.get(result["item_id"])
                        if item:
                            item.category_id = result["new_category_id"]
                            db.session.commit()

                            result["is_applied"] = True
                            success_count += 1

                            with task_lock:
                                current_task["applied_count"] += 1
                    except Exception as e:
                        logging.error(
                            f"应用商品 {result['item_id']} 分类失败: {str(e)}"
                        )
                        error_count += 1
                        continue

            return jsonify(
                {
                    "success": True,
                    "message": f"成功应用 {success_count} 个商品的分类",
                    "data": {
                        "applied_count": success_count,
                        "error_count": error_count,
                        "total_applied": current_task["applied_count"],
                    },
                }
            )

        except Exception as e:
            logging.error(f"部分应用失败: {str(e)}")
            return (
                jsonify({"success": False, "message": f"部分应用失败: {str(e)}"}),
                500,
            )

    except Exception as e:
        logging.error(f"部分应用结果失败: {str(e)}")
        return (
            jsonify({"success": False, "message": f"部分应用结果失败: {str(e)}"}),
            500,
        )


@batch_category_bp.route("/task/continue", methods=["POST"])
def continue_recognition():
    """继续识别剩余商品"""
    try:
        data = request.get_json()
        batch_size = data.get("batch_size", current_task.get("batch_size", 50))

        with task_lock:
            if current_task["status"] not in [
                TaskStatus.COMPLETED,
                TaskStatus.STOPPED,
                TaskStatus.FAILED,
            ]:
                return (
                    jsonify(
                        {"success": False, "message": "当前任务状态不允许继续识别"}
                    ),
                    400,
                )

            # 检查是否还有未处理的商品
            all_items = Item.query.filter(Item.name_zh.isnot(None)).all()
            processed_item_ids = {r["item_id"] for r in current_task["results"]}
            remaining_items = [
                item for item in all_items if item.id not in processed_item_ids
            ]

            if not remaining_items:
                return (
                    jsonify({"success": False, "message": "所有商品都已处理完成"}),
                    400,
                )

            # 重置部分任务状态以继续处理
            current_task["status"] = TaskStatus.RUNNING
            current_task["batch_size"] = batch_size
            current_task["total_items"] = current_task.get("processed_items", 0) + len(
                remaining_items
            )

        # 启动继续处理任务
        def get_app():
            from run import app

            return app

        thread = threading.Thread(
            target=_continue_batch_task, args=(get_app, remaining_items, batch_size)
        )
        thread.daemon = True
        thread.start()

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"继续识别任务已启动，剩余 {len(remaining_items)} 个商品",
                }
            ),
            202,
        )

    except Exception as e:
        logging.error(f"继续识别失败: {str(e)}")
        return jsonify({"success": False, "message": f"继续识别失败: {str(e)}"}), 500


@batch_category_bp.route("/task/apply", methods=["POST"])
def apply_results():
    """应用分类结果"""
    try:
        data = request.get_json()
        scope = data.get("scope", "all")  # "all" 或 "batch"
        batch_index = data.get("batch_index", 0)

        with task_lock:
            if current_task["status"] != TaskStatus.COMPLETED:
                return (
                    jsonify(
                        {"success": False, "message": "任务尚未完成，无法应用结果"}
                    ),
                    400,
                )

            current_task["status"] = TaskStatus.APPLYING

        # 启动应用任务
        def get_app():
            from run import app

            return app

        thread = threading.Thread(
            target=_apply_results_task, args=(get_app, scope, batch_index)
        )
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "message": "分类结果应用任务已启动"}), 202

    except Exception as e:
        logging.error(f"应用结果失败: {str(e)}")
        return jsonify({"success": False, "message": f"应用结果失败: {str(e)}"}), 500


@batch_category_bp.route("/task/stop", methods=["POST"])
def stop_task():
    """停止当前任务"""
    try:
        with task_lock:
            if current_task["status"] in [TaskStatus.RUNNING, TaskStatus.APPLYING]:
                current_task["status"] = TaskStatus.STOPPED
                # 如果有结果，设置为可查看
                if current_task["success_count"] > 0:
                    current_task["results_ready"] = True
                return jsonify({"success": True, "message": "任务已停止"})
            else:
                return (
                    jsonify({"success": False, "message": "当前没有正在运行的任务"}),
                    400,
                )

    except Exception as e:
        logging.error(f"停止任务失败: {str(e)}")
        return jsonify({"success": False, "message": f"停止任务失败: {str(e)}"}), 500


@batch_category_bp.route("/task", methods=["DELETE"])
def clear_task():
    """清理任务状态"""
    try:
        with task_lock:
            if current_task["status"] in [TaskStatus.RUNNING, TaskStatus.APPLYING]:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "无法清理正在运行的任务，请先停止任务",
                        }
                    ),
                    400,
                )

            reset_task()

        return jsonify({"success": True, "message": "任务结果已清理，系统已重置"})

    except Exception as e:
        logging.error(f"清理任务失败: {str(e)}")
        return jsonify({"success": False, "message": f"清理任务失败: {str(e)}"}), 500


def _process_batch_task(get_app_func, batch_size):
    """后台处理批量任务"""
    global current_task

    app = get_app_func()
    with app.app_context():
        try:
            # 获取所有有中文名称的商品
            items = Item.query.filter(Item.name_zh.isnot(None)).all()

            # 调用通用处理函数
            _process_items_batch(items, batch_size, is_continue=False)

        except Exception as e:
            logging.error(f"批量任务处理失败: {str(e)}")
            with task_lock:
                current_task["status"] = TaskStatus.FAILED
                current_task["error_message"] = str(e)


def _continue_batch_task(get_app_func, remaining_items, batch_size):
    """继续处理剩余商品的后台任务"""
    global current_task

    app = get_app_func()
    with app.app_context():
        try:
            # 调用通用处理函数
            _process_items_batch(remaining_items, batch_size, is_continue=True)

        except Exception as e:
            logging.error(f"继续批量任务处理失败: {str(e)}")
            with task_lock:
                current_task["status"] = TaskStatus.FAILED
                current_task["error_message"] = str(e)


def _process_items_batch(items, batch_size, is_continue=False):
    """通用商品批量处理函数"""
    global current_task

    try:
        if not is_continue:
            # 新任务，设置总数
            with task_lock:
                current_task["total_items"] = len(items)
                current_task["total_batches"] = (
                    len(items) + batch_size - 1
                ) // batch_size
        else:
            # 继续任务，更新总数
            original_processed = current_task.get("processed_items", 0)
            with task_lock:
                current_task["total_items"] = original_processed + len(items)
                additional_batches = (len(items) + batch_size - 1) // batch_size
                current_task["total_batches"] += additional_batches

        ai_service = AIService()

        # 分批处理
        for batch_idx in range(0, len(items), batch_size):
            # 检查是否需要停止
            with task_lock:
                if current_task["status"] == TaskStatus.STOPPED:
                    return

            batch_items = items[batch_idx : batch_idx + batch_size]

            # 计算当前批次索引
            if is_continue:
                original_batches = current_task.get("processed_items", 0) // batch_size
                batch_index = original_batches + (batch_idx // batch_size)
            else:
                batch_index = batch_idx // batch_size

            with task_lock:
                current_task["current_batch_index"] = batch_index

            # 准备批量数据
            items_for_ai = []
            for item in batch_items:
                items_for_ai.append(
                    {
                        "id": item.id,
                        "chinese_name": item.name_zh or "",
                        "japanese_name": item.name_ja or "",
                    }
                )

            # 处理当前批次
            batch_success = _process_single_batch(ai_service, items_for_ai, batch_items)

            # 如果批次处理失败，记录但继续处理下一批次
            if not batch_success:
                logging.warning(f"批次 {batch_index} 处理失败，继续处理下一批次")

            # 更新处理进度
            with task_lock:
                current_task["processed_items"] += len(batch_items)

            # 避免过快处理，给AI服务一些喘息时间
            time.sleep(1)

        # 任务完成
        with task_lock:
            current_task["status"] = TaskStatus.COMPLETED
            current_task["results_ready"] = True

    except Exception as e:
        logging.error(f"商品批量处理失败: {str(e)}")
        with task_lock:
            current_task["status"] = TaskStatus.FAILED
            current_task["error_message"] = str(e)


def _process_single_batch(ai_service, items_for_ai, batch_items):
    """处理单个批次的商品"""
    global current_task

    try:
        # 批量调用AI进行分类
        ai_result = ai_service.categorize_items_batch(items_for_ai)

        if ai_result and ai_result.get("success"):
            ai_results = ai_result.get("results", [])

            # 处理AI返回的结果
            for ai_item_result in ai_results:
                _process_single_item_result(ai_item_result, batch_items)

            # 处理没有返回结果的商品（AI可能遗漏了一些）
            returned_item_ids = {result.get("item_id") for result in ai_results}
            for item in batch_items:
                if item.id not in returned_item_ids:
                    logging.warning(f"AI未返回商品 {item.id} 的分类结果")
                    with task_lock:
                        current_task["failed_count"] += 1

            return True
        else:
            # 整个批次失败，但不应该停止整个任务
            error_msg = (
                ai_result.get("error", "AI处理失败") if ai_result else "AI返回空结果"
            )
            logging.warning(f"AI批量分类失败: {error_msg}")

            with task_lock:
                current_task["failed_count"] += len(batch_items)

            return False

    except Exception as e:
        logging.error(f"处理批次失败: {str(e)}")
        with task_lock:
            current_task["failed_count"] += len(batch_items)
        return False


def _process_single_item_result(ai_item_result, batch_items):
    """处理单个商品的AI分类结果"""
    global current_task

    try:
        item_id = ai_item_result.get("item_id")
        new_category_id = ai_item_result.get("category_id")
        new_category_name = ai_item_result.get("category_name", "")
        reason = ai_item_result.get("reason", "")

        # 找到对应的商品
        item = next((item for item in batch_items if item.id == item_id), None)
        if not item:
            logging.warning(f"未找到ID为 {item_id} 的商品")
            with task_lock:
                current_task["failed_count"] += 1
            return

        # 验证新分类是否存在
        new_category = Category.query.get(new_category_id) if new_category_id else None
        if not new_category:
            logging.warning(f"商品 {item_id} 的分类ID {new_category_id} 不存在")
            with task_lock:
                current_task["failed_count"] += 1
            return

        old_category_name = item.category.name if item.category else "未分类"

        # 如果分类有变化，记录结果
        if new_category.id != item.category_id:
            result_item = {
                "item_id": item.id,
                "item_name": item.name_zh,
                "old_category": old_category_name,
                "new_category": new_category.name,
                "new_category_id": new_category.id,
                "reason": reason,
                "is_applied": False,
            }

            with task_lock:
                current_task["results"].append(result_item)
                current_task["success_count"] += 1
        else:
            # 分类无变化，跳过
            with task_lock:
                current_task["skipped_count"] += 1

    except Exception as e:
        logging.error(
            f"处理商品 {ai_item_result.get('item_id', 'unknown')} 结果失败: {str(e)}"
        )
        with task_lock:
            current_task["failed_count"] += 1


def _apply_results_task(get_app_func, scope, batch_index):
    """后台应用结果任务"""
    global current_task

    app = get_app_func()
    with app.app_context():
        try:
            results_to_apply = []

            with task_lock:
                if scope == "all":
                    results_to_apply = [
                        r for r in current_task["results"] if not r["is_applied"]
                    ]
                else:  # batch
                    start_idx = batch_index * current_task["batch_size"]
                    end_idx = start_idx + current_task["batch_size"]
                    results_to_apply = [
                        r
                        for r in current_task["results"][start_idx:end_idx]
                        if not r["is_applied"]
                    ]

            # 应用变更
            for result in results_to_apply:
                # 检查是否需要停止
                with task_lock:
                    if current_task["status"] == TaskStatus.STOPPED:
                        return

                try:
                    item = Item.query.get(result["item_id"])
                    if item:
                        item.category_id = result["new_category_id"]
                        db.session.commit()

                        # 更新结果状态
                        result["is_applied"] = True

                        with task_lock:
                            current_task["applied_count"] += 1

                except Exception as e:
                    logging.error(f"应用商品 {result['item_id']} 分类失败: {str(e)}")
                    continue

            # 应用完成
            with task_lock:
                current_task["status"] = TaskStatus.COMPLETED

        except Exception as e:
            logging.error(f"应用结果任务失败: {str(e)}")
            with task_lock:
                current_task["status"] = TaskStatus.FAILED
                current_task["error_message"] = str(e)
