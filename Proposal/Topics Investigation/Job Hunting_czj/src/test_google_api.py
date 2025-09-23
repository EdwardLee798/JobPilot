import os
import google.generativeai as genai
import httpx # 确保 httpx 库已安装

print("--- Google AI 连接测试脚本 (最终修正版) ---")

# 1. 定义你的代理地址
# 注意：对于 httpx，代理值本身也应该是字符串。
proxy_url = "http://127.0.0.1:7897"
proxies = {
    "http://": proxy_url,
    "https://": proxy_url,
}

print(f"将强制使用代理: {proxy_url}")

# 2. 配置API密钥
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("错误: 请确保你已经设置了 'GOOGLE_API_KEY' 环境变量。")
else:
    print("API 密钥已加载。")
    genai.configure(api_key=api_key)

    try:
        # 3. 创建一个配置好代理的 httpx 客户端
        transport = httpx.Client(proxies=proxies)

        # 4. 在创建模型时，将配置好的客户端作为 transport 传入
        print("正在创建 Gemini Pro 模型并应用代理配置...")
        model = genai.GenerativeModel(
            model_name='gemini-pro',
            transport=transport  # <--- 这是最关键、最正确的修改
        )
        print("模型创建成功。")

        # 5. 发送一个简单的请求
        print("\n正在通过代理向 Google AI 发送一个简单的测试请求...")
        print("(这可能需要几秒钟，请耐心等待...)")
        
        response = model.generate_content("用中文简单回答：天空是什么颜色的？")
        
        print("\n✅--- 测试成功! ---✅")
        print("从Google AI收到的回答:")
        print(response.text)
        print("------------------------")
        print("您的Python环境已成功通过代理连接到 Google AI 服务！")

    except Exception as e:
        print("\n❌--- 测试失败! ---❌")
        print("即使强制使用代理，连接到 Google AI 时仍然发生错误。")
        print("错误详情:", e)
        print("\n这不应该发生，因为curl测试成功了。请检查代理软件的日志或重启代理软件再试一次。")