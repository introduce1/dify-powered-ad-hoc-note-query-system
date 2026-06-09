# -*- coding: utf-8 -*-
"""
聊天历史管理路由（新功能）
- GET    /api/history/sessions               —— 分页获取会话列表
- POST   /api/history/sessions               —— 新建会话
- GET    /api/history/sessions/<id>          —— 获取会话及消息
- PUT    /api/history/sessions/<id>          —— 重命名会话
- DELETE /api/history/sessions/<id>          —— 删除会话（级联删消息）
- POST   /api/history/sessions/<id>/messages —— 追加消息到会话
- PUT    /api/history/messages/<id>/favorite —— 切换消息收藏状态
- GET    /api/history/favorites              —— 获取所有收藏消息
- POST   /api/history/sessions/<id>/export  —— 导出会话（JSON / markdown）
"""
import json
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from config import Config
from db import db_conn, execute, execute_lastrowid, query, query_one

logger = logging.getLogger(__name__)
history_bp = Blueprint("history", __name__)


def _fmt(row: dict) -> dict:
    """将 datetime 对象转为字符串，方便 JSON 序列化"""
    for k in ("create_time", "update_time"):
        if k in row and row[k] is not None:
            row[k] = str(row[k])
    return row


# ── 会话 CRUD ────────────────────────────────────────────────────────────────

