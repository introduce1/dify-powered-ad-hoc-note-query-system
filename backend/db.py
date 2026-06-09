# -*- coding: utf-8 -*-
"""
数据库连接管理模块
- 提供 get_connection() 获取连接
- 提供 query() / execute() 便捷封装
- 自动重连机制
"""
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

import pymysql
import pymysql.cursors

from config import Config

logger = logging.getLogger(__name__)


def _build_conn_kwargs() -> dict:
    cfg = Config.get_db_config()
    cfg["cursorclass"] = pymysql.cursors.DictCursor
    return cfg


def get_connection() -> pymysql.Connection:
    """获取一个新的数据库连接（调用方负责关闭）"""
    try:
        conn = pymysql.connect(**_build_conn_kwargs())
        return conn
    except pymysql.MySQLError as e:
        logger.error("数据库连接失败: %s", e)
        raise


@contextmanager
def db_conn():
    """上下文管理器，自动提交/回滚并关闭连接"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql: str, args: tuple = ()) -> List[Dict[str, Any]]:
    """执行 SELECT，返回 dict 列表"""
    with db_conn() as conn:
        with conn.cursor() as cur:
            if args:
                cur.execute(sql, args)
            else:
                cur.execute(sql)
            return cur.fetchall()


def query_one(sql: str, args: tuple = ()) -> Optional[Dict[str, Any]]:
    """执行 SELECT，返回单行 dict 或 None"""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchone()


def execute(sql: str, args: tuple = ()) -> int:
    """执行 INSERT / UPDATE / DELETE，返回受影响行数"""
    with db_conn() as conn:
        with conn.cursor() as cur:
            if args:
                affected = cur.execute(sql, args)
            else:
                affected = cur.execute(sql)
            return affected


def execute_lastrowid(sql: str, args: tuple = ()) -> int:
    """执行 INSERT，返回新插入行的自增 ID"""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.lastrowid


def executemany(sql: str, args_list: List[tuple]) -> int:
    """批量执行，返回受影响行数"""
    with db_conn() as conn:
        with conn.cursor() as cur:
            affected = cur.executemany(sql, args_list)
            return affected


# ── 初始化建表（首次运行自动创建缺失的表） ──────────────────────────────

_INIT_SQL = [
    # 碎片记录表（原有）
    """
    CREATE TABLE IF NOT EXISTS record (
        id          BIGINT AUTO_INCREMENT PRIMARY KEY,
        content     TEXT         NOT NULL,
        rec_type    VARCHAR(64)  DEFAULT '用户输入碎片',
        emp_id      VARCHAR(32)  DEFAULT '',
        product_code VARCHAR(64) DEFAULT '',
        create_time DATETIME     DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        is_deleted  TINYINT(1)   DEFAULT 0,
        INDEX idx_emp_id (emp_id),
        INDEX idx_rec_type (rec_type),
        INDEX idx_create_time (create_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='碎片记录表'
    """,

    # 随记随查主表（新规范，统一记录查询）
    """
    CREATE TABLE IF NOT EXISTS zhihiku (
        id          BIGINT AUTO_INCREMENT PRIMARY KEY,
        content     TEXT         NOT NULL,
        rec_type    VARCHAR(64)  DEFAULT '用户输入碎片',
        emp_id      VARCHAR(32)  DEFAULT '',
        product_code VARCHAR(64) DEFAULT '',
        create_time DATETIME     DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        is_deleted  TINYINT(1)   DEFAULT 0,
        INDEX idx_emp_id (emp_id),
        INDEX idx_rec_type (rec_type),
        INDEX idx_create_time (create_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='随记随查主表'
    """,

    # 兼容迁移：将旧 record 数据同步到 zhihiku（幂等）
    """
    INSERT INTO zhihiku (id, content, rec_type, emp_id, product_code, create_time, update_time, is_deleted)
    SELECT r.id, r.content, r.rec_type, r.emp_id, r.product_code, r.create_time, r.update_time, r.is_deleted
    FROM record r
    ON DUPLICATE KEY UPDATE
        content = VALUES(content),
        rec_type = VALUES(rec_type),
        emp_id = VALUES(emp_id),
        product_code = VALUES(product_code),
        create_time = VALUES(create_time),
        update_time = VALUES(update_time),
        is_deleted = VALUES(is_deleted)
    """,

    # 聊天会话表（新增）
    """
    CREATE TABLE IF NOT EXISTS chat_session (
        id            BIGINT AUTO_INCREMENT PRIMARY KEY,
        session_name  VARCHAR(200) DEFAULT '新对话',
        workflow_type VARCHAR(32)  DEFAULT 'suijisuicha',
        emp_id        VARCHAR(32)  DEFAULT '',
        msg_count     INT          DEFAULT 0,
        create_time   DATETIME     DEFAULT CURRENT_TIMESTAMP,
        update_time   DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        is_deleted    TINYINT(1)   DEFAULT 0,
        INDEX idx_emp_id (emp_id),
        INDEX idx_workflow (workflow_type),
        INDEX idx_create_time (create_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='聊天会话表'
    """,

    # 聊天消息表（新增）
    """
    CREATE TABLE IF NOT EXISTS chat_message (
        id          BIGINT AUTO_INCREMENT PRIMARY KEY,
        session_id  BIGINT       NOT NULL,
        role        VARCHAR(8)   DEFAULT 'user',
        content     TEXT         NOT NULL,
        raw_text    TEXT,
        create_time DATETIME     DEFAULT CURRENT_TIMESTAMP,
        is_favorite TINYINT(1)   DEFAULT 0,
        INDEX idx_session_id (session_id),
        INDEX idx_role (role),
        INDEX idx_create_time (create_time),
        FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='聊天消息表'
    """,

    # 查询统计表（新增）
    """
    CREATE TABLE IF NOT EXISTS query_stat (
        id            BIGINT AUTO_INCREMENT PRIMARY KEY,
        workflow_type VARCHAR(32)  NOT NULL,
        query_text    TEXT,
        emp_id        VARCHAR(32)  DEFAULT '',
        duration_ms   INT          DEFAULT 0,
        success       TINYINT(1)   DEFAULT 1,
        create_time   DATETIME     DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_workflow (workflow_type),
        INDEX idx_emp_id (emp_id),
        INDEX idx_create_time (create_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='查询统计表'
    """,
]


def init_tables():
    """首次运行时自动创建所有表（已有表不影响）"""
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                for sql in _INIT_SQL:
                    cur.execute(sql.strip())
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.warning("数据库表初始化失败（可能数据库尚未启动）: %s", e)


def test_connection() -> dict:
    """测试数据库连接，返回状态信息"""
    try:
        row = query_one("SELECT VERSION() AS version, NOW() AS server_time")
        return {"status": "ok", "version": row["version"], "server_time": str(row["server_time"])}
    except Exception as e:
        return {"status": "error", "message": str(e)}
