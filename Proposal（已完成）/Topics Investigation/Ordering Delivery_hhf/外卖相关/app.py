import pygetwindow as gw
import pyautogui
import time
import requests
import json
import base64
import os
from PIL import Image
import io

# 豆包大模型API配置（使用你提供的信息）
DOUBAO_API_KEY = "560df2c4-d33f-4c26-8c77-bd9b6ee92bf8"
DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_MODEL = "doubao-seed-1-6-vision-250815"

# 截图保存路径（当前脚本所在目录）
SCREENSHOT_SAVE_PATH = os.path.join(os.path.dirname(__file__), "foodpanda_screenshot.png")


def encode_image_to_base64(image):
    """将PIL图像转换为base64编码字符串"""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')


def call_doubao_api(prompt, image=None):
    """调用豆包API，严格遵循官方格式"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DOUBAO_API_KEY}"
    }

    content = []
    if image:
        base64_image = encode_image_to_base64(image)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64_image}"
            }
        })
    content.append({
        "type": "text",
        "text": prompt
    })

    payload = {
        "model": DOUBAO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ]
    }

    try:
        response = requests.post(DOUBAO_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        print(f"响应内容: {response.text if 'response' in locals() else '无响应'}")
        return None


def get_valid_screenshot(window_region):
    """获取有效截图（解决纯黑问题），并保存备份"""
    # 1. 激活窗口并等待渲染
    emu_window = gw.getWindowsWithTitle("Android Device")[0]
    emu_window.activate()
    time.sleep(1.5)  # 延长等待时间，确保界面渲染完成

    # 2. 截图（使用窗口坐标，避免截到其他区域）
    screenshot = pyautogui.screenshot(
        region=(
            window_region["left"],
            window_region["top"],
            window_region["width"],
            window_region["height"]
        )
    )

    # 3. 保存截图备份
    screenshot.save(SCREENSHOT_SAVE_PATH)
    print(f"截图已保存到：{SCREENSHOT_SAVE_PATH}")

    # 4. 检查截图是否纯黑（简单验证：计算非黑色像素占比）
    img_array = Image.open(SCREENSHOT_SAVE_PATH).convert("L")  # 转为灰度图
    pixels = img_array.getdata()
    non_black_pixels = sum(1 for p in pixels if p > 10)  # 像素值>10视为非黑色
    non_black_ratio = non_black_pixels / len(pixels)

    if non_black_ratio < 0.05:  # 非黑色像素占比<5%，判定为纯黑
        print("警告：截图接近纯黑，尝试重新截图...")
        # 重新激活+截图（增加窗口交互，确保渲染）
        pyautogui.click(window_region["left"] + 50, window_region["top"] + 50)  # 点击窗口内部
        time.sleep(1)
        screenshot = pyautogui.screenshot(region=(
            window_region["left"], window_region["top"],
            window_region["width"], window_region["height"]
        ))
        screenshot.save(SCREENSHOT_SAVE_PATH)  # 覆盖保存
        print("重新截图已保存")

    return screenshot


def get_button_coordinates(category, window_region, screenshot):
    """让豆包识别按钮坐标"""
    prompt = f"""
    这是Foodpanda应用的截图，显示了菜式分类按钮。
    请找到"{category}"类别按钮在截图中的位置，坐标以截图左上角为原点，格式为"x,y"（仅数字，用英文逗号分隔）。
    若未找到该按钮，直接返回"not_found"。不要添加任何额外文字、解释或标点。
    """
    coord_str = call_doubao_api(prompt, screenshot)
    if not coord_str or coord_str.strip().lower() == "not_found":
        return None
    try:
        # 清理坐标字符串（去除可能的空格、引号）
        coord_str = coord_str.strip().replace('"', '').replace("'", "")
        x, y = map(int, coord_str.split(','))
        # 转换为屏幕绝对坐标（加上窗口偏移）
        return (window_region["left"] + x, window_region["top"] + y)
    except Exception as e:
        print(f"坐标解析失败：{str(e)}，原始坐标字符串：{coord_str}")
        return None


def main():
    print("===== Foodpanda自动点餐助手 =====")

    # 1. 查找并激活模拟器窗口
    target_window_title = "Android Device"
    emu_windows = [w for w in gw.getAllWindows() if target_window_title in w.title]
    if not emu_windows:
        print(f"错误：未找到标题包含'{target_window_title}'的窗口，请先打开MuMu模拟器")
        return
    emu_window = emu_windows[0]
    window_region = {
        "left": emu_window.left,
        "top": emu_window.top,
        "width": emu_window.width,
        "height": emu_window.height
    }

    # 确保窗口非最小化并激活
    if emu_window.isMinimized:
        emu_window.restore()
        time.sleep(0.5)
    emu_window.activate()
    time.sleep(1)
    print(
        f"已激活窗口：{emu_window.title}（位置：{window_region['left']},{window_region['top']}，大小：{window_region['width']}x{window_region['height']}）")

    # 2. 获取有效截图（解决纯黑问题）
    print("正在截取应用界面...")
    screenshot = get_valid_screenshot(window_region)

    # 3. 识别可用菜式分类
    categories_prompt = """
    请识别这张Foodpanda应用截图中的所有菜式分类名称（仅分类按钮上的文字，如"Pizza"、"寿司"），
    用英文逗号分隔所有分类，不要添加任何额外文字、解释或标点。
    若截图中无分类按钮，直接返回"no_categories"。
    """
    categories = call_doubao_api(categories_prompt, screenshot)
    if not categories or categories.strip().lower() == "no_categories":
        print("错误：无法从截图中识别菜式分类，请检查截图是否正常（路径：{SCREENSHOT_SAVE_PATH}）")
        return
    # 清理分类结果（去除可能的空格、中文逗号）
    categories = categories.strip().replace('，', ',').replace(' ', '')
    print(f"识别到的菜式分类: {categories}")

    # 4. 对话循环（处理用户输入）
    while True:
        try:
            user_input = input("\n今天想吃什么？")
            if not user_input.strip():
                print("提示：请输入有效的菜式名称（如'寿司'、'Pizza'）")
                continue

            # 5. 调用豆包识别用户意图（匹配分类）
            intent_prompt = f"""
            已知Foodpanda可用菜式分类：{categories}（用英文逗号分隔）
            用户输入："{user_input.strip()}"
            请判断用户想吃的菜式属于哪个分类，直接返回分类名称（需与已知分类完全一致）。
            若不属于任何已知分类，直接返回"none"。不要添加任何额外文字、解释或标点。
            """
            recognized_category = call_doubao_api(intent_prompt)
            if not recognized_category or recognized_category.strip().lower() == "none":
                print(f"未找到匹配的分类（可用分类：{categories}），请重新输入")
                continue

            recognized_category = recognized_category.strip()
            print(f"识别到用户想吃: {recognized_category}")

            # 6. 查找并点击对应按钮
            button_coords = get_button_coordinates(recognized_category, window_region, screenshot)
            if button_coords:
                print(f"找到{recognized_category}按钮，坐标：{button_coords}，准备点击...")
                # 点击前再次激活窗口，确保在前台
                emu_window.activate()
                time.sleep(0.5)
                pyautogui.click(button_coords)
                print(f"成功点击{recognized_category}按钮")
                break
            else:
                print(f"未找到{recognized_category}按钮，请检查截图中是否存在该分类（截图路径：{SCREENSHOT_SAVE_PATH}）")

        except KeyboardInterrupt:
            print("\n程序已被手动中断")
            break
        except Exception as e:
            print(f"操作出错：{str(e)}，请重试")
            continue


if __name__ == "__main__":
    main()