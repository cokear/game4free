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

# ================= 配置区域 =================
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
            print(f"⚠️ SERVERS 配置格式错误: {item}")
# ===========================================


class Game4FreeRenewal:
    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.screenshot_dir = os.path.join(self.BASE_DIR, "artifacts")
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

    def log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] [INFO] {msg}", flush=True)

    def human_wait(self, min_s=6, max_s=10):
        time.sleep(random.uniform(min_s, max_s))

    def get_remaining_time(self, sb):
        remaining_text = "未知"
        try:
            sb.wait_for_element_visible('div.countdown-time', timeout=15)
            time.sleep(2)
            remaining_text = sb.get_text('div.countdown-time').strip()
        except:
            try:
                remaining_text = sb.execute_script("""
                    var el = document.querySelector('div.countdown-time');
                    return el ? el.innerText.trim() : null;
                """)
            except:
                remaining_text = "未知"

        return remaining_text

    # ================= ⭐ 核心增强成功判定 =================
    def wait_add_success(self, sb, old_time, server_num, timeout=90):
        start = time.time()

        while time.time() - start < timeout:

            try:
                new_time = self.get_remaining_time(sb)
            except:
                new_time = "未知"

            self.log(f"🧪 判定中: {old_time} → {new_time}")

            # ✔ 成功条件：时间必须变化
            if new_time != old_time and new_time != "未知":
                self.log("🎉 检测到时间变化 = 续期成功")
                return True, new_time

            time.sleep(3)

        return False, old_time

    # ================= 主流程 =================
    def run_single_server(self, server_num, region):

        URL_APP_PANEL = f"https://g4f.gg/{server_num}"

        self.log("=" * 40)
        self.log(f"🚀 开始续期 [{region}] ({server_num})")
        self.log("=" * 40)

        with SB(
            uc=True,
            test=True,
            headed=True,
            headless=False,
            xvfb=False,
            chromium_arg="--no-sandbox,--disable-dev-shm-usage,--disable-gpu,--window-position=0,0,--start-maximized",
            proxy=PROXY_URL if PROXY_URL else None
        ) as sb:

            try:
                self.log("✅ 浏览器已启动！")

                sb.uc_open_with_reconnect(URL_APP_PANEL, reconnect_time=5)
                self.human_wait(6, 10)

                if "login" in sb.get_current_url().lower():
                    self.log("❌ 权限失效")
                    return

                # ================= 续期前时间 =================
                old_time = self.get_remaining_time(sb)
                self.log(f"🕒 续期前: {old_time}")

                # ================= 点击 =================
                self.log("🖱️ 点击 ADD 90 MIN")
                sb.click("//button[contains(., 'ADD 90 MIN')]")

                self.human_wait(5, 8)

                sb.save_screenshot(f"{self.screenshot_dir}/after_click_{server_num}.png")

                # ================= ⭐ 替换：原CF循环 =================
                self.log("🧪 开始成功判定（替代CF逻辑）")

                ok, new_time = self.wait_add_success(sb, old_time, server_num)

                # ================= 截图 =================
                final_path = f"{self.screenshot_dir}/final_{server_num}.png"
                sb.save_screenshot(final_path)

                # ================= 输出 =================
                if ok:
                    self.log(f"✅ 成功：{old_time} → {new_time}")
                else:
                    self.log("❌ 未检测到成功（可能CF阻断或未生效）")

            except Exception as e:
                self.log(f"❌ 运行异常: {e}")
                sb.save_screenshot(f"{self.screenshot_dir}/error_{server_num}.png")

    def run(self):
        if not SERVER_LIST:
            self.log("❌ 未配置 SERVERS")
            return

        for server in SERVER_LIST:
            self.run_single_server(server["num"], server["region"])


if __name__ == "__main__":
    Game4FreeRenewal().run()
