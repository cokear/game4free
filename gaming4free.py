import time
import os
import json
import re
import random
import requests

# 智能环境配置
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"

if "XAUTHORITY" not in os.environ:
    if os.path.exists("/home/headless/.Xauthority"):
        os.environ["XAUTHORITY"] = "/home/headless/.Xauthority"

print(f"[DEBUG] Env DISPLAY: {os.environ.get('DISPLAY')}")
print(f"[DEBUG] Env XAUTHORITY: {os.environ.get('XAUTHORITY')}")

from seleniumbase import SB

# ================= CF 状态检测 =================

def is_cf_blocked(sb):
    try:
        text = sb.get_text("body").lower()
    except:
        text = ""

    if (
        "just a moment" in text or
        "verify you are human" in text or
        "checking your browser" in text or
        "challenge" in text
    ):
        return True

    try:
        if sb.is_element_present('iframe[src*="cloudflare"]'):
            return True
        if sb.is_element_present('iframe[src*="turnstile"]'):
            return True
    except:
        pass

    return False


def wait_cf_clear(sb, timeout=120):
    start = time.time()

    while time.time() - start < timeout:
        if not is_cf_blocked(sb):
            return True

        print("🛡️ CF 阻塞中，等待解除...")
        time.sleep(3)

    return False


# ================= 配置 =================
PROXY_URL = os.getenv("PROXY", "")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
SERVERS = os.getenv("SERVERS", "").strip()

SERVER_LIST = []
if SERVERS:
    for item in SERVERS.split("|"):
        try:
            num, region = item.split(",", 1)
            SERVER_LIST.append({"num": num.strip(), "region": region.strip()})
        except:
            print(f"⚠️ SERVERS 配置错误: {item}")

# ================= 主类 =================

class Game4FreeRenewal:

    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.screenshot_dir = os.path.join(self.BASE_DIR, "artifacts")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    def get_remaining_time(self, sb):
        try:
            return sb.get_text('div.countdown-time').strip()
        except:
            return "未知"

    # ================= 核心：成功判定 =================
    def wait_success(self, sb, old_time, timeout=90):
        start = time.time()

        while time.time() - start < timeout:

            # 1. CF 卡住直接退出
            if is_cf_blocked(sb):
                self.log("⚠️ CF 仍在阻塞，暂停判定")
                time.sleep(3)
                continue

            # 2. 读取时间
            try:
                new_time = self.get_remaining_time(sb)
            except:
                new_time = "未知"

            self.log(f"🧪 时间检测: {old_time} → {new_time}")

            # 3. 成功条件（关键）
            if new_time != old_time and new_time != "未知":
                self.log("✅ 检测到时间变化（可能续期成功）")
                return True, new_time

            time.sleep(3)

        return False, old_time

    # ================= 运行逻辑 =================
    def run_single_server(self, server_num, region):

        url = f"https://g4f.gg/{server_num}"

        self.log("=" * 40)
        self.log(f"🚀 开始 [{region}] {server_num}")
        self.log("=" * 40)

        with SB(
            uc=True,
            test=True,
            headed=True,
            headless=False,
            xvfb=False,
            chromium_arg="--no-sandbox,--disable-dev-shm-usage,--disable-gpu",
            proxy=PROXY_URL if PROXY_URL else None
        ) as sb:

            try:
                self.log("启动浏览器...")
                sb.uc_open_with_reconnect(url, reconnect_time=5)
                time.sleep(5)

                if "login" in sb.get_current_url():
                    self.log("❌ 登录失效")
                    return

                # 初始时间
                old_time = self.get_remaining_time(sb)
                self.log(f"⏱️ 当前时间: {old_time}")

                # 点击
                self.log("🖱️ 点击 ADD 90 MIN")
                sb.click("//button[contains(., 'ADD 90 MIN')]")

                time.sleep(3)

                # ================= CF 等待 =================
                if is_cf_blocked(sb):
                    self.log("🛡️ 进入 CF 状态，等待解除")
                    wait_cf_clear(sb, 120)

                # ================= 成功判定 =================
                ok, new_time = self.wait_success(sb, old_time)

                screenshot = f"{self.screenshot_dir}/result_{server_num}.png"
                sb.save_screenshot(screenshot)

                if ok:
                    self.log(f"🎉 成功: {old_time} → {new_time}")
                else:
                    self.log("❌ 未检测到成功变化")

            except Exception as e:
                self.log(f"❌ 异常: {e}")
                sb.save_screenshot(f"{self.screenshot_dir}/error_{server_num}.png")

    def run(self):
        if not SERVER_LIST:
            self.log("❌ 没有服务器")
            return

        for s in SERVER_LIST:
            self.run_single_server(s["num"], s["region"])


if __name__ == "__main__":
    Game4FreeRenewal().run()
