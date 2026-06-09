# -*- coding: utf-8 -*-
"""
碎片记录 CRUD 路由
- GET    /api/records          —— 分页列表（支持 keyword、rec_type、emp_id 过滤）
- POST   /api/records          —— 新增记录
- GET    /api/records/<id>     —— 获取单条
- PUT    /api/records/<id>     —— 更新记录
- DELETE /api/records/<id>     —— 软删除
- POST   /api/records/bulk_delete —— 批量软删除
- GET    /api/records/types    —— 获取所有记录类型枚举
- POST   /api/execute          —— 兼容旧接口（直接执行 SQL，支持 MySQL 和 SQL Server）
"""
import logging
import re
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request

from config import Config
from db import execute, execute_lastrowid, query, query_one

logger = logging.getLogger(__name__)
records_bp = Blueprint("records", __name__)
TABLE_NAME = "zhihiku"
WORKFLOW_ALLOWED_TABLES = {
    "suijisuicha": {
        "zhihiku",
    },
    "duolunduihua": {
        "pm_project",
        "pm_wbsnode",
        "pm_contract",
        "pm_contractgathering",
        "sf_org_department",
        "sf_org_user",
        "lz_misdepartment",
        "lz_misdepartmentuser",
        "r_dynamicroleuser",
        "cod_fileinfo",
        "choose_by_jd",
        "wf_his_instance",
    },
    "shengchanjilu": {
        "drawing_record",
        "production_value",
        "production_plan",
        "work_hours",
        "project_progress",
        "pm_wbsnode",
        "sf_org_department",
        "sf_org_user",
    },
}


def _normalize_table_name(name: str) -> str:
    raw = (name or "").strip().strip("`").strip('"').strip("'")
    if "." in raw:
        raw = raw.split(".")[-1]
    return raw.strip().strip("`").strip('"').strip("'").lower()


