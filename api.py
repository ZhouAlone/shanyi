# -*- coding: utf-8 -*-
"""Shanyi · 翻译与 OCR 的 HTTP 调用（每次读取云配置，改配置即生效）。"""
from __future__ import annotations
import json
import urllib.error
import urllib.request

from config import CONF, load_cloud


def _chat(base: str, api_key: str, payload: dict, timeout: int) -> str:
    """POST /chat/completions；HTTP 错误带出服务端响应体（真实拒绝原因）。"""
    # 显式空代理 = 永远直连：urllib 会在进程内缓存启动时的系统代理，
    # Clash 之类关掉后缓存的 127.0.0.1:7890 会造成 10061 假故障
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        base + "/chat/completions", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"})
    try:
        with opener.open(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"HTTP {e.code}: {body}") from None
    return d["choices"][0]["message"]["content"].strip()


def translate(text: str) -> str:
    """方向自动判断：汉字为主→译英，拉丁字母为主→译中。"""
    base, model, api_key = load_cloud()
    cjk = sum('\u4e00' <= c <= '\u9fff' for c in text)
    latin = sum(c.isascii() and c.isalpha() for c in text)
    target = "英语" if cjk >= latin else "中文"
    payload = {
        "model": model,
        "messages": [
            {"role": "system",
             "content": f"你是翻译引擎。把用户文本翻译为{target}，只输出译文，不要解释、不要引号。"},
            {"role": "user", "content": text},
        ],
        "max_tokens": 500,
    }
    return _chat(base, api_key, payload, CONF["http_timeout"])


_EXPLAIN_SYSTEM = (
    "你是编程助手。用户在阅读技术文档或源码时遇到了不理解的文本"
    "（可能是英文术语、参数名、代码片段或文档句子）。\n"
    "用中文解释它的作用与使用场景：\n"
    "- 是代码/参数名：逐部分说明含义，指出属于哪个知名库/框架（如能识别）\n"
    "- 是文档句子：解释这句话在讲什么技术行为\n"
    "- 简明扼要，最多 3 句话；一句话能说清就不要写三句\n"
    "- 只输出解释本身，不要开场白和客套")


def explain(text: str) -> str:
    """解释模式：术语/参数/代码的中文讲解（非翻译）。"""
    base, model, api_key = load_cloud()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _EXPLAIN_SYSTEM},
            {"role": "user", "content": text},
        ],
        # 解释回答比翻译长；推理型模型思考也吃 token，给足余量
        "max_tokens": CONF.get("explain_max_tokens", 1000),
    }
    return _chat(base, api_key, payload, CONF["http_timeout"])


def ocr(b64png: str) -> str:
    """DeepSeek-OCR：截屏 PNG 的 base64 → 文字。"""
    base, _, api_key = load_cloud()
    payload = {
        "model": CONF["cloud"].get("ocr_model", "deepseek-ai/DeepSeek-OCR"),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64png}"}},
                # 官方触发词：Free OCR.（认完即止，抑制幻觉长文）
                {"type": "text", "text": "Free OCR."},
            ],
        }],
        "max_tokens": 2000,
        "temperature": 0,
    }
    return _chat(base, api_key, payload, 120)