@history_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """分页获取会话列表"""
    emp_id = (request.args.get("emp_id") or "").strip()
    workflow = (request.args.get("workflow_type") or "").strip()
    keyword = (request.args.get("keyword") or "").strip()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", Config.DEFAULT_PAGE_SIZE))
    page = max(1, page)
    page_size = min(max(1, page_size), Config.MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    conditions = ["is_deleted = 0"]
    params: list = []

    if emp_id:
        conditions.append("emp_id = %s")
        params.append(emp_id)
    if workflow:
        conditions.append("workflow_type = %s")
        params.append(workflow)
    if keyword:
        conditions.append("session_name LIKE %s")
        params.append(f"%{keyword}%")

    where = " AND ".join(conditions)
    total_row = query_one(f"SELECT COUNT(*) AS total FROM chat_session WHERE {where}", tuple(params))
    total = total_row["total"] if total_row else 0

    rows = query(
        f"SELECT id, session_name, workflow_type, emp_id, msg_count, create_time, update_time "
        f"FROM chat_session WHERE {where} ORDER BY update_time DESC LIMIT %s OFFSET %s",
        tuple(params + [page_size, offset]),
    )

    return jsonify({
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [_fmt(r) for r in rows],
    })


@history_bp.route("/sessions", methods=["POST"])
def create_session():
    """新建一个空会话"""
    body = request.get_json(force=True) or {}
    name = (body.get("session_name") or "新对话").strip()
    workflow = body.get("workflow_type", "suijisuicha")
    emp_id = body.get("emp_id", "001")

    try:
        new_id = execute_lastrowid(
            "INSERT INTO chat_session (session_name, workflow_type, emp_id) VALUES (%s, %s, %s)",
            (name, workflow, emp_id),
        )
        row = query_one("SELECT * FROM chat_session WHERE id = %s", (new_id,))
        return jsonify({"message": "创建成功", "data": _fmt(row)}), 201
    except Exception as e:
        logger.exception("create_session 失败")
        return jsonify({"message": f"创建失败: {e}"}), 500


@history_bp.route("/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id: int):
    """获取会话基本信息及所有消息"""
    session = query_one(
        "SELECT * FROM chat_session WHERE id = %s AND is_deleted = 0",
        (session_id,),
    )
    if not session:
        return jsonify({"message": "会话不存在"}), 404

    messages = query(
        "SELECT id, role, content, raw_text, is_favorite, create_time "
        "FROM chat_message WHERE session_id = %s ORDER BY create_time ASC",
        (session_id,),
    )

    return jsonify({
        "session": _fmt(session),
        "messages": [_fmt(m) for m in messages],
    })


@history_bp.route("/sessions/<int:session_id>", methods=["PUT"])
def rename_session(session_id: int):
    """重命名会话"""
    body = request.get_json(force=True) or {}
    name = (body.get("session_name") or "").strip()
    if not name:
        return jsonify({"message": "session_name 不能为空"}), 400

    affected = execute(
        "UPDATE chat_session SET session_name = %s WHERE id = %s AND is_deleted = 0",
        (name, session_id),
    )
    if affected == 0:
        return jsonify({"message": "会话不存在"}), 404
    return jsonify({"message": "重命名成功"})


@history_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id: int):
    """软删除会话（消息通过外键级联物理删除）"""
    affected = execute(
        "UPDATE chat_session SET is_deleted = 1 WHERE id = %s AND is_deleted = 0",
        (session_id,),
    )
    if affected == 0:
        return jsonify({"message": "会话不存在"}), 404
    return jsonify({"message": "删除成功"})


# ── 消息操作 ─────────────────────────────────────────────────────────────────

@history_bp.route("/sessions/<int:session_id>/messages", methods=["POST"])
def add_message(session_id: int):
    """向指定会话追加一条消息"""
    session = query_one(
        "SELECT id FROM chat_session WHERE id = %s AND is_deleted = 0",
        (session_id,),
    )
    if not session:
        return jsonify({"message": "会话不存在"}), 404

    body = request.get_json(force=True) or {}
    role = body.get("role", "user")
    content = (body.get("content") or "").strip()
    raw_text = (body.get("raw_text") or content).strip()

    if not content:
        return jsonify({"message": "content 不能为空"}), 400
    if role not in ("user", "ai"):
        return jsonify({"message": "role 必须是 user 或 ai"}), 400

    try:
        msg_id = execute_lastrowid(
            "INSERT INTO chat_message (session_id, role, content, raw_text) VALUES (%s, %s, %s, %s)",
            (session_id, role, content, raw_text),
        )
        # 更新会话消息计数和最后活跃时间
        execute(
            "UPDATE chat_session SET msg_count = msg_count + 1, update_time = NOW() WHERE id = %s",
            (session_id,),
        )
        msg = query_one("SELECT * FROM chat_message WHERE id = %s", (msg_id,))
        return jsonify({"message": "添加成功", "data": _fmt(msg)}), 201
    except Exception as e:
        logger.exception("add_message 失败")
        return jsonify({"message": f"添加失败: {e}"}), 500


@history_bp.route("/messages/<int:msg_id>/favorite", methods=["PUT"])
def toggle_favorite(msg_id: int):
    """切换消息的收藏状态"""
    msg = query_one("SELECT id, is_favorite FROM chat_message WHERE id = %s", (msg_id,))
    if not msg:
        return jsonify({"message": "消息不存在"}), 404

    new_state = 0 if msg["is_favorite"] else 1
    execute("UPDATE chat_message SET is_favorite = %s WHERE id = %s", (new_state, msg_id))
    action = "已收藏" if new_state else "已取消收藏"
    return jsonify({"message": action, "is_favorite": new_state})


@history_bp.route("/favorites", methods=["GET"])
def list_favorites():
    """获取当前用户所有已收藏的消息"""
    emp_id = (request.args.get("emp_id") or "001").strip()
    rows = query(
        "SELECT m.id, m.session_id, m.role, m.content, m.raw_text, m.create_time, "
        "       s.session_name, s.workflow_type "
        "FROM chat_message m "
        "JOIN chat_session s ON m.session_id = s.id "
        "WHERE m.is_favorite = 1 AND s.emp_id = %s AND s.is_deleted = 0 "
        "ORDER BY m.create_time DESC",
        (emp_id,),
    )
    return jsonify({"data": [_fmt(r) for r in rows]})


# ── 导出 ─────────────────────────────────────────────────────────────────────

@history_bp.route("/sessions/<int:session_id>/export", methods=["POST"])
def export_session(session_id: int):
    """导出会话为 JSON 或 Markdown 格式"""
    body = request.get_json(force=True) or {}
    fmt = body.get("format", "json").lower()

    session = query_one(
        "SELECT * FROM chat_session WHERE id = %s AND is_deleted = 0",
        (session_id,),
    )
    if not session:
        return jsonify({"message": "会话不存在"}), 404

    messages = query(
        "SELECT role, content, raw_text, create_time FROM chat_message "
        "WHERE session_id = %s ORDER BY create_time ASC",
        (session_id,),
    )

    if fmt == "markdown":
        wf_label = Config.WORKFLOW_CONFIG.get(session["workflow_type"], {}).get("label", session["workflow_type"])
        lines = [
            f"# {session['session_name']}",
            f"> 工作流：{wf_label}  |  创建时间：{session['create_time']}",
            "",
        ]
        for m in messages:
            role_label = "**用户**" if m["role"] == "user" else "**AI**"
            ts = str(m["create_time"])
            lines.append(f"### {role_label} · {ts}")
            lines.append(m["raw_text"] or m["content"])
            lines.append("")

        return jsonify({"format": "markdown", "content": "\n".join(lines)})

    # JSON 格式
    payload = {
        "session": _fmt(dict(session)),
        "messages": [_fmt(dict(m)) for m in messages],
        "exported_at": str(datetime.now()),
    }
    return jsonify({"format": "json", "content": json.dumps(payload, ensure_ascii=False, indent=2)})


# ── 简化接口：直接创建消息记录 ──────────────────────────────────────────────────

@history_bp.route("/messages", methods=["POST"])
def create_message_simple():
    """
    简化的消息创建接口，自动创建或关联会话
    body: { emp_id, workflow_type, query_text, response_text, session_id? }
    """
    body = request.get_json(force=True) or {}
    emp_id = body.get("emp_id", "001")
    workflow_type = body.get("workflow_type", "suijisuicha")
    query_text = (body.get("query_text") or "").strip()
    response_text = (body.get("response_text") or "").strip()
    session_id = body.get("session_id")

    if not query_text:
        return jsonify({"message": "query_text 不能为空"}), 400

    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                active_session_id = None

                # 仅复用“当前用户 + 当前工作流 + 未删除”的会话，避免写入失效会话后历史页不可见
                if session_id:
                    cur.execute(
                        "SELECT id, is_deleted FROM chat_session "
                        "WHERE id = %s AND emp_id = %s AND workflow_type = %s",
                        (session_id, emp_id, workflow_type),
                    )
                    existing = cur.fetchone()
                    if existing and int(existing.get("is_deleted", 0)) == 0:
                        active_session_id = existing["id"]

                # session_id 缺失 / 会话已删除 / 会话不存在时，自动创建新会话
                if not active_session_id:
                    wf_label = Config.WORKFLOW_CONFIG.get(workflow_type, {}).get("label", workflow_type)
                    session_name = f"{wf_label} - {query_text[:20]}"
                    cur.execute(
                        "INSERT INTO chat_session (emp_id, workflow_type, session_name) VALUES (%s, %s, %s)",
                        (emp_id, workflow_type, session_name),
                    )
                    active_session_id = cur.lastrowid

                # 插入用户消息
                cur.execute(
                    "INSERT INTO chat_message (session_id, role, content, raw_text) VALUES (%s, %s, %s, %s)",
                    (active_session_id, "user", query_text, query_text),
                )
                added_count = 1

                # 插入 AI 回复
                if response_text:
                    cur.execute(
                        "INSERT INTO chat_message (session_id, role, content, raw_text) VALUES (%s, %s, %s, %s)",
                        (active_session_id, "ai", response_text, response_text),
                    )
                    added_count += 1

                # 同步更新会话统计与活跃时间
                cur.execute(
                    "UPDATE chat_session SET msg_count = msg_count + %s, update_time = NOW() "
                    "WHERE id = %s",
                    (added_count, active_session_id),
                )

        return jsonify({"message": "保存成功", "session_id": active_session_id}), 201

    except Exception as e:
        logger.exception("create_message_simple 失败")
        return jsonify({"message": f"保存失败: {e}"}), 500

