# -*- coding: utf-8 -*-
"""
数据统计分析路由（新功能）
- GET /api/stats/overview    —— 总览：记录数、会话数、今日查询数
- GET /api/stats/daily       —— 近 N 天每日查询量折线图数据
- GET /api/stats/workflows   —— 各工作流使用占比饼图数据
- GET /api/stats/heatmap     —— 近 12 周活跃热力图数据
- GET /api/stats/top_records —— 最近新增的碎片记录（快速回顾）
- GET /api/stats/keywords    —— 高频关键词（简单词频统计）
"""
import logging
import re
from collections import Counter
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from config import Config
from db import query, query_one

logger = logging.getLogger(__name__)
stats_bp = Blueprint("stats", __name__)
TABLE_NAME = "zhihiku"


# ── 总览 ─────────────────────────────────────────────────────────────────────

@stats_bp.route("/overview", methods=["GET"])
def overview():
    """系统总览统计"""
    emp_id = (request.args.get("emp_id") or "").strip()
    emp_cond = "AND emp_id = %s" if emp_id else ""
    emp_args = (emp_id,) if emp_id else ()

    total_records = (query_one(
        f"SELECT COUNT(*) AS cnt FROM {TABLE_NAME} WHERE is_deleted = 0 {emp_cond}",
        emp_args,
    ) or {}).get("cnt", 0)

    total_sessions = (query_one(
        f"SELECT COUNT(*) AS cnt FROM chat_session WHERE is_deleted = 0 {emp_cond}",
        emp_args,
    ) or {}).get("cnt", 0)

    today_queries = (query_one(
        f"SELECT COUNT(*) AS cnt FROM query_stat "
        f"WHERE DATE(create_time) = CURDATE() {emp_cond}",
        emp_args,
    ) or {}).get("cnt", 0)

    today_records = (query_one(
        f"SELECT COUNT(*) AS cnt FROM {TABLE_NAME} "
        f"WHERE DATE(create_time) = CURDATE() AND is_deleted = 0 {emp_cond}",
        emp_args,
    ) or {}).get("cnt", 0)

    total_messages = (query_one(
        "SELECT COUNT(*) AS cnt FROM chat_message"
    ) or {}).get("cnt", 0)

    total_favorites = (query_one(
        "SELECT COUNT(*) AS cnt FROM chat_message WHERE is_favorite = 1"
    ) or {}).get("cnt", 0)

    return jsonify({
        "total_records": total_records,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_favorites": total_favorites,
        "today_queries": today_queries,
        "today_records": today_records,
    })


# ── 每日趋势 ─────────────────────────────────────────────────────────────────

@stats_bp.route("/daily", methods=["GET"])
def daily_trend():
    """返回近 N 天每日查询量（默认 30 天）"""
    days = min(int(request.args.get("days", 30)), 90)
    emp_id = (request.args.get("emp_id") or "").strip()

    cond = "AND emp_id = %s" if emp_id else ""
    args = (days, emp_id) if emp_id else (days,)

    rows = query(
        f"SELECT DATE(create_time) AS day, COUNT(*) AS cnt "
        f"FROM query_stat "
        f"WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL %s DAY) {cond} "
        f"GROUP BY day ORDER BY day ASC",
        args,
    )

    # 补全缺失日期（值为 0）
    date_map = {str(r["day"]): r["cnt"] for r in rows}
    result = []
    for i in range(days - 1, -1, -1):
        day = str((datetime.now() - timedelta(days=i)).date())
        result.append({"day": day, "count": date_map.get(day, 0)})

    # 同时返回 zhihiku 新增量
    record_rows = query(
        f"SELECT DATE(create_time) AS day, COUNT(*) AS cnt "
        f"FROM {TABLE_NAME} "
        f"WHERE is_deleted = 0 AND create_time >= DATE_SUB(CURDATE(), INTERVAL %s DAY) {cond} "
        f"GROUP BY day ORDER BY day ASC",
        args,
    )
    record_map = {str(r["day"]): r["cnt"] for r in record_rows}
    for item in result:
        item["records"] = record_map.get(item["day"], 0)

    return jsonify({"days": days, "data": result})


# ── 工作流占比 ────────────────────────────────────────────────────────────────

