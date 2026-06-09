# -*- coding: utf-8 -*-
from flask import Blueprint

from .workflow import workflow_bp
from .records import records_bp
from .history import history_bp
from .stats import stats_bp


def register_blueprints(app):
    """将所有蓝图注册到 Flask app"""
    app.register_blueprint(workflow_bp, url_prefix="/api/workflow")
    app.register_blueprint(records_bp,  url_prefix="/api/records")
    app.register_blueprint(history_bp,  url_prefix="/api/history")
    app.register_blueprint(stats_bp,    url_prefix="/api/stats")
