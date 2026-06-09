# -*- coding: utf-8 -*-
"""
个人碎片数据管理系统 —— 后端入口
启动: python main.py
"""
import logging
import sys

from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from db import init_tables, test_connection
from routes import register_blueprints

# ── 日志配置 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if Config.DEBUG else logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_MIMETYPE"] = "application/json; charset=utf-8"

    # CORS
    CORS(
        app,
        resources={r"/*": {"origins": Config.CORS_ORIGINS}},
        supports_credentials=False,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers="*",
    )

    # 注册所有蓝图
    register_blueprints(app)

    # ── 系统路由 ────────────────────────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health():
        db_status = test_connection()
        return jsonify({
            "status": "ok",
            "service": "个人碎片数据管理系统",
            "version": "2.0.0",
            "database": db_status,
        })

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "service": "Fragment Data Management API",
            "version": "2.0.0",
            "endpoints": {
                "health": "GET /health",
                "workflow_list": "GET /api/workflow/list",
                "workflow_run": "POST /api/workflow/run",
                "workflow_test": "GET /api/workflow/test",
                "records_list": "GET /api/records",
                "records_create": "POST /api/records",
                "history_sessions": "GET /api/history/sessions",
                "stats_overview": "GET /api/stats/overview",
            },
        })

    # 保留旧接口地址兼容性（/execute → /api/records/execute）
    @app.route("/execute", methods=["POST"])
    def execute_compat():
        from flask import redirect
        return redirect("/api/records/execute", code=307)

    # 保留旧工作流地址兼容性（/run_workflow → /api/workflow/run）
    @app.route("/run_workflow", methods=["POST"])
    def run_workflow_compat():
        from flask import redirect
        return redirect("/api/workflow/run", code=307)

    # ── 全局错误处理 ─────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "接口不存在", "path": str(e)}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "请求方法不允许"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("未处理的服务器异常")
        return jsonify({"error": "服务器内部错误"}), 500

    return app


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  个人碎片数据管理系统 v2.0  正在启动...")
    logger.info("=" * 60)

    # 尝试初始化数据库表
    logger.info("正在初始化数据库表结构...")
    init_tables()

    app = create_app()

    logger.info("服务已启动：http://%s:%s", Config.HOST, Config.PORT)
    logger.info("健康检查：http://%s:%s/health", Config.HOST, Config.PORT)
    logger.info("API文档（路由列表）：http://%s:%s/", Config.HOST, Config.PORT)

    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=True,
        use_reloader=False,
    )
