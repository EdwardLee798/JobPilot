#!/usr/bin/env python3
"""
测试整合后的进度管理模块
"""

import requests
import time

BASE_URL = "http://localhost:5000"

def test_create_job():
    """测试创建职位记录"""
    print("测试创建职位记录...")
    data = {
        "job_title": "Python后端工程师",
        "company_name": "测试公司",
        "job_desc": "负责后端开发，要求熟悉Python、Flask等技术栈",
        "tracking_method": "email@example.com"
    }
    
    response = requests.post(f"{BASE_URL}/api/tracking/job", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    return response.json().get('job_id')

def test_update_status(job_id):
    """测试更新状态"""
    print(f"\n测试更新职位 {job_id} 的状态...")
    data = {
        "status": "一面",
        "event_time": time.time()
    }
    
    response = requests.put(f"{BASE_URL}/api/tracking/job/{job_id}", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")

def test_get_jobs():
    """测试获取职位列表"""
    print("\n测试获取职位列表...")
    response = requests.get(f"{BASE_URL}/api/tracking/jobs")
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"找到 {len(data.get('jobs', []))} 个职位")
    if data.get('jobs'):
        print(f"第一个职位: {data['jobs'][0]['company_name']} - {data['jobs'][0]['job_title']}")

def test_stats():
    """测试统计信息"""
    print("\n测试获取统计信息...")
    response = requests.get(f"{BASE_URL}/api/tracking/stats")
    print(f"状态码: {response.status_code}")
    print(f"统计: {response.json()}")

def test_chat():
    """测试聊天功能"""
    print("\n测试聊天功能...")
    data = {"message": "帮我查询所有的申请进度"}
    
    response = requests.post(
        f"{BASE_URL}/api/tracking/chat_stream",
        json=data,
        stream=True
    )
    
    print("Agent回复:")
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                print(line_str[6:])

if __name__ == "__main__":
    print("=" * 50)
    print("JobPilot 进度管理模块测试")
    print("=" * 50)
    
    try:
        # 测试创建职位
        job_id = test_create_job()
        
        if job_id:
            # 测试更新状态
            test_update_status(job_id)
        
        # 测试获取列表
        test_get_jobs()
        
        # 测试统计
        test_stats()
        
        # 测试聊天（需要agent配置）
        # test_chat()
        
        print("\n" + "=" * 50)
        print("测试完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n错误: {e}")
