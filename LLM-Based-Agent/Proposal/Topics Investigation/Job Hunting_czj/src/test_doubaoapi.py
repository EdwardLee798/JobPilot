import os
from openai import OpenAI

# -------------------------- 关键配置（请确认以下2点）--------------------------
# 1. 确保环境变量中已设置 "ARK_API_KEY"（火山方舟的API密钥）
# 2. 确认 "model" 参数是您在火山方舟平台创建的「豆包推理接入点ID」
# -----------------------------------------------------------------------------

# 1. 从环境变量获取火山方舟API密钥（若未获取到则报错提醒）
ark_api_key = os.environ.get("ARK_API_KEY")
if not ark_api_key:
    raise ValueError("请先设置环境变量 'ARK_API_KEY'（火山方舟平台的API密钥）！")

# 2. 初始化火山方舟的OpenAI兼容客户端（明确指定api_key，避免默认逻辑冲突）
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",  # 火山方舟北京地域地址（无需修改）
    api_key=ark_api_key  # 显式传入火山方舟密钥，避免读取OPENAI_API_KEY
)

try:
    # 3. 调用豆包模型（支持图文输入，此处为您的原始需求）
    response = client.chat.completions.create(
        model="doubao-seed-1-6-250615",  # 替换为您在火山方舟的「豆包推理接入点ID」
        messages=[
            {
                "role": "user",
                "content": [
                    # 图片输入（确保图片URL可访问，或替换为您自己的图片URL）
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"
                        },
                    },
                    # 文本问题
                    {"type": "text", "text": "这是哪里？"},
                ],
            }
        ],
        temperature=0.7,  # 生成多样性（0-1，按需调整）
        max_tokens=512    # 最大生成长度（按需调整）
    )

    # 4. 解析并打印结果（简化输出，只显示豆包的回答内容）
    answer = response.choices[0].message.content
    print("豆包回答：")
    print("-" * 50)
    print(answer)
    print("-" * 50)

except Exception as e:
    print(f"调用失败：{str(e)}")
    # 若报错包含"model not found"，请检查：
    # 1. model参数是否为火山方舟的「推理接入点ID」（不是模型名称）
    # 2. 接入点是否已部署，且状态为"正常"