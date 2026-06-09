# -*- coding: utf-8 -*-
"""
工作流代理路由
- POST /api/workflow/run   —— 运行工作流（SSE 流式返回）
- GET  /api/workflow/list  —— 获取可用工作流列表
- GET  /api/workflow/test  —— 本地流式输出测试
"""
import json
import logging
import ssl
import time
from datetime import datetime

import requests
import urllib3
from flask import Blueprint, Response, jsonify, request
from requests.adapters import HTTPAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SSLAdapter(HTTPAdapter):
    """使用宽松 SSL 设置的适配器，解决部分 HTTPS 连接问题"""
    def init_poolmanager(self, num_pools, maxsize, block=False, **connection_pool_kw):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        connection_pool_kw["ssl_context"] = ctx
        super().init_poolmanager(num_pools, maxsize, block, **connection_pool_kw)

from config import Config
from db import execute

logger = logging.getLogger(__name__)
workflow_bp = Blueprint("workflow", __name__)

# 服务端记忆：{ (emp_id, workflow_type): conversation_id }
# 避免依赖前端正确回传 conversation_id
_conversation_store: dict = {}


# ── 工具函数 ────────────────────────────────────────────────────────────────

def _log(*args):
    if Config.DEBUG_STREAM:
        logger.debug("[SSE] %s", " ".join(str(a) for a in args))


def _preview(s: str, n: int = 120) -> str:
    s = s.replace("\n", "\\n")
    return s[:n] + ("…" if len(s) > n else "")


def extract_json_stream(text: str, start_pos: int = 0):
    """从不完整的流式缓冲区中逐个提取 JSON 对象"""
    objects, decoder = [], json.JSONDecoder()
    pos = start_pos
    n = len(text)
    while pos < n:
        while pos < n and text[pos] not in "{[":
            pos += 1
        if pos >= n:
            break
        try:
            obj, end = decoder.raw_decode(text, pos)
            objects.append(obj)
            pos = end
        except (ValueError, IndexError):
            break
    return objects, pos


def _extract_final_text(data_obj: dict) -> str:
    """从 workflow_finished 事件中提取最终文本（只查已知字段，不做深度扫描）"""
    if not isinstance(data_obj, dict):
        return ""
    try:
        outputs = data_obj.get("outputs") or {}
        if isinstance(outputs, str) and outputs.strip():
            return outputs
        if isinstance(outputs, dict):
            for k in ("text", "result", "answer", "message", "content", "output"):
                v = outputs.get(k)
                if isinstance(v, str) and v.strip():
                    return v

        for k in ("text", "result", "answer", "message", "content"):
            v = data_obj.get(k)
            if isinstance(v, str) and v.strip():
                return v

        return ""
    except Exception:
        return ""

