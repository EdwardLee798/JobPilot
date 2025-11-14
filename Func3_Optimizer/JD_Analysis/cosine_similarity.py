# -*- coding: utf-8 -*-
"""
resume_exp_cosine_rank.py

功能（只关注 experience 部分）：
- 从一个或多个简历 JSON 中，仅抽取 experience 列表
- 逐“经历块”与 JD 计算向量余弦相似度
- 输出结构化 JSON：块数量、每块得分、最终排序（控制台打印 + 写文件）

依赖：
    pip install -U openai numpy

使用方式：
    直接修改本文件顶部的 RESUME_JSON_PATHS 与 JD_TEXT，然后运行：
    python resume_exp_cosine_rank.py
"""

import os
import json
from typing import List, Dict, Any, Tuple
import numpy as np
from openai import OpenAI

# ======= 在这里配置你的输入 =======

# 放简历 JSON；脚本会把所有 experience 合并计算
RESUME_JSON_PATHS = [
    "/home/zhenghong/hku_semester1/NLP/nlp_project/json_document/中文简历1.json",
    #/home/zhenghong/hku_semester1/NLP/nlp_project/json_document/中文简历2.json",
    #"/home/zhenghong/hku_semester1/NLP/nlp_project/json_document/英文简历1.json",
    #"/home/zhenghong/hku_semester1/NLP/nlp_project/json_document/英文简历2.json"

]

# JD 文本
JD_TEXT = """职位描述
1、为企业服务团队（如房产、物理安全和行政）建立业务指标系统，分析长期趋势和短期异常，产出有价值的报表；
2、基于指标系统搭建数据看板，并建立每日追踪和监控系统，及时辨别趋势或识别潜在风险；
3、根据业务需求进行各类数据分析，借助定性和定量分析、建模，快速识别内部问题或发现机会；
4、与运营、数仓、产品、研发和算法等团队合作，实现数据分析报表的持续优化，构建用户友好的数据系统和数据产品，以更好支持业务。
职位要求
1、本科及以上学历；五年以上数据分析相关经验；
2、精通SQL和Tableau、PowerBI或类似可视化工具；可运用Python或R进行数据分析；了解算法（ML、因果推断，动态规划）优先；
3、丰富的数据挖掘、信息收集、分析能力，较强的将业务问题转化为数据建模的能力；
4、具有较强的学习能力和好奇心，能够快速学习和理解新领域、新知识；
5、有良好的沟通表达能力和团队合作意识，能够带领项目团队支持业务；
6、英文可作为工作语言。"""

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

# ---------- IO ----------
def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- 文本拼接 ----------
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

# ---------- 仅抽取 experience 列表 ----------
def get_experience_list_and_key(resume: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    if isinstance(resume.get("experience"), list):
        return resume["experience"], "experience"
    if isinstance(resume.get("experiences"), list):
        return resume["experiences"], "experiences"
    return [], "experience"

def build_exp_title_text(item: Dict[str, Any]) -> Tuple[str, str]:
    name = item.get("name") or item.get("company") or ""
    title = item.get("title") or item.get("role") or ""
    period = item.get("period") or _join(item.get("start",""), item.get("end",""))
    location = item.get("location") or ""
    desc = item.get("description") or item.get("details") or item.get("summary") or ""
    head = _join(name, title, period, location)
    body = _stringify(desc)
    full = _join(head, body)
    return head if head else "Experience", full

# ---------- 向量与余弦 ----------
def embed_texts(client: OpenAI, texts: List[str], model: str) -> np.ndarray:
    if not texts:
        return np.zeros((0, 1), dtype="float32")
    resp = client.embeddings.create(model=model, input=texts)
    vecs = [d.embedding for d in resp.data]
    arr = np.array(vecs, dtype="float32")
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return arr / norms

def cosine_scores(q: np.ndarray, M: np.ndarray) -> np.ndarray:
    q = q.reshape(1, -1)
    return (M @ q.T).reshape(-1)

# ---------- 主流程 ----------
def run(jd_text: str, resume_paths: List[str]) -> Dict[str, Any]:
    client = _get_client()
    jd_vec = embed_texts(client, [jd_text], model=EMBED_MODEL)[0]

    results = []
    for path in resume_paths:
        if not path or not os.path.isfile(path):
            continue
        try:
            resume = load_json(path)
        except Exception as e:
            print(f"[WARN] 读取失败：{path} -> {e}")
            continue

        exp_list, key_name = get_experience_list_and_key(resume)
        if not exp_list:
            # 没有 experience 也输出空结果
            results.append({
                #"file": path,
                "sorted_blocks": [],
                "reordered_resume": resume
            })
            continue

        titles, texts = [], []
        for item in exp_list:
            t, full = build_exp_title_text(item)
            titles.append(t)
            texts.append(t + "\n" + full)

        blk_vecs = embed_texts(client, texts, model=EMBED_MODEL)
        sims = cosine_scores(jd_vec, blk_vecs)

        # 组装 (idx, score) 并按分数降序（分数并列保持原顺序）
        indexed_scores = [(i, float(sims[i])) for i in range(len(exp_list))]
        indexed_scores.sort(key=lambda x: (-x[1], x[0]))

        # 1) 只输出 sorted_blocks: "exp-i score=..."
        sorted_blocks_strings = [f"exp-{i+1} score={indexed_scores[k][1]:.6f}"
                                 for k, (i, _) in enumerate(indexed_scores)]

        # 2) 生成 experience 降序后的完整简历 JSON
        reordered = dict(resume)  # 浅拷贝
        reordered[key_name] = [exp_list[i] for (i, _) in indexed_scores]

        results.append({
            #"file": path,
            "sorted_blocks": sorted_blocks_strings,
            "reordered_resume": reordered
        })

    # 仅保留所需两项输出
    return {"results": results}

if __name__ == "__main__":
    out = run(JD_TEXT, RESUME_JSON_PATHS)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    try:
        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n已写入：{OUTPUT_JSON_PATH}")
    except Exception as e:
        print(f"[WARN] 写文件失败：{e}")
