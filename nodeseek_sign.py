import os
import time

import requests

random = "false"  # 随机签到1-x鸡腿为true，固定鸡腿*5为false
Cookie = os.environ.get("COOKIE", "")

SIGNED_MARKERS = (
    "今天已签到", "今天已经签到", "今日已签到", "今日已经签到",
    "已经签到过", "已签到过", "已完成签到", "重复签到",
)
ATTEMPTS = 3  # 网络/风控类失败重试次数


def sign_in():
    """返回 (是否成功, 说明文字)。只有重试也没救的才返回失败。"""
    url = f"https://www.nodeseek.com/api/attendance?random={random}"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        'sec-ch-ua': "\"Not A(Brand\";v=\"99\", \"Microsoft Edge\";v=\"121\", \"Chromium\";v=\"121\"",
        'sec-ch-ua-mobile': "?0",
        'sec-ch-ua-platform': "\"Windows\"",
        'origin': "https://www.nodeseek.com",
        'sec-fetch-site': "same-origin",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://www.nodeseek.com/board",
        'accept-language': "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        'Cookie': Cookie
    }

    reason = "未知错误"
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.post(url, headers=headers, timeout=30)
        except requests.RequestException as e:
            reason = f"请求异常：{e}"
            print(f"第{attempt}次 {reason}")
            time.sleep(5 * attempt)
            continue

        print(f"NodeSeek HTTP status: {response.status_code}; Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        try:
            response_data = response.json()
        except ValueError:
            # Cloudflare 挑战页（Just a moment...）等非 JSON 响应
            reason = f"NodeSeek 返回非 JSON（HTTP {response.status_code}），通常是 Cloudflare 风控拦截"
            print(f"第{attempt}次 {reason}")
            time.sleep(5 * attempt)
            continue

        message = str(response_data.get('message') or '')
        if any(text in message for text in SIGNED_MARKERS):
            return True, message
        success = response_data.get('success')
        if success is True or success == "true":
            return True, message

        reason = message or f"HTTP {response.status_code}"
        if "high risk" in message.lower():
            reason = f"{message}（NodeSeek 风控拦截，多与出口 IP 有关，可稍后重试或换 runner）"
        elif "USER NOT FOUND" in message:
            reason = f"{message}（Cookie 已失效，请重新抓取后更新 COOKIE secret）"
        if response.status_code >= 500 or response.status_code == 429:
            print(f"第{attempt}次 服务端 {response.status_code}：{reason}")
            time.sleep(5 * attempt)
            continue
        return False, reason

    return False, reason


if not Cookie:
    print("请先设置Cookie")
    raise SystemExit(1)

ok, message = sign_in()
print(message)
raise SystemExit(0 if ok else 1)
