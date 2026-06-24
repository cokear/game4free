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
PROXY_URL = os.getenv("PROXY", "")  # 代理
TG_TOKEN = os.getenv("TG_TOKEN")  # tg通知token
TG_CHAT_ID = os.getenv("TG_CHAT_ID")  # tg通知chat_id
SERVERS = os.getenv("SERVERS", "").strip()  # 服务器列表: NUM1,地区1|NUM2,地区2

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

    def move_mouse_human(self, sb):
        try:
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                sb.slow_click("body", force=True)
                time.sleep(random.uniform(0.5, 1.2))
        except:
            pass

    def get_remaining_time(self, sb):
        remaining_text = "未知"
        try:
            sb.wait_for_element_visible('div.countdown-time', timeout=15)
            time.sleep(2)
            remaining_text = sb.get_text('div.countdown-time').strip()
            self.log(f"✅ 获取剩余时间成功: {remaining_text}")
        except Exception as e:
            self.log(f"⚠️ 获取剩余时间失败: {e}")
            try:
                remaining_text = sb.execute_script("""
                    var el = document.querySelector('div.countdown-time');
                    return el ? el.innerText.trim() : null;
                """)
                if remaining_text:
                    self.log(f"✅ JS获取剩余时间成功: {remaining_text}")
                else:
                    remaining_text = "未知"
            except Exception as js_e:
                self.log(f"⚠️ JS获取失败: {js_e}")
                remaining_text = "未知"
        return remaining_text

    def send_telegram_notify(self, message, photo_path=None):
        if not TG_TOKEN or not TG_CHAT_ID:
            self.log("⚠️ 未配置 TG_TOKEN 或 TG_CHAT_ID，跳过推送。")
            return
        try:
            if photo_path and os.path.exists(photo_path):
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                with open(photo_path, 'rb') as f:
                    requests.post(url, data={'chat_id': TG_CHAT_ID, 'caption': message}, files={'photo': f})
            else:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                requests.post(url, data={'chat_id': TG_CHAT_ID, 'text': message})
            self.log("✅ TG 推送已发送")
        except Exception as e:
            self.log(f"❌ TG 推送失败: {e}")

    def run_single_server(self, server_num, region):
        URL_APP_PANEL = f"https://g4f.gg/{server_num}"

        self.log("=" * 40)
        self.log(f"🚀 开始续期 [{region}] ({server_num})")
        self.log("=" * 40)
        self.log("🎯 正在启动 Chrome 浏览器...")

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

                # IP 检测
                self.log("🌍 正在检测出口 IP...")
                try:
                    sb.open("https://api.ipify.org?format=json")
                    ip_val = json.loads(re.search(r'\{.*\}', sb.get_text("body")).group(0)).get('ip', 'Unknown')
                    parts = ip_val.split('.')
                    self.log(f"✅ 当前出口 IP: {parts[0]}.{parts[1]}.***.{parts[-1]}")
                except:
                    self.log("⚠️ IP 检测跳过...")

                # 打开续期面板
                self.log(f"📂 正在进入续期面板 [{region}] ...")
                sb.uc_open_with_reconnect(URL_APP_PANEL, reconnect_time=5)
                self.human_wait(6, 10)

                if "login" in sb.get_current_url().lower():
                    self.log(f"❌ 权限失效。当前 URL: {sb.get_current_url()}")
                    sb.save_screenshot(f"{self.screenshot_dir}/login_fail_{server_num}.png")
                    self.send_telegram_notify(
                        f"❌ [{region}] 登录状态失效\n🖥️ 编号: {server_num}",
                        f"{self.screenshot_dir}/login_fail_{server_num}.png"
                    )
                    return

                # 获取续期前剩余运行时间
                timestamp_before = self.get_remaining_time(sb)
                self.log(f"🕒 续期前剩余运行时间: {timestamp_before}")
                
                # 点击 '+ ADD 90 MIN'
                try:
                    self.log("🖱️ 正在点击 '+ ADD 90 MIN'...")
                    self.move_mouse_human(sb)
                    sb.wait_for_element('//button[contains(., "ADD 90 MIN")]', timeout=10)
                    sb.click("//button[contains(., 'ADD 90 MIN')]")
                    self.human_wait(6, 10)
                except Exception as e:
                    self.log(f"❌ 未找到 '+ ADD 90 MIN' 按钮: {e}")
                    test2_screenshot = f"{self.screenshot_dir}/test2_{server_num}.png"
                    sb.save_screenshot(test2_screenshot)
                    self.send_telegram_notify(f"未找到 '+ ADD 90 MIN' 按钮 [{region}]", test2_screenshot)
                    return

                # 保存点击后测试截图
                test_screenshot = f"{self.screenshot_dir}/test_{server_num}.png"
                sb.save_screenshot(test_screenshot)
                self.send_telegram_notify(f"服务器{server_num}测试截图", test_screenshot)

                # 验证码处理
                self.human_wait(6, 10)
                #sb.uc_gui_click_captcha()
                sb.uc_gui_handle_captcha()
                self.human_wait(6, 10)

                # 保存最终截图
                final_screenshot = f"{self.screenshot_dir}/final_success_{server_num}.png"
                sb.save_screenshot(final_screenshot)

                # 获取续期后剩余运行时间
                timestamp_after = self.get_remaining_time(sb)
                self.log(f"🕒 续期后剩余运行时间: {timestamp_after}")

                # TG通知
                msg = f"✅ [{region}] 续期成功\n🖥️ 编号: {server_num}\n🕒 续期前剩余运行时间: {timestamp_before}\n🎉 续期后剩余运行时间: {timestamp_after}"
                self.send_telegram_notify(msg, final_screenshot)

            except Exception as e:
                self.log(f"❌ 运行异常: {e}")
                import traceback
                traceback.print_exc()
                sb.save_screenshot(f"{self.screenshot_dir}/error_{server_num}.png")
                self.send_telegram_notify(f"❌ [{region}] 执行异常\n🖥️ 编号: {server_num}", f"{self.screenshot_dir}/error_{server_num}.png")

    def run(self):
        if not SERVER_LIST:
            self.log("❌ 未配置 SERVERS")
            return

        for server in SERVER_LIST:
            self.run_single_server(server["num"], server["region"])


if __name__ == "__main__":
    Game4FreeRenewal().run()
