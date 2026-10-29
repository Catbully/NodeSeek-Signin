import os
import time

import requests

random = "false"  # 随机签到1-x鸡腿为true，固定鸡腿*5为false
Cookie = os.environ.get("COOKIE", "")
pushplus_token = os.environ.get("PUSHPLUS_TOKEN")
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
chat_id = os.environ.get("CHAT_ID", "")
telegram_api_url = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")  # 代理api,可以使用自己的反代

SIGNED_MARKERS = (
    "今天已签到", "今天已经签到", "今日已签到", "今日已经签到",
    "已经签到过", "已签到过", "已完成签到", "重复签到",
)
ATTEMPTS = 3  # 网络/风控类失败重试次数


def telegram_Bot(token, chat_id, message):
    url = f'{telegram_api_url}/bot{token}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': message
    }
    try:
        r = requests.post(url, json=data, timeout=30)
        print(f"telegram推送结果：{r.json().get('ok')}\n")
    except Exception as e:
        # 推送失败不能影响签到结论，否则日志会被误导
        print(f"telegram推送异常：{e}\n")


def pushplus_ts(token, rw, msg):
    url = 'https://www.pushplus.plus/send/'
    data = {
        "token": token,
        "title": rw,
        "content": msg
    }
    try:
        r = requests.post(url, json=data, timeout=30)
        print(f'pushplus推送结果：{r.json().get("msg", None)}\n')
    except Exception as e:
        print(f"pushplus推送异常：{e}\n")


def report(message, failed):
    # 沿用原策略：telegram 成功失败都推，pushplus 只在失败时推
    if telegram_bot_token and chat_id:
        telegram_Bot(telegram_bot_token, chat_id, message)
    if failed and pushplus_token:
        pushplus_ts(pushplus_token, "nodeseek签到", message)


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
if ok:
    report(message, failed=False)
else:
    report(message, failed=True)
    raise SystemExit(1)
