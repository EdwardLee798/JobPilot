# -*- coding: utf-8 -*-
"""
resume_exp_cosine_rank.py

功能（只关注 experience 部分）：
- 从一个或多个简历 JSON 中，仅抽取 experience 列表
- 逐“经历块”与 JD 计算向量余弦相似度
- 输出结构化 JSON：块数量、每块得分、最终排序（控制台打印 + 写文件）

依赖：
    pip install -U openai numpy

环境变量（DashScope OpenAI兼容端点）：
    # 国际
    export DASHSCOPE_API_KEY=your_key
    export DASHSCOPE_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    # 国内
    # export DASHSCOPE_API_KEY=your_key
    # export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

使用方式：
    直接修改本文件顶部的 RESUME_JSON_PATHS 与 JD_TEXT，然后运行：
    python resume_exp_cosine_rank.py
"""

import os
import json
import re
from typing import List, Dict, Any
import numpy as np
from openai import OpenAI

# ======= 在这里配置你的输入 =======

# 放简历 JSON；脚本会把所有 experience 合并计算
RESUME_JSON_PATHS = [
    #"/home/zhenghong/hku_semester1/NLP/nlp_project/json_document/中文简历1.json",
    #/home/zhenghong/hku_semester1/NLP/nlp_project/json_document/中文简历2.json",
    "/home/zhenghong/hku_semester1/NLP/nlp_project/json_document/英文简历1.json",
    #"/home/zhenghong/hku_semester1/NLP/nlp_project/json_document/英文简历2.json"

]

# JD 文本
JD_TEXT = """职位描述
1、负责负责客服业务大模型基建相关研发，深入业务，理解抽象，为用户提供智能化、高效的服务解决方案；
2、对不同周期和紧急程度的产品需求进行合理拆解实现；
3、进行相关产品的技术文档编写，方案设计；
4、学习研究业界先进技术，保持技术进步。
职位要求
1、本科及以上学历，计算机相关专业背景；
2、熟悉Java/Golang/PHP/Python/C++等至少一门语言，Golang、Python、Java经验者优先；
3、熟悉常用的互联网技术，包括但不限于Linux系统及原理、MySQL、NoSQL、RPC、MQ、缓存技术、微服务架构等；
4、具有良好的编码和文档习惯，注重代码风格，熟悉基础设计模式和原则，能持续的关注和优化自己做的项目；
5、加分：有客服系统或商业化SaaS平台相关开发经验。"""

# 结果写入路径
OUTPUT_JSON_PATH = "/home/zhenghong/hku_semester1/NLP/nlp_project/json_output/exp_cosine_rank_result.json"

# 选择 Embedding 模型名（DashScope 兼容端点）
EMBED_MODEL = os.getenv("EMBED_MODEL_NAME", "text-embedding-v3")
# ==================================

# -------- OpenAI 兼容客户端（DashScope） --------
def _get_client() -> OpenAI:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    if not api_key:
        raise RuntimeError("请设置环境变量 DASHSCOPE_API_KEY（DashScope 的 API Key）。")
    return OpenAI(api_key=api_key, base_url=base_url)

# -------- 小工具 --------
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
def detect_lang(text: str) -> str:
    if not text:
        return "unk"
    cjk = len(_CJK_RE.findall(text))
    return "zh" if cjk >= max(1, int(0.1 * len(text))) else "en"

def _join(*parts) -> str:
    return " ".join([p for p in parts if p]).strip()

def _stringify(obj) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, (list, tuple)):
        return " ".join([_stringify(x) for x in obj if _stringify(x)])
    if isinstance(obj, dict):
        return " ".join([_stringify(v) for v in obj.values() if _stringify(v)])
    return str(obj)