def _extract_sql_tables(sql: str) -> set[str]:
    tables: set[str] = set()
    patterns = [
        r"\bINSERT\s+INTO\s+([`\"\w\.]+)",
        r"\bFROM\s+([`\"\w\.]+)",
        r"\bJOIN\s+([`\"\w\.]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, sql or "", flags=re.IGNORECASE):
            table_name = _normalize_table_name(match.group(1))
            if table_name:
                tables.add(table_name)
    return tables


def _resolve_allowed_tables(workflow_type: str) -> set[str]:
    workflow = (workflow_type or "").strip().lower()
    if workflow and workflow in WORKFLOW_ALLOWED_TABLES:
        return set(WORKFLOW_ALLOWED_TABLES[workflow])

    allowed: set[str] = set()
    for tables in WORKFLOW_ALLOWED_TABLES.values():
        allowed.update(tables)
    return allowed


def _extract_unknown_column(error_text: str) -> tuple[str, str]:
    """
    解析 MySQL Unknown column 报错并返回 (table_name, column_name)。
    例如: Unknown column 'project_progress.target_projects' in 'field list'
    """
    m = re.search(r"Unknown column '([^']+)'", error_text or "", flags=re.IGNORECASE)
    if not m:
        return "", ""
    full = m.group(1).strip()
    if "." not in full:
        return "", full
    table_name, column_name = full.split(".", 1)
    return _normalize_table_name(table_name), column_name.strip()


def _load_table_columns(table_name: str) -> list[str]:
    if not table_name:
        return []
    try:
        rows = query(f"SHOW COLUMNS FROM `{table_name}`", ())
        return [str(r.get("Field")) for r in rows if r.get("Field")]
    except Exception:
        return []


def _format_select_exception(sql: str, err: Exception) -> Optional[tuple[dict, int]]:
    """
    识别常见 SQL 错误并返回可读信息，未识别则返回 None。
    """
    table_name, column_name = _extract_unknown_column(str(err))
    if not column_name:
        return None

    # 报错里没有带表名时，且 SQL 仅涉及一张表，尝试补全
    if not table_name:
        tables = sorted(_extract_sql_tables(sql))
        if len(tables) == 1:
            table_name = tables[0]

    if table_name:
        columns = _load_table_columns(table_name)
        if columns:
            message = (
                f"SQL 字段不存在: {table_name}.{column_name}。"
                f"`{table_name}` 可用字段: {', '.join(columns)}"
            )
        else:
            message = f"SQL 字段不存在: {table_name}.{column_name}"
    else:
        message = f"SQL 字段不存在: {column_name}"

    return {"message": message, "error_type": "unknown_column"}, 400


def _paginate(page: int, page_size: int):
    page = max(1, page)
    page_size = min(max(1, page_size), Config.MAX_PAGE_SIZE)
    offset = (page - 1) * page_size
    return page, page_size, offset


# ── 列表 & 搜索 ──────────────────────────────────────────────────────────────

@records_bp.route("", methods=["GET"])
def list_records():
    """分页查询记录，支持关键字搜索和类型过滤"""
    keyword = (request.args.get("keyword") or "").strip()
    rec_type = (request.args.get("rec_type") or "").strip()
    emp_id = (request.args.get("emp_id") or "").strip()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", Config.DEFAULT_PAGE_SIZE))

    page, page_size, offset = _paginate(page, page_size)

    conditions = ["is_deleted = 0"]
    params: list = []

    if keyword:
        conditions.append("content LIKE %s")
        params.append(f"%{keyword}%")
    if rec_type:
        conditions.append("rec_type = %s")
        params.append(rec_type)
    if emp_id:
        conditions.append("emp_id = %s")
        params.append(emp_id)

    where = " AND ".join(conditions)

    count_row = query_one(f"SELECT COUNT(*) AS total FROM {TABLE_NAME} WHERE {where}", tuple(params))
    total = count_row["total"] if count_row else 0

    params_page = params + [page_size, offset]
    rows = query(
        f"SELECT id, content, rec_type, emp_id, product_code, "
        f"create_time, update_time FROM {TABLE_NAME} WHERE {where} "
        f"ORDER BY create_time DESC LIMIT %s OFFSET %s",
        tuple(params_page),
    )

    for row in rows:
        row["create_time"] = str(row["create_time"])
        row["update_time"] = str(row["update_time"])

    return jsonify({
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "data": rows,
    })


@records_bp.route("/types", methods=["GET"])
def get_record_types():
    """获取所有已使用的记录类型"""
    rows = query(
        f"SELECT rec_type, COUNT(*) AS cnt FROM {TABLE_NAME} "
        "WHERE is_deleted = 0 GROUP BY rec_type ORDER BY cnt DESC"
    )
    return jsonify({"types": [{"rec_type": r["rec_type"], "count": r["cnt"]} for r in rows]})


# ── 单条 CRUD ─────────────────────────────────────────────────────────────────

@records_bp.route("", methods=["POST"])
def create_record():
    """新增一条碎片记录"""
    body = request.get_json(force=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"message": "content 不能为空"}), 400

    rec_type = body.get("rec_type", "用户输入碎片")
    emp_id = body.get("emp_id", "001")
    product_code = body.get("product_code", "")

    try:
        new_id = execute_lastrowid(
            f"INSERT INTO {TABLE_NAME} (content, rec_type, emp_id, product_code) "
            "VALUES (%s, %s, %s, %s)",
            (content, rec_type, emp_id, product_code),
        )
        row = query_one(f"SELECT * FROM {TABLE_NAME} WHERE id = %s", (new_id,))
        if row:
            row["create_time"] = str(row["create_time"])
            row["update_time"] = str(row["update_time"])
        return jsonify({"message": "保存成功", "data": row}), 201
    except Exception as e:
        logger.exception("create_record 失败")
        return jsonify({"message": f"保存失败: {e}"}), 500


@records_bp.route("/<int:record_id>", methods=["GET"])
def get_record(record_id: int):
    """获取单条记录详情"""
    row = query_one(
        f"SELECT * FROM {TABLE_NAME} WHERE id = %s AND is_deleted = 0",
        (record_id,),
    )
    if not row:
        return jsonify({"message": "记录不存在"}), 404
    row["create_time"] = str(row["create_time"])
    row["update_time"] = str(row["update_time"])
    return jsonify({"data": row})


@records_bp.route("/<int:record_id>", methods=["PUT"])
def update_record(record_id: int):
    """更新记录内容或类型"""
    body = request.get_json(force=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"message": "content 不能为空"}), 400

    rec_type = body.get("rec_type")
    emp_id = body.get("emp_id")
    product_code = body.get("product_code")

    # 动态构建 SET 子句
    sets, params = ["content = %s"], [content]
    if rec_type is not None:
        sets.append("rec_type = %s")
        params.append(rec_type)
    if emp_id is not None:
        sets.append("emp_id = %s")
        params.append(emp_id)
    if product_code is not None:
        sets.append("product_code = %s")
        params.append(product_code)

    params.append(record_id)

    try:
        affected = execute(
            f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE id = %s AND is_deleted = 0",
            tuple(params),
        )
        if affected == 0:
            return jsonify({"message": "记录不存在或未作变更"}), 404
        return jsonify({"message": "更新成功"})
    except Exception as e:
        logger.exception("update_record 失败")
        return jsonify({"message": f"更新失败: {e}"}), 500