@stats_bp.route("/workflows", methods=["GET"])
def workflow_distribution():
    """各工作流调用占比"""
    emp_id = (request.args.get("emp_id") or "").strip()
    cond = "WHERE emp_id = %s" if emp_id else ""
    args = (emp_id,) if emp_id else ()

    rows = query(
        f"SELECT workflow_type, COUNT(*) AS cnt "
        f"FROM query_stat {cond} "
        f"GROUP BY workflow_type ORDER BY cnt DESC",
        args,
    )

    total = sum(r["cnt"] for r in rows)
    result = []
    for r in rows:
        label = Config.WORKFLOW_CONFIG.get(r["workflow_type"], {}).get("label", r["workflow_type"])
        result.append({
            "workflow_type": r["workflow_type"],
            "label": label,
            "count": r["cnt"],
            "percent": round(r["cnt"] / total * 100, 1) if total > 0 else 0,
        })

    return jsonify({"total": total, "data": result})


# ── 活跃热力图 ────────────────────────────────────────────────────────────────

@stats_bp.route("/heatmap", methods=["GET"])
def activity_heatmap():
    """近 12 周（84天）按日期统计活跃量，供前端热力图使用"""
    emp_id = (request.args.get("emp_id") or "").strip()
    cond = "AND emp_id = %s" if emp_id else ""
    args = (emp_id,) if emp_id else ()

    q_rows = query(
        f"SELECT DATE(create_time) AS day, COUNT(*) AS cnt "
        f"FROM query_stat "
        f"WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL 84 DAY) {cond} "
        f"GROUP BY day",
        args,
    )
    r_rows = query(
        f"SELECT DATE(create_time) AS day, COUNT(*) AS cnt "
        f"FROM {TABLE_NAME} "
        f"WHERE is_deleted = 0 AND create_time >= DATE_SUB(CURDATE(), INTERVAL 84 DAY) {cond} "
        f"GROUP BY day",
        args,
    )

    heat: dict = {}
    for r in q_rows:
        heat[str(r["day"])] = heat.get(str(r["day"]), 0) + r["cnt"]
    for r in r_rows:
        heat[str(r["day"])] = heat.get(str(r["day"]), 0) + r["cnt"]

    result = []
    for i in range(83, -1, -1):
        day = str((datetime.now() - timedelta(days=i)).date())
        result.append({"date": day, "count": heat.get(day, 0)})

    return jsonify({"data": result})


# ── 最新记录 ─────────────────────────────────────────────────────────────────

@stats_bp.route("/top_records", methods=["GET"])
def top_records():
    """最近新增的碎片记录（用于首页快速回顾）"""
    limit = min(int(request.args.get("limit", 10)), 50)
    emp_id = (request.args.get("emp_id") or "").strip()
    cond = "AND emp_id = %s" if emp_id else ""
    args_t = (emp_id, limit) if emp_id else (limit,)

    rows = query(
        f"SELECT id, content, rec_type, emp_id, create_time "
        f"FROM {TABLE_NAME} WHERE is_deleted = 0 {cond} "
        f"ORDER BY create_time DESC LIMIT %s",
        args_t,
    )
    for r in rows:
        r["create_time"] = str(r["create_time"])
        # 内容截断
        if r["content"] and len(r["content"]) > 120:
            r["content_short"] = r["content"][:117] + "…"
        else:
            r["content_short"] = r["content"]

    return jsonify({"data": rows})


# ── 高频关键词 ────────────────────────────────────────────────────────────────

_STOPWORDS = {
    "的", "了", "是", "在", "有", "和", "我", "你", "他", "她", "它",
    "这", "那", "一", "不", "也", "都", "到", "以", "就", "与", "对",
    "为", "但", "如", "及", "等", "而", "其", "可", "并", "从", "于",
    "被", "由", "或", "把", "因", "让", "使", "将",
}


def _tokenize(text: str) -> list:
    """简单中文分词：按非汉字字符切割，过滤停用词和单字"""
    words = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return [w for w in words if w not in _STOPWORDS]


@stats_bp.route("/keywords", methods=["GET"])
def top_keywords():
    """统计 query_stat 近 30 天的高频关键词（Top 20）"""
    emp_id = (request.args.get("emp_id") or "").strip()
    cond = "AND emp_id = %s" if emp_id else ""
    args = (emp_id,) if emp_id else ()

    rows = query(
        f"SELECT query_text FROM query_stat "
        f"WHERE query_text IS NOT NULL AND query_text != '' "
        f"AND create_time >= DATE_SUB(NOW(), INTERVAL 30 DAY) {cond} "
        f"LIMIT 500",
        args,
    )

    counter: Counter = Counter()
    for r in rows:
        tokens = _tokenize(r["query_text"] or "")
        counter.update(tokens)

    top = [{"word": w, "count": c} for w, c in counter.most_common(20)]
    return jsonify({"data": top})