def _stringify_payload(value) -> str:
    """将任意类型的输出转换为可展示文本（布尔/数字不作为文本）"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        return ""
    if isinstance(value, dict):
        if not value:
            return ""
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except Exception:
            return str(value)
    if isinstance(value, list):
        if not value:
            return ""
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except Exception:
            return str(value)
    return ""


def _extract_event_text(obj: dict) -> str:
    """兼容不同 Dify 事件结构，提取文本内容（仅提取真正有意义的文本）"""
    if not isinstance(obj, dict):
        return ""

    data = obj.get("data", {}) or {}

    # 顶层字段（chat-messages 常见 answer）
    for key in ("answer", "text", "message", "content"):
        v = obj.get(key)
        if isinstance(v, str) and len(v.strip()) > 0:
            return v

    # data 子字段
    for key in ("answer", "text", "message", "content"):
        v = data.get(key)
        if isinstance(v, str) and len(v.strip()) > 0:
            return v

    # data.outputs 内的文本字段
    outputs = data.get("outputs")
    if isinstance(outputs, dict):
        for key in ("text", "answer", "result", "message", "content", "output"):
            v = outputs.get(key)
            if isinstance(v, str) and len(v.strip()) > 0:
                return v

    return ""


def _infer_event_type(obj: dict) -> str:
    """当 SSE event 行缺失且 JSON 内无 event 字段时，根据字段特征推断事件类型"""
    if "answer" in obj and "message_id" not in obj.get("metadata", {}):
        if "metadata" in obj and "usage" in (obj.get("metadata") or {}):
            return "message_end"
        return "message"
    data = obj.get("data", {}) or {}
    if "text" in data and "node_id" not in data:
        return "text_chunk"
    if "outputs" in data or "outputs" in obj:
        return "workflow_finished"
    return ""


def generate_stream(dify_payload: dict, headers: dict, base_url: str, store_key=None):
    """从 Dify 获取 SSE 并转发给前端，同时累积文本用于后续存储。

    使用 iter_lines() 逐行解析标准 SSE 格式，正确关联
    ``event: xxx`` 行与后续 ``data: {...}`` 行，兼容两种 Dify
    响应风格（event 在 JSON 内 / event 作为独立 SSE 行）。
    store_key: (emp_id, workflow_type) 用于服务端 conversation_id 持久化。
    """
    accumulated_text = []
    try:
        logger.info("[SSE] POST %s, payload keys: %s", base_url, list(dify_payload.keys()))
        if dify_payload.get("conversation_id"):
            logger.info("[SSE] 使用 conversation_id: %s", dify_payload.get("conversation_id"))
        session = requests.Session()
        session.mount("https://", SSLAdapter())
        with session.post(
            base_url,
            headers=headers,
            json=dify_payload,
            stream=True,
            timeout=Config.STREAM_TIMEOUT,
            verify=False,
        ) as r:
            logger.info("[SSE] Dify HTTP status: %s", r.status_code)

            if r.status_code != 200:
                try:
                    error_detail = r.json()
                    err = f"Dify 请求失败: {r.status_code} - {error_detail}"
                except Exception:
                    error_detail = r.text[:500]
                    err = f"Dify 请求失败: {r.status_code} - {error_detail}"
                logger.error(err)
                logger.error("请求 URL: %s", base_url)
                logger.error("请求体: %s", json.dumps(dify_payload, ensure_ascii=False))
                yield f'data: {json.dumps({"error": err}, ensure_ascii=False)}\n\n'.encode()
                return

            seen_agent_ids: set = set()
            finished = False
            sse_event_field = None
            line_count = 0
            # 用可变 dict 持有状态，避免 Python 闭包变量重绑定问题
            ctx = {
                "cid": "",
                "announced": False,
                "has_text": False,
                "last_text": "",
            }

            def emit_conversation():
                if ctx["cid"] and not ctx["announced"]:
                    ctx["announced"] = True
                    payload = {"conversation_id": ctx["cid"], "done": False}
                    logger.info("[CONV] emit conversation_id=%s", ctx["cid"])
                    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()
                return None

            def emit_text(text: str):
                normalized = (text or "").strip()
                if not normalized:
                    return None
                # 避免同一段文本被重复透传
                if normalized == ctx["last_text"]:
                    _log("跳过重复文本块:", _preview(normalized, 120))
                    return None
                ctx["last_text"] = normalized
                ctx["has_text"] = True
                accumulated_text.append(text)
                payload = {"text": text, "done": False}
                if ctx["cid"]:
                    payload["conversation_id"] = ctx["cid"]
                return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()

            for raw_line in r.iter_lines():
                line_count += 1
                if not raw_line:
                    sse_event_field = None
                    continue

                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line:
                    sse_event_field = None
                    continue

                # SSE event 行：记住类型，等 data 行到来
                if line.startswith("event:"):
                    sse_event_field = line[6:].strip()
                    _log("SSE event 行:", sse_event_field)
                    continue

                # SSE data 行
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                else:
                    # 非标准行，可能是纯 JSON（部分 Dify 版本）
                    if line.startswith("{"):
                        data_str = line
                    else:
                        _log("跳过非 SSE 行:", _preview(line, 120))
                        continue

                if not data_str:
                    continue

                try:
                    obj = json.loads(data_str)
                except json.JSONDecodeError:
                    _log("JSON 解析失败:", _preview(data_str, 200))
                    continue

                if not isinstance(obj, dict):
                    continue

                cid = obj.get("conversation_id")
                if isinstance(cid, str) and cid.strip() and not ctx["cid"]:
                    ctx["cid"] = cid.strip()
                    if store_key:
                        _conversation_store[store_key] = ctx["cid"]
                    logger.info("[CONV] 获取 conversation_id=%s store_key=%s", ctx["cid"], store_key)

                conv_payload = emit_conversation()
                if conv_payload:
                    yield conv_payload

                # 确定事件类型：JSON 内 event > SSE event 行 > 字段推断
                event = obj.get("event") or sse_event_field or _infer_event_type(obj)
                data = obj.get("data", {}) or {}

                logger.info("[SSE] 事件: %s | 内容: %s", event, _preview(json.dumps(obj, ensure_ascii=False, default=str), 200))

                if event == "text_chunk":
                    text = _extract_event_text(obj)
                    if text:
                        payload = emit_text(text)
                        if payload:
                            yield payload

                elif event in ("message", "agent_message"):
                    text = _extract_event_text(obj)
                    if text:
                        payload = emit_text(text)
                        if payload:
                            yield payload

                elif event == "message_end":
                    if not ctx["has_text"]:
                        fallback_text = _extract_event_text(obj)
                        if fallback_text:
                            payload = emit_text(fallback_text)
                            if payload:
                                yield payload
                    finished = True
                    done_payload = {"done": True}
                    if ctx["cid"]:
                        done_payload["conversation_id"] = ctx["cid"]
                    yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n".encode()

                elif event == "workflow_finished":
                    wf_outputs = data.get("outputs") or obj.get("outputs") or {}
                    logger.info("[SSE] workflow_finished outputs: %s",
                                json.dumps(wf_outputs, ensure_ascii=False, default=str)[:1000])
                    final = _extract_final_text(data) or _extract_final_text(obj) or _extract_event_text(obj)
                    if (not ctx["has_text"]) and final:
                        payload = emit_text(final)
                        if payload:
                            yield payload
                    elif not ctx["has_text"] and not accumulated_text:
                        err_hint = "Dify 工作流未返回文本结果，可能工作流内部出现错误。请检查 Dify 日志。"
                        fallback_payload = {"text": err_hint, "done": False}
                        if ctx["cid"]:
                            fallback_payload["conversation_id"] = ctx["cid"]
                        yield f"data: {json.dumps(fallback_payload, ensure_ascii=False)}\n\n".encode()
                    finished = True
                    done_payload = {"done": True}
                    if ctx["cid"]:
                        done_payload["conversation_id"] = ctx["cid"]
                    yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n".encode()

                elif event == "node_finished":
                    node_type = (data.get("node_type") or "").lower()
                    if node_type in ("llm", "answer", "direct-reply", "end"):
                        fallback_text = _extract_event_text(obj)
                        if fallback_text and not ctx["has_text"]:
                            logger.info("[SSE] node_finished(%s) 提取文本: %s", node_type, _preview(fallback_text, 120))
                            payload = emit_text(fallback_text)
                            if payload:
                                yield payload
                    else:
                        _log("跳过 node_finished(%s) 不提取文本" % node_type)

                elif event == "error":
                    err_msg = obj.get("message") or obj.get("msg") or data.get("message") or str(obj)
                    logger.error("Dify 错误事件: %s", err_msg)
                    yield f'data: {json.dumps({"error": "Dify 工作流错误: " + str(err_msg), "done": True}, ensure_ascii=False)}\n\n'.encode()
                    return

                elif event == "agent_log":
                    log_id = data.get("id") or obj.get("id")
                    if log_id:
                        if log_id in seen_agent_ids:
                            continue
                        seen_agent_ids.add(log_id)

                elif event in ("ping", "workflow_started", "node_started",
                               "node_retry", "parallel_branch_started",
                               "parallel_branch_finished", "iteration_started",
                               "iteration_next", "iteration_completed",
                               "tts_message", "tts_message_end", "message_file",
                               "message_replace"):
                    _log("忽略事件:", event)

                else:
                    _log("未处理事件:", event, _preview(json.dumps(obj, ensure_ascii=False, default=str), 200))

                sse_event_field = None

            logger.info("[SSE] 流结束, 共 %d 行, has_text=%s, finished=%s, cid=%s, 累积文本长度=%d",
                        line_count, ctx["has_text"], finished, ctx["cid"], sum(len(t) for t in accumulated_text))

            if not finished:
                if not ctx["has_text"]:
                    msg = "工作流已结束，但未返回可展示文本。"
                    fallback_payload = {"text": msg, "done": False}
                    if ctx["cid"]:
                        fallback_payload["conversation_id"] = ctx["cid"]
                    yield f"data: {json.dumps(fallback_payload, ensure_ascii=False)}\n\n".encode()
                done_payload = {"done": True}
                if ctx["cid"]:
                    done_payload["conversation_id"] = ctx["cid"]
                yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n".encode()

    except Exception as e:
        logger.exception("generate_stream 异常")
        yield f'data: {json.dumps({"error": "服务器内部错误: " + str(e)}, ensure_ascii=False)}\n\n'.encode()


def _record_query_stat(workflow_type: str, query_text: str, emp_id: str,
                       duration_ms: int, success: bool):
    """异步记录查询统计（失败不影响主流程）"""
    try:
        execute(
            "INSERT INTO query_stat (workflow_type, query_text, emp_id, duration_ms, success) "
            "VALUES (%s, %s, %s, %s, %s)",
            (workflow_type, query_text[:500] if query_text else "", emp_id, duration_ms, int(success)),
        )
    except Exception as e:
        logger.warning("记录查询统计失败: %s", e)


# ── 路由 ────────────────────────────────────────────────────────────────────

@workflow_bp.route("/list", methods=["GET"])
def list_workflows():
    """返回所有可用工作流的元信息"""
    result = []
    for key, cfg in Config.WORKFLOW_CONFIG.items():
        result.append({
            "key": key,
            "label": cfg.get("label", key),
            "description": cfg.get("description", ""),
        })
    return jsonify({"workflows": result})


@workflow_bp.route("/run", methods=["POST"])
def run_workflow():
    """运行工作流，以 SSE 流式方式返回结果"""
    start_time = time.time()
    emp_id = "001"
    query_text = ""

    try:
        data = request.get_json(force=True)
        workflow_type = data.get("workflow_type", "suijisuicha")
        emp_id = data.get("user", "001")
        conversation_id = (data.get("conversation_id") or "").strip()

        # 如果前端没传 conversation_id，从服务端记忆里恢复
        store_key = (emp_id, workflow_type)
        logger.info("[CONV] 查询 store key=%s 当前store=%s 前端传入cid=%r",
                    store_key, dict(_conversation_store), conversation_id)
        if not conversation_id:
            conversation_id = _conversation_store.get(store_key, "")
            if conversation_id:
                logger.info("[CONV] 服务端记忆恢复 conversation_id: %s", conversation_id)
            else:
                logger.info("[CONV] store 里没有此 key，将新建对话")

        config = Config.WORKFLOW_CONFIG.get(workflow_type)
        if not config:
            return jsonify({"error": f"不支持的工作流类型: {workflow_type}"}), 400

        # 参数解析
        inputs_raw = data.get("inputs", {})
        if isinstance(inputs_raw, (str, bytes)):
            try:
                inputs = json.loads(inputs_raw)
            except json.JSONDecodeError:
                return jsonify({"error": "inputs 参数 JSON 解析失败"}), 400
        elif isinstance(inputs_raw, dict):
            inputs = inputs_raw
        else:
            return jsonify({"error": "inputs 参数类型错误"}), 400

        # 提取查询文本（用于统计）
        query_text = (
            inputs.get("content") or inputs.get("query") or
            inputs.get("question") or inputs.get("sys.query") or ""
        )

        # 各工作流参数适配
        if workflow_type == "duolunduihua":
            q = inputs.pop("query", None) or inputs.pop("question", None) or ""
            inputs["sys.query"] = q or inputs.get("sys.query", "")
        elif workflow_type == "shengchanjilu":
            if "question" not in inputs:
                inputs["question"] = (
                    inputs.pop("query", None) or
                    inputs.pop("content", None) or ""
                )

        # 根据应用类型构建不同的请求体
        app_type = config.get("app_type", "workflow")

        if app_type == "chatflow":
            # Chatflow 使用不同的 API 格式
            dify_payload = {
                "inputs": inputs,
                "query": query_text or inputs.get("content", ""),
                "response_mode": "streaming",
                "user": data.get("user", emp_id),
            }
            if conversation_id:
                dify_payload["conversation_id"] = conversation_id
        else:
            # Workflow 格式
            dify_payload = {
                "inputs": inputs,
                "response_mode": data.get("response_mode", "streaming"),
                "workflow_id": config["workflow_id"],
            }
            if data.get("user"):
                dify_payload["user"] = data["user"]

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }

        def streaming_response():
            yield from generate_stream(dify_payload, headers, config["base_url"], store_key=store_key)
            duration = int((time.time() - start_time) * 1000)
            _record_query_stat(workflow_type, query_text, emp_id, duration, True)

        return Response(
            streaming_response(),
            mimetype="text/event-stream",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "close",
            },
        )

    except Exception as e:
        logger.exception("run_workflow 异常")
        duration = int((time.time() - start_time) * 1000)
        _record_query_stat(workflow_type if "workflow_type" in locals() else "unknown",
                           query_text, emp_id, duration, False)
        return jsonify({"error": "服务器内部错误: " + str(e)}), 500


@workflow_bp.route("/reset", methods=["POST"])
def reset_conversation():
    """清除指定用户+工作流的 conversation_id（清屏时调用）"""
    data = request.get_json(force=True) or {}
    emp_id = data.get("user", "001")
    workflow_type = data.get("workflow_type", "")
    if workflow_type:
        key = (emp_id, workflow_type)
        old = _conversation_store.pop(key, None)
        logger.info("[SSE] 清除 conversation_id: %s (user=%s, type=%s)", old, emp_id, workflow_type)
    else:
        # 清除该用户所有工作流的记忆
        keys = [k for k in _conversation_store if k[0] == emp_id]
        for k in keys:
            _conversation_store.pop(k, None)
        logger.info("[SSE] 清除用户 %s 的所有 conversation_id, 共 %d 条", emp_id, len(keys))
    return jsonify({"ok": True})


@workflow_bp.route("/test", methods=["GET"])
def test_stream():
    """本地流式测试，不需要真实 Dify 连接"""
    def _gen():
        yield 'data: {"text": "流式输出测试开始\\n", "done": false}\n\n'
        sample = [
            "| 字段 | 值 |\\n",
            "| --- | --- |\\n",
            "| 系统 | 个人碎片数据管理 |\\n",
            "| 版本 | 2.0 |\\n",
            "| 状态 | ✅ 正常运行 |\\n",
            "\\n**所有流式接口工作正常。**",
        ]
        for chunk in sample:
            payload = json.dumps({"text": chunk, "done": False}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            time.sleep(0.08)
        yield 'data: {"done": true}\n\n'

    return Response(
        _gen(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