@records_bp.route("/<int:record_id>", methods=["DELETE"])
def delete_record(record_id: int):
    """软删除单条记录"""
    try:
        affected = execute(
            f"UPDATE {TABLE_NAME} SET is_deleted = 1 WHERE id = %s AND is_deleted = 0",
            (record_id,),
        )
        if affected == 0:
            return jsonify({"message": "记录不存在"}), 404
        return jsonify({"message": "删除成功"})
    except Exception as e:
        logger.exception("delete_record 失败")
        return jsonify({"message": f"删除失败: {e}"}), 500


@records_bp.route("/bulk_delete", methods=["POST"])
def bulk_delete():
    """批量软删除（POST body: {"ids": [1,2,3]}）"""
    body = request.get_json(force=True) or {}
    ids = body.get("ids") or []
    if not ids or not all(isinstance(i, int) for i in ids):
        return jsonify({"message": "ids 必须为整数数组"}), 400

    placeholders = ",".join(["%s"] * len(ids))
    try:
        affected = execute(
            f"UPDATE {TABLE_NAME} SET is_deleted = 1 WHERE id IN ({placeholders}) AND is_deleted = 0",
            tuple(ids),
        )
        return jsonify({"message": f"成功删除 {affected} 条记录"})
    except Exception as e:
        logger.exception("bulk_delete 失败")
        return jsonify({"message": f"批量删除失败: {e}"}), 500


# ── 旧接口兼容 ────────────────────────────────────────────────────────────────

@records_bp.route("/execute", methods=["POST"])
def execute_sql_compat():
    """
    兼容旧版前端 /execute 接口。
    支持 INSERT（插入）和 SELECT（查询）语句。
    出于安全考虑，不允许 UPDATE / DELETE / DROP 等危险操作。
    """
    body = request.get_json(force=True) or {}
    # 兼容两种字段名：sql 和 sql_query
    sql: str = (body.get("sql") or body.get("sql_query") or "").strip()
    workflow_type = (body.get("workflow_type") or "").strip()

    # 添加调试日志
    logger.info(f"[execute] 收到请求，body keys: {list(body.keys())}")
    logger.info(f"[execute] SQL 长度: {len(sql)}, 前100字符: {sql[:100] if sql else 'empty'}")

    if not sql:
        logger.warning("[execute] SQL 为空")
        return jsonify({"message": "没有提供 SQL 语句"}), 400

    normalized = sql.upper().lstrip()
    logger.info(f"[execute] SQL 类型: {normalized.split()[0] if normalized else 'unknown'}")
    referenced_tables = _extract_sql_tables(sql)
    allowed_tables = _resolve_allowed_tables(workflow_type)
    blocked_tables = sorted(referenced_tables - allowed_tables)

    if blocked_tables:
        logger.warning(
            "[execute] SQL 被拦截, workflow_type=%s, referenced=%s, blocked=%s",
            workflow_type or "unknown",
            sorted(referenced_tables),
            blocked_tables,
        )
        return jsonify({
            "message": "安全限制：SQL 包含未授权的数据表",
            "workflow_type": workflow_type or "unknown",
            "blocked_tables": blocked_tables,
        }), 403

    # 允许 INSERT 和 SELECT
    if normalized.startswith("INSERT"):
        try:
            execute(sql, ())
            logger.info("[execute] INSERT 成功")
            return jsonify({"message": "保存完成"})
        except Exception as e:
            logger.exception("execute_sql_compat INSERT 失败")
            return jsonify({"message": f"保存过程中发生错误：{e}"}), 500

    elif normalized.startswith("SELECT"):
        try:
            logger.info(
                "[execute] 使用 MySQL 查询, workflow_type=%s, tables=%s",
                workflow_type or "unknown",
                sorted(referenced_tables),
            )
            rows = query(sql, ())

            # 转换日期时间为字符串
            for row in rows:
                for key, value in list(row.items()):
                    if hasattr(value, 'isoformat'):
                        row[key] = value.isoformat()

            logger.info(f"[execute] SELECT 成功，返回 {len(rows)} 行")
            return jsonify({"message": "查询成功", "data": rows})
        except Exception as e:
            logger.exception("execute_sql_compat SELECT 失败")
            formatted = _format_select_exception(sql, e)
            if formatted:
                body, status = formatted
                return jsonify(body), status
            return jsonify({"message": f"查询过程中发生错误：{e}"}), 500

    else:
        logger.warning(f"[execute] 不支持的 SQL 类型: {normalized[:50]}")
        return jsonify({"message": "安全限制：仅允许 INSERT 和 SELECT 语句"}), 403