# -------- 从简历 JSON 中仅抽取 experience 块 --------
def load_resume_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_experience_blocks(resume: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    兼容以下字段：
      - experience 或 experiences: List[dict]
        典型子字段：name/company, title/role, period 或 start+end, location, description
    输出块字段：
      block_id, section='experience', title, lang, text
    """
    blocks: List[Dict[str, Any]] = []
    exp_list = None
    # 兼容 experience / experiences
    for key in ["experience", "experiences"]:
        if isinstance(resume.get(key), list):
            exp_list = resume[key]
            break
    if not isinstance(exp_list, list):
        return blocks

    for i, e in enumerate(exp_list, 1):
        name = e.get("name") or e.get("company") or ""
        title = e.get("title") or e.get("role") or ""
        period = e.get("period") or _join(e.get("start",""), e.get("end",""))
        location = e.get("location") or ""
        desc = e.get("description") or e.get("details") or e.get("summary") or ""
        # desc 可能是 list/dict，统一转字符串
        desc_txt = _stringify(desc)

        head = _join(name, title, period, location)
        txt = _join(head, desc_txt)
        if not txt:
            continue

        blocks.append({
            "block_id": f"exp-{i}",
            "section": "experience",
            "title": head if head else "Experience",
            "lang": detect_lang(txt),
            "text": txt
        })
    return blocks

# -------- 向量与余弦相似度 --------
def embed_texts(client: OpenAI, texts: List[str], model: str) -> np.ndarray:
    """
    使用 DashScope 的 OpenAI 兼容接口做向量，返回 L2 归一化后的向量矩阵。
    """
    if not texts:
        return np.zeros((0, 1536), dtype="float32")
    resp = client.embeddings.create(model=model, input=texts)
    vecs = [d.embedding for d in resp.data]
    arr = np.array(vecs, dtype="float32")
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return arr / norms

def cosine_scores(q: np.ndarray, M: np.ndarray) -> np.ndarray:
    """
    q: (d,) 或 (1,d)
    M: (n,d)
    return: (n,) 余弦相似度（点积，因为已归一化）
    """
    q = q.reshape(1, -1)
    return (M @ q.T).reshape(-1)

# -------- 主流程（只对 experience 计算相似度） --------
def run(jd_text: str, resume_paths: List[str]) -> Dict[str, Any]:
    # 1) 载入所有简历，仅抽取 experience
    all_blocks: List[Dict[str, Any]] = []
    used_files: List[str] = []
    for p in resume_paths:
        if not p or not os.path.isfile(p):
            continue
        try:
            rj = load_resume_json(p)
        except Exception as e:
            print(f"[WARN] 加载失败：{p} -> {e}")
            continue
        exps = extract_experience_blocks(rj)
        all_blocks.extend(exps)
        used_files.append(p)

    if not all_blocks:
        raise RuntimeError("没有抽取到任何【experience】块，请检查 JSON 路径或文件内容。")

    # 2) 向量计算
    client = _get_client()
    jd_vec = embed_texts(client, [jd_text], model=EMBED_MODEL)[0]
    blk_texts = [b["title"] + "\n" + b["text"] for b in all_blocks]
    blk_vecs = embed_texts(client, blk_texts, model=EMBED_MODEL)

    # 3) 余弦相似度 & 排序
    sims = cosine_scores(jd_vec, blk_vecs)  # (n,)
    for i, s in enumerate(sims.tolist()):
        all_blocks[i]["score"] = float(s)

    order = np.argsort(-sims)  # 从高到低
    sorted_blocks = [all_blocks[int(i)] for i in order.tolist()]

    # 4) 结构化输出
    out = {
        "jd": {
            "text": jd_text,
            "embedding_model": EMBED_MODEL
        },
        "resume_source_files": used_files,
        "section": "experience",
        "blocks_count": len(all_blocks),
        "blocks": [
            {
                "block_id": b["block_id"],
                "title": b["title"],
                "lang": b.get("lang", "unk"),
                "score": round(float(b["score"]), 6)
            } for b in all_blocks
        ],
        "sorted_block_ids": [b["block_id"] for b in sorted_blocks],
        "sorted_blocks": [
            {
                "block_id": b["block_id"],
                "title": b["title"],
                "lang": b.get("lang", "unk"),
                "score": round(float(b["score"]), 6)
            } for b in sorted_blocks
        ]
    }
    return out

if __name__ == "__main__":
    result = run(JD_TEXT, RESUME_JSON_PATHS)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    try:
        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n已写入：{OUTPUT_JSON_PATH}")
    except Exception as e:
        print(f"[WARN] 写文件失败：{e}")
