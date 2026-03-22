from ppadb.client import Client as AdbClient  # pip install pure-python-adb
import cv2
import numpy as np
import time
import configparser
import subprocess
import os
import pyperclip
import requests
from datetime import datetime
from colorama import Fore, Style, init
import socket
# Set master socket timeout to prevent ADB from deadlocking
socket.setdefaulttimeout(15)

import sys
import threading
import pytesseract
import re
from rapidfuzz import fuzz
from collections import Counter
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize colorama
init()
ADB_PATH = os.path.join('bin', 'adb', 'adb.exe')



### clear_screen ###

def clear_screen():
    """ล้างหน้าจอโดยตรวจสอบระบบปฏิบัติการ"""
    os.system('cls' if os.name == 'nt' else 'clear')

### Discord Notification ###

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1401458653126590486/2rxA-PxqKt95RXFFEpoq6zEQ5duR1qszozPQ0WoA0f-4tx_nCdTTESdbdsFeiGv6SLk8"

def send_discord_notification(devices_count):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        
        data = {
            "username": "Fuck Bot Status",
            "embeds": [
                {
                    "title": "🚀 บอทเริ่มทำงานสำเร็จแล้ว!",
                    "description": "ระบบบอทได้ถูกเปิดขึ้นและเชื่อมต่อกับอุปกรณ์ ADB เรียบร้อยแล้ว",
                    "color": 3066993,  # Greenish Blue
                    "fields": [
                        {
                            "name": "📊 จำนวนอุปกรณ์เชื่อมต่อ",
                            "value": f"`{devices_count}` จอ",
                            "inline": True
                        },
                        {
                            "name": "⏰ เวลาเริ่มทำงาน",
                            "value": f"`{timestamp}`",
                            "inline": True
                        },
                        {
                            "name": "🖥️ ชื่อเครื่องคอมพิวเตอร์",
                            "value": f"`{socket.gethostname()}`",
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": "Fuck Bot - การแจ้งเตือนระบบ"
                    }
                }
            ]
        }
        requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=5)
    except Exception:
        pass

### adb search ###

def ImgSearchADB(adb_img, find_img_path, threshold=0.95, method=cv2.TM_CCOEFF_NORMED):
    find_img = cv2.imread(find_img_path, cv2.IMREAD_COLOR)
    needle_w = find_img.shape[1]
    needle_h = find_img.shape[0]
    result = cv2.matchTemplate(adb_img, find_img, method)
    locations = np.where(result >= threshold)
    locations = list(zip(*locations[::-1]))
    rectangles = []
    for loc in locations:
        rect = [int(loc[0]), int(loc[1]), needle_w, needle_h]
        rectangles.append(rect)
        rectangles.append(rect)
    rectangles, _ = cv2.groupRectangles(rectangles, groupThreshold=1, eps=1)
    points = []
    if len(rectangles):
        for (x, y, w, h) in rectangles:
            center_x = x + int(w/2)
            center_y = y + int(h/2)
            points.append((center_x, center_y))
            break
    if len(points) > 0:
        return points
    else:
        return []

### check_retry_play

def check_retry_play(dv):
    """Optimized version of the retry/play checking function"""
    # Define all image targets and their actions
    IMAGE_ACTIONS = [
        ('bin/pic/retry.png', lambda pos: dv.shell(f"input tap {pos[0][0]} {pos[0][1]}")),
        ('bin/pic/lose.png', lambda _: dv.shell("input tap 631 454")),
        ('bin/pic/X2.png', lambda pos: dv.shell(f"input tap {pos[0][0]} {pos[0][1]}")),
        ('bin/pic/play.png', lambda pos: dv.shell(f"input tap {pos[0][0]} {pos[0][1]}")),
        ('bin/pic/shop.png', lambda _: dv.shell("input tap 27 27")),
        ('bin/pic/moveto.png', lambda _: dv.shell("input tap 474 362")),
        ('bin/pic/Puzzle.png', lambda _: dv.shell("input tap 744 105")),
        ('bin/pic/belevel.png', lambda _: dv.shell("input tap 474 360")),
        ('bin/pic/apple3.png', lambda _: dv.shell("input keyevent KEYCODE_BACK"))
    ]
    BLACK_SCREEN_CHECK = 'bin/pic/black.png'
    while True:
        try:
            # Get screen capture once per iteration
            cap = dv.screencap()
            image = np.frombuffer(cap, dtype=np.uint8)
            adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
            # Check for black screen (special handling)
            pos_adb = ImgSearchADB(adb_img, BLACK_SCREEN_CHECK)
            if len(pos_adb) > 0:
                time.sleep(10)
                cap = dv.screencap()
                image = np.frombuffer(cap, dtype=np.uint8)
                adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                pos_adb = ImgSearchADB(adb_img, BLACK_SCREEN_CHECK)
                if len(pos_adb) > 0:
                    dv.shell("am force-stop com.linecorp.LGRGS")
                continue  # Skip other checks if we had black screen
            # Check all other image patterns
            action_taken = False
            for img_path, action in IMAGE_ACTIONS:
                pos_adb = ImgSearchADB(adb_img, img_path)
                if len(pos_adb) > 0:
                    action(pos_adb)
                    action_taken = True
                    break  # Only handle one action per iteration
            # Dynamic sleep based on whether we took action
            sleep_time = 1 if action_taken else 5
            time.sleep(sleep_time)
        except Exception as e:
            time.sleep(5)

########################################################
# ตั้งค่า path แบบ absolute เพื่อความมั่นใจ
project_path = os.path.dirname(os.path.abspath(__file__))
tesseract_path = os.path.join(project_path, "bin", "tesseract-ocr", "tesseract.exe")
# ตั้งค่าให้ pytesseract ใช้ path นี้
pytesseract.pytesseract.tesseract_cmd = tesseract_path
# ตั้งค่า path สำหรับไฟล์ภาษา
os.environ["TESSDATA_PREFIX"] = os.path.join(project_path, "bin", "tesseract-ocr", "tessdata")
#ตัวสแกนข้อความจากรูป

def preprocess_images(gray_img):
    processed_images = []
    # เพิ่มการปรับ contrast แบบ CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img_clahe = clahe.apply(gray_img)
    # 1. Original with CLAHE
    img1 = cv2.resize(img_clahe, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, img1 = cv2.threshold(img1, 150, 255, cv2.THRESH_BINARY)
    processed_images.append(img1)
    # 2. Gaussian Blur + Adaptive Threshold
    img2 = cv2.GaussianBlur(img_clahe, (3, 3), 0)
    img2 = cv2.adaptiveThreshold(img2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 51, 7)
    img2 = cv2.resize(img2, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    processed_images.append(img2)
    # 3. Morphological Opening
    kernel = np.ones((2,2), np.uint8)
    img3 = cv2.morphologyEx(img_clahe, cv2.MORPH_OPEN, kernel)
    img3 = cv2.resize(img3, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, img3 = cv2.threshold(img3, 150, 255, cv2.THRESH_BINARY)
    processed_images.append(img3)
    return processed_images

def clean_text(text):
    """ฟอกข้อความและกรองคำที่ไม่น่าจะเป็นชื่อ"""
    if not text:
        return ""
    # ลบอักขระพิเศษ แต่เก็บตัวอักษร, ตัวเลข, ช่องว่าง และจุด
    text = re.sub(r'[^a-zA-Z0-9\s\.]', '', str(text))
    # ทำให้ช่องว่างเป็นมาตรฐาน
    text = re.sub(r'\s+', ' ', text).strip()
    # แยกคำและกรอง
    words = text.split()
    filtered_words = []
    for word in words:
        # ข้ามคำที่สั้นเกินไป
        if len(word) <= 3:
            continue
        # ข้ามคำที่เป็นตัวเลขล้วน
        if word.isdigit():
            continue
        # ข้ามคำที่มีตัวเลขมากกว่าตัวอักษร
        if sum(c.isdigit() for c in word) > len(word)/2:
            continue
        # ข้ามคำที่มีรูปแบบตัวอักษรซ้ำๆ
        if re.search(r'([a-zA-Z])\1{2,}', word):  # 3+ ตัวอักษรซ้ำ
            continue
        filtered_words.append(word)
    # สร้างข้อความใหม่จากคำที่กรองแล้ว
    cleaned_text = " ".join(filtered_words)
    return cleaned_text.lower()

def ocr_multiple_versions(cropped_gray):
    """ทำ OCR ด้วยเทคนิคการประมวลผลภาพหลายแบบ"""
    processed_images = preprocess_images(cropped_gray)
    texts = []
    custom_config = r'--oem 1 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789. '
    for img in processed_images:
        try:
            ocr_text = pytesseract.image_to_string(img, config=custom_config, lang='eng')
            clean = clean_text(ocr_text)
            if clean:
                texts.append(clean)
        except Exception as e:
            print(f"OCR Error: {str(e)}")
            continue
    return texts

def enhance_ocr_accuracy(text):
    """แก้ไขตัวอักษรที่มักสับสนใน OCR"""
    char_replacements = {
        'i': ['l', '1', '|'],
        'l': ['i', '1', '|'],
        '1': ['i', 'l'],
        'o': ['0'],
        '0': ['o']
    }
    for correct_char, similar_chars in char_replacements.items():
        for similar in similar_chars:
            text = text.replace(similar, correct_char)
    return text

class MuMuADBConnector:
    def __init__(self):
        # Initialize colorama
        init(autoreset=True)
        # Configuration
        self.MAX_MUMU_INSTANCES = 50  # Adjusted to comfortably cover up to 40 instances + buffer
        self.ADB_CONNECT_RETRIES = 3  # Increased retries for better success rate
        self.RETRY_DELAY = 1.5  # Increased delay to give emulators more time to stabilize
    def get_adb_version(self, adb_path):
        """Checks the ADB version."""
        try:
            result = subprocess.run([adb_path, "version"], capture_output=True, text=True, shell=True, check=True, timeout=3)
            # Get only the first line for a cleaner version string, remove colorama codes if any
            return result.stdout.strip().split('\n')[0].replace(Fore.RESET, '').replace(Style.RESET_ALL, '')
        except Exception:
            return "Unknown"
    def fast_port_scan(self, ports):
        open_ports = []
        with ThreadPoolExecutor(max_workers=300) as executor:
            futures = {executor.submit(self.check_port_open, port): port for port in ports}
            for future in as_completed(futures):
                if future.result():
                    open_ports.append(futures[future])
        return open_ports
    def check_port_open(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.05)
            try:
                s.connect(('127.0.0.1', port))
                return True
            except (socket.timeout, ConnectionRefusedError):
                return False
            except Exception:
                return False
    def connect_port(self, adb_path, port):
        address = f"127.0.0.1:{port}"
        try:
            result = subprocess.run(
                [adb_path, "connect", address],
                capture_output=True,
                text=True,
                shell=True,
                timeout=1.0
            )
            output = result.stdout.strip()
            if "connected to" in output:
                return f"Connected to {address}"
            elif "already connected" in output:
                return f"Already connected to {address}"
            else:
                return None
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None
    def retry_connect_port(self, adb_path, port, retries, delay):
        address = f"127.0.0.1:{port}"
        for i in range(retries):
            time.sleep(delay)
            try:
                subprocess.run([adb_path, "disconnect", address], shell=True, capture_output=True, timeout=0.5)
                result = subprocess.run(
                    [adb_path, "connect", address],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=2.0
                )
                output = result.stdout.strip()
                if "connected to" in output:
                    return f"Connected to {address}"
                elif "already connected" in output:
                    current_status = self.get_adb_device_status(adb_path, address)
                    if current_status == "device":
                        return f"Connected to {address}"
                    else:
                        return f"Already connected to {address} (still '{current_status}')"
                if self.get_adb_device_status(adb_path, address) == "device":
                    return f"Connected to {address}"
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
        final_status = self.get_adb_device_status(adb_path, address)
        if final_status == "device":
            return f"Connected to {address}"
        else:
            return f"Failed to connect to {address} (remains '{final_status}')"
    def get_adb_device_status(self, adb_path, address):
        return_status = "not found"
        try:
            result = subprocess.run([adb_path, "devices"], capture_output=True, text=True, shell=True, check=True, timeout=5)
            for line in result.stdout.splitlines():
                line = line.strip()
                if address in line:
                    if "device" in line and "offline" not in line and "unauthorized" not in line:
                        return_status = "device"
                    elif "offline" in line:
                        return_status = "offline"
                    elif "unauthorized" in line:
                        return_status = "unauthorized"
                    else:
                        parts = line.split('\t')
                        if len(parts) > 1:
                            return_status = parts[1].strip()
                        else:
                            return_status = "unknown"
                    break
        except subprocess.TimeoutExpired:
            return_status = "status_check_timed_out"
        except Exception:
            return_status = "status_check_error"
        return return_status
    def get_all_adb_device_status(self, adb_path):
        device_statuses = {}
        try:
            result = subprocess.run([adb_path, "devices"], capture_output=True, text=True, shell=True, check=True, timeout=5)
            for line in result.stdout.splitlines():
                line = line.strip()
                if "device" in line or "offline" in line or "unauthorized" in line:
                    parts = line.split('\t')
                    if len(parts) == 2 and ':' in parts[0]:
                        address = parts[0].strip()
                        status = parts[1].strip()
                        device_statuses[address] = status
        except Exception:
            pass
        return device_statuses
    def connect(self):
        script_path = os.path.dirname(os.path.abspath(__file__))
        adb_path = os.path.join(script_path, "bin", "adb", "adb.exe")
        if not os.path.exists(adb_path):
            print(Fore.RED + "🚫 Error: adb.exe not found at", adb_path)
            #input("🔴 Press Enter to exit...")
            return
        start_time = time.time()
        try:
            subprocess.run([adb_path, "kill-server"], shell=True, capture_output=True, timeout=5)
            subprocess.run([adb_path, "start-server"], shell=True, capture_output=True, timeout=5)
        except subprocess.TimeoutExpired:
            #print(Fore.RED + "❌ ADB server restart timed out. Check ADB installation or running processes.")
            #input("🔴 Press Enter to exit...")
            return
        except Exception as e:
            #print(Fore.RED + f"❌ Error restarting ADB server: {e}")
            #input("🔴 Press Enter to exit...")
            return
        # Port ranges
        mumu_seq_ports = [16384 + i * 32 for i in range(self.MAX_MUMU_INSTANCES + 10)]
        general_adb_ports = list(range(16400, 16501)) + list(range(17000, 18000))
        mumu_lower_ports = list(range(7500, 7750))
        broad_mumu_ports = list(range(16300, 18000))
        ports_to_scan = sorted(list(set(mumu_seq_ports + general_adb_ports + mumu_lower_ports + broad_mumu_ports)))
        open_ports = self.fast_port_scan(ports_to_scan)
        if not open_ports:
            #print(Fore.YELLOW + "⚠️ No open MuMu Player 12 ADB ports found. Ensure emulators are running.")
            #input("🔴 Press Enter to exit...")
            return
        connected_successfully_initial = []
        with ThreadPoolExecutor(max_workers=self.MAX_MUMU_INSTANCES + 10) as executor:
            futures = {executor.submit(self.connect_port, adb_path, port): port for port in open_ports}
            for future in as_completed(futures):
                port = futures[future]
                try:
                    result = future.result()
                    if result:
                        if "Connected to" in result or "Already connected" in result:
                            connected_successfully_initial.append(port)
                except Exception:
                    pass
        current_devices_status = self.get_all_adb_device_status(adb_path)
        offline_ports_for_retry = []
        for port in connected_successfully_initial:
            address = f"127.0.0.1:{port}"
            status = current_devices_status.get(address, "not found")
            if status == "offline":
                offline_ports_for_retry.append(port)
        if offline_ports_for_retry:
            with ThreadPoolExecutor(max_workers=self.MAX_MUMU_INSTANCES + 10) as executor:
                retry_futures = {
                    executor.submit(self.retry_connect_port, adb_path, port, self.ADB_CONNECT_RETRIES, self.RETRY_DELAY): port
                    for port in offline_ports_for_retry
                }
                for future in as_completed(retry_futures):
                    pass
        # Get final device list
        final_devices_output = subprocess.run([adb_path, "devices"], shell=True, capture_output=True, text=True).stdout
        connected_devices = []
        for line in final_devices_output.splitlines():
            line = line.strip()
            if "device" in line and not "offline" in line and not "unauthorized" in line and "127.0.0.1:" in line:
                connected_devices.append(line)
        # Special handling for port 7555
        port_7555_device = [d for d in connected_devices if "127.0.0.1:7555" in d]
        if len(port_7555_device) > 0:
            if len(connected_devices) > 1:
                # If there are multiple devices, remove port 7555
                connected_devices = [d for d in connected_devices if "127.0.0.1:7555" not in d]
            # If only one device and it's 7555, keep it
        # Display results
        print(Fore.MAGENTA + " ===== Connected Devices Status =====")
        if len(connected_devices) > 0:
            for device_line in connected_devices:
                print(Fore.GREEN + device_line)
        else:
            print(Fore.YELLOW + " No devices found in 'device' status.")
        print(Fore.CYAN + f"\n Connected: {len(connected_devices)} Emulator\n")
        elapsed_time = time.time() - start_time
        print(Fore.LIGHTWHITE_EX + f"Scan completed in {elapsed_time:.2f} seconds")
        #print(Fore.GREEN + "Press Enter to exit...")
        time.sleep(1.5)
        clear_screen()

class Login():
    @staticmethod
    def interpolate_color(start_color, end_color, step, total_steps):
        """Calculate intermediate color between start and end colors"""
        r = start_color[0] + (end_color[0] - start_color[0]) * step // total_steps
        g = start_color[1] + (end_color[1] - start_color[1]) * step // total_steps
        b = start_color[2] + (end_color[2] - start_color[2]) * step // total_steps
        return r, g, b
    def LOGIN_MAIN1():
        banner = """
██╗      ██████╗  █████╗ ██████╗ ██╗███╗   ██╗ ██████╗ 
██║     ██╔═══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝ 
██║     ██║   ██║███████║██║  ██║██║██╔██╗ ██║██║  ███╗
██║     ██║   ██║██╔══██║██║  ██║██║██║╚██╗██║██║   ██║
███████╗╚██████╔╝██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝
╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ 
                                                       
            Created by Nattapong :)"""
        start_color = (0, 102, 204)  # Dark blue
        end_color = (173, 216, 230)  # Light blue
        gradient_text = ""
        for i, char in enumerate(banner):
            r, g, b = Login.interpolate_color(start_color, end_color, i, len(banner))
            gradient_text += f"\033[38;2;{r};{g};{b}m{char}"
        gradient_text += Style.RESET_ALL
        print(gradient_text)
        print("")
        time.sleep(3)
        clear_screen()
    def LOGO2():
        banner = """
          .:'
      __ :'__
   .'`__`-'__``.
  :__________.-'
  :_________:
   :_________`-;
    `.__.-.__.'

    Created by Nattapong :)"""
        start_color = (0, 102, 204)  # Dark blue
        end_color = (173, 216, 230)  # Light blue
        gradient_text = ""
        for i, char in enumerate(banner):
            r, g, b = Login.interpolate_color(start_color, end_color, i, len(banner))
            gradient_text += f"\033[38;2;{r};{g};{b}m{char}"
        gradient_text += Style.RESET_ALL
        print(gradient_text)
        print("")

class adb():
    def botnumber1(self, devicsX, bot_num):
        # โหลดค่าตั้งจาก config
        config = configparser.ConfigParser()
        config.read('bin/config.ini')
        gachaselect = config.getint('SETTINGS', 'gachaselect')
        herowant = config.getint('SETTINGS', 'herowant')
        adb = AdbClient()
        dv = adb.device(devicsX)
        if not dv:
            print(f"\\n\\033[91m[BOT {bot_num}] ERROR: Could not connect to {devicsX}. Stopping thread.\\033[0m\\n")
            globals()[f'sw_emu{bot_num}'] = False
            time.sleep(5)
            return
        # สร้าง Thread สำหรับตรวจสอบ Retry/Play
        retry_play_thread = threading.Thread(target=check_retry_play, args=(dv,))
        retry_play_thread.daemon = True
        retry_play_thread.start()
        #mainloop
        while globals().get(f'sw_emu{bot_num}', False):
            # Stage 1: เตรียมเกม
            dv.shell("am force-stop com.linecorp.LGRGS")
            time.sleep(1)
            dv.shell("su -c 'rm -r /data/data/com.linecorp.LGRGS/shared_prefs'")
            time.sleep(2)
            # Stage 2: เปิดเกมจนเจอ guest login
            count_loop = 0
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Glogin.png')
                    if len(pos_adb) > 0:
                        #print('Stage 2: เปิดเกมจนเจอ guest login')
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/icongame.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(0.5)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/apple.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Linegame.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 923 150") #T1
                        time.sleep(1)
                        dv.shell("input tap 924 277") #T2
                        time.sleep(1)
                        dv.shell("input tap 927 363") #T3
                        time.sleep(1)
                        dv.shell("input tap 424 448") #Agree
                        time.sleep(1)
                        dv.shell("input keyevent KEYCODE_BACK")
                        time.sleep(3)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Glogin.png')
                    if len(pos_adb) > 0:
                        #print('Stage 2: เปิดเกมจนเจอ guest login')
                        break
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
            # Stage 3: ล็อกอินเกม
            count_loop = 0
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/SNn.png')
                    if len(pos_adb) > 0:
                        #print('Stage 3: ล็อกอินเกม')
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Glogin.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/login.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/oklogin.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Linegame.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 923 150") #T1
                        time.sleep(1)
                        dv.shell("input tap 924 277") #T2
                        time.sleep(1)
                        dv.shell("input tap 927 363") #T3
                        time.sleep(1)
                        dv.shell("input tap 424 448") #Agree
                        time.sleep(2)
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
            # Stage 4: เล่นหน้าฝึกสอน
            count_loop = 0
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/1s.png')
                    if len(pos_adb) > 0:
                        #print('Stage 4: เล่นหน้าฝึกสอน')
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/mainstate.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Terms.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 924 151")
                        time.sleep(0.5)
                        dv.shell("input tap 924 281")
                        time.sleep(0.5)
                        dv.shell("input tap 924 367")
                        time.sleep(0.5)
                        dv.shell("input tap 420 453")
                        time.sleep(0.5)
                    ################ Clicker all #############
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok3.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    ############################################
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/playttl.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 280 471") #r1
                        time.sleep(0.5)
                        dv.shell("input tap 377 476") #r2
                        time.sleep(0.5)
                        dv.shell("input tap 484 476") #r3
                        time.sleep(0.5)
                        dv.shell("input tap 582 477") #r4
                        time.sleep(0.5)
                        dv.shell("input tap 685 480") #r5
                        time.sleep(0.5)
                        dv.shell("input tap 809 474") #miner
                        time.sleep(0.5)
                        dv.shell("input tap 153 472") #missler
                        time.sleep(0.5)
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
            # Stage 5: ไปเล่นด่าน 1 จนถึงหน้ากาชา
            count_loop = 0
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/gacha.png')
                    if len(pos_adb) > 0:
                        #print('Stage 5: ไปเล่นด่าน 1 จนถึงหน้ากาชา')
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/mainstate.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/1s.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/1s1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/fireball.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/start.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/win.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/SCB.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    ################ Clicker all #############
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok3.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/oklevelup.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    ############################################
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/playstage.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 280 471") #r1
                        time.sleep(0.5)
                        dv.shell("input tap 377 476") #r2
                        time.sleep(0.5)
                        dv.shell("input tap 484 476") #r3
                        time.sleep(0.5)
                        dv.shell("input tap 582 477") #r4
                        time.sleep(0.5)
                        dv.shell("input tap 48 43") #firebal
                        time.sleep(0.5)
                        dv.shell("input tap 153 472") #missler
                        time.sleep(0.5)
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
            # Stage 6: หน้ากาชา จนเจอ save
            count_loop = 0
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/save.png')
                    if len(pos_adb) > 0:
                        #print('Stage 6: หน้ากาชา จนเจอ save')
                        time.sleep(1)
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/X1.png')
                    if len(pos_adb) > 0:
                        time.sleep(1)
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/myteam.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Tor.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/d1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(0.5)
                        dv.shell(f"input swipe 475 200 172 417")
                        time.sleep(0.5)
                        dv.shell(f"input swipe 77 458 477 196")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/myteam1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Ngacha1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/gacha.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    ################ Clicker all #############
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok3.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/oklevelup.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    ############################################
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
            lv3_found=False
            # Stage 7/1: โหลดทรัพยาการ แล้วเล่นอีกรอบ win ออกเกม
            count_loop = 0
            while count_loop < 100 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/save.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/X.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/lv3.png')
                    if len(pos_adb) > 0:
                        #print('lv3_found = True ')
                        lv3_found=True
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/mainstate.png')
                    if len(pos_adb) > 0:
                        #print('# Stage 7/1: โหลดทรัพยาการ ')
                        break
                    ################ Clicker all #############
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok3.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/oklevelup.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    ############################################
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 100:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 100 tries, restarting mainloop...\033[0m')

                continue
            if lv3_found :
                count_loop = 0
                while count_loop < 100 and globals().get(f'sw_emu{bot_num}', False):
                    count_loop += 1
                    try:
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/1s.png')
                        if len(pos_adb) > 0:
                            dv.shell("am force-stop com.linecorp.LGRGS")
                            break
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/1s2.png')
                        if len(pos_adb) > 0:
                            dv.shell("am force-stop com.linecorp.LGRGS")
                            break
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/save.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/X.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/mainstate.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        ############################################
                    except Exception as e:
                        print(f"[BOT {bot_num}] Error: {str(e)}")
                        globals()[f'sw_emu{bot_num}'] = False
                        return
                if count_loop >= 100:

                    print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 100 tries, restarting mainloop...\033[0m')

                    continue
            else:
                # Stage 7/2: โหลดทรัพยาการ แล้วเล่นอีกรอบ win ออกเกม
                count_loop = 0
                while count_loop < 100 and globals().get(f'sw_emu{bot_num}', False):
                    count_loop += 1
                    try:
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/win.png')
                        if len(pos_adb) > 0:
                            #print('Stage 7: โหลดทรัพยาการ แล้วเล่นอีกรอบ win ออกเกม')
                            break
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/save.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/X.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/mainstate.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/1s.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/1s2.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/1s1.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/start.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        ################ Clicker all #############
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok2.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok3.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip1.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/oklevelup.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        ############################################
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/playstage.png')
                        if len(pos_adb) > 0:
                            dv.shell("input tap 280 471") #r1
                            time.sleep(0.5)
                            dv.shell("input tap 377 476") #r2
                            time.sleep(0.5)
                            dv.shell("input tap 484 476") #r3
                            time.sleep(0.5)
                            dv.shell("input tap 582 477") #r4
                            time.sleep(0.5)
                            dv.shell("input tap 48 43") #firebal
                            time.sleep(0.5)
                            dv.shell("input tap 153 472") #missler
                            time.sleep(0.5)
                    except Exception as e:
                        print(f"[BOT {bot_num}] Error: {str(e)}")
                        globals()[f'sw_emu{bot_num}'] = False
                        return
                if count_loop >= 100:

                    print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 100 tries, restarting mainloop...\033[0m')

                    continue
            # Stage 8: เข้าเกม จนเจอ mainstart
            count_loop = 0
            while count_loop < 40 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/mainstate.png')
                    if len(pos_adb) > 0:
                        #print('Stage 8: เข้าเกม จนเจอ mainstart')
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/win.png')
                    if len(pos_adb) > 0:
                        dv.shell("am force-stop com.linecorp.LGRGS")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Re2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/icongame.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Re2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/X.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/X.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    ################ Clicker all #############
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                except Exception as e:
                    print(f"[BOT {bot_num}] Error in Stage 8: {str(e)}")
                    time.sleep(1)
            if count_loop >= 40:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 40 tries, restarting mainloop...\033[0m')

                continue
            # Stage 9/1: 7days รับตั๋ว
            count_loop = 0
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/7days.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/7days1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/7days2.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 839 36")
                        time.sleep(5)
                        #print('Stage 9/1: 7days รับตั๋ว')
                        break
                    ################ Clicker all #############
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok3.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    ############################################
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
           # Stage 9/2: 7days รับตั๋ว
            count_loop = 0
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/acceptall.png')
                    if len(pos_adb) > 0:
                        #print('Stage 9/2: 7days รับตั๋ว')
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/GB.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(0.5)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/BE.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 813 37")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok3.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
            # Stage 10: ไปรับของ ในจดหมาย
            count_loop = 0
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/gacha2.png')
                    if len(pos_adb) > 0:
                        #print('Stage 10: ไปรับของ ในจดหมาย')
                        break
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/gacha.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(0.5)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/acceptall.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/done1.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 802 35")
                        time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/ok2.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(1)
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
            if gachaselect == 1:
                dv.shell("input tap 750 180")
                time.sleep(1)
            elif gachaselect == 2:
                dv.shell("input tap 747 309")
                time.sleep(1)
            elif gachaselect == 3:
                dv.shell("input tap 747 432")
                time.sleep(1)
            hero_names = []  # เก็บชื่อ Hero ทั้งหมดที่พบ
            hero_found = False  # Initialize here to prevent UnboundLocalError
            max_ocr_attempts = int(config.get('SETTINGS', 'max_loop', fallback=40))
            count_loop = 0
            # Stage 11: gacha  และตรวจสอบ
            while count_loop < 50 and globals().get(f'sw_emu{bot_num}', False):
                count_loop += 1
                try:
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/cancel1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        break
                    # ตรวจสอบปุ่ม gacha
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/Ngacha1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(0.5)
                    # ตรวจสอบปุ่ม skip
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/skip1.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(0.5)
                    time.sleep(1)
                    hero_found = False
                    # ตรวจสอบหน้าจอ onemore และทำ OCR
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/onemore.png')
                    if len(pos_adb) > 0:
                        hero_found = False
                        ocr_attempts = 0
                        while ocr_attempts < max_ocr_attempts:
                            ocr_attempts += 1
                            # จับภาพใหม่ทุกครั้ง
                            cap = dv.screencap()
                            image = np.frombuffer(cap, dtype=np.uint8)
                            adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                            # ครอปภาพ
                            gray = cv2.cvtColor(adb_img, cv2.COLOR_BGR2GRAY)
                            top_left = (424, 156)
                            bottom_right = (765, 227)
                            x, y = top_left
                            w = bottom_right[0] - top_left[0]
                            h = bottom_right[1] - top_left[1]
                            cropped_gray = gray[y:y+h, x:x+w]
                            # OCR
                            ocr_results = ocr_multiple_versions(cropped_gray)
                            if not ocr_results:
                                time.sleep(0.1)
                                continue
                            # Vote คำที่ได้
                            counter = Counter(ocr_results)
                            most_common_text, count = counter.most_common(1)[0]
                            # ตรวจจับ Hero
                            for i in range(1, min(herowant, 4) + 1):  # ตรวจสอบไม่เกิน name4
                                try:
                                    hero_entry = config.get('SETTINGS', f'name{i}')
                                    if '=' in hero_entry:
                                        conditions_part, result_name = hero_entry.split('=', 1)
                                        result_name = result_name.strip()
                                        # แยกคำโดยตัดจากช่องว่างและ +
                                        raw_conditions = re.split(r'\+|\s+', conditions_part.strip())
                                        raw_conditions = [c.strip() for c in raw_conditions if c.strip()]
                                        # สร้างข้อความรวมล่วงหน้า
                                        joined_text = " ".join([line.strip() for line in ocr_results if line.strip() != ""]).lower()
                                        all_conditions_met = True
                                        condition_details = []
                                        for cond in raw_conditions:
                                            is_negative = cond.startswith('-')
                                            keyword = cond[1:].strip().lower() if is_negative else cond.strip().lower()
                                            found = keyword in joined_text
                                            if is_negative:
                                                passed = not found  # ห้ามพบ
                                            else:
                                                passed = found      # ต้องพบ
                                            condition_details.append({
                                                'condition': cond,
                                                'found': found,
                                                'passed': passed,
                                                'type': 'NEG' if is_negative else 'POS'
                                            })
                                            if not passed:
                                                all_conditions_met = False
                                        if all_conditions_met:
                                            hero_found = True
                                            hero_names.append(result_name)
                                            break
                                    else:
                                        hero_name = hero_entry.strip().lower()
                                        max_score = max(
                                            fuzz.partial_ratio(hero_name, ocr_text.lower())
                                            for ocr_text in ocr_results
                                        )
                                        if max_score >= 92:
                                            hero_found = True
                                            hero_names.append(hero_entry.strip())
                                            break
                                except Exception as hero_error:
                                    print(f"{Fore.RED}[BOT {bot_num}] Error to scan Hero {i}: {str(hero_error)}{Style.RESET_ALL}")
                                    continue
                            if hero_found:
                                break  # ออกจาก while OCR ทันที เพราะเจอแล้ว
                            time.sleep(0.1)
                    time.sleep(1)
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/gacha3.png')
                    if len(pos_adb) > 0:
                        dv.shell("input tap 550 407")
                        time.sleep(0.5)
                    # ตรวจสอบปุ่ม onemore และ gacha3
                    cap = dv.screencap()
                    image = np.frombuffer(cap, dtype=np.uint8)
                    adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    pos_adb = ImgSearchADB(adb_img, 'bin/pic/onemore.png')
                    if len(pos_adb) > 0:
                        dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                        time.sleep(0.5)
                except Exception as e:
                    print(f"[BOT {bot_num}] Error: {str(e)}")
                    globals()[f'sw_emu{bot_num}'] = False
                    return
            if count_loop >= 50:

                print(f'\033[31m[BOT {bot_num}] STAGE TIMEOUT! Exceeded 50 tries, restarting mainloop...\033[0m')

                continue
# ★★★★★ จบ Stage 5 แล้ว ทำการเก็บไฟล์ ★★★★★
            hero_name_str = "_".join(hero_names)
            # บันทึกบัญชีหรือเริ่มใหม่
            if hero_found:
                # รอจนกว่าจะเจอหน้าหลัก
                while globals().get(f'sw_emu{bot_num}', False):
                    try:
                        cap = dv.screencap()
                        image = np.frombuffer(cap, dtype=np.uint8)
                        adb_img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/coppyid.png')
                        if len(pos_adb) > 0:
                            break
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/cancel1.png')
                        if len(pos_adb) > 0:
                            dv.shell("input tap 406 355")
                            time.sleep(1)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/V.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/V2.png')
                        if len(pos_adb) > 0:
                            dv.shell("input tap 900 102")
                            time.sleep(1)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/settings.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/settings2.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/settings3.png')
                        if len(pos_adb) > 0:
                            dv.shell(f"input tap {pos_adb[0][0]} {pos_adb[0][1]}")
                            time.sleep(1)
                        pos_adb = ImgSearchADB(adb_img, 'bin/pic/end1.png')
                        if len(pos_adb) > 0:
                            dv.shell("input tap 476 359")
                            time.sleep(1)
                    except Exception as e:
                        print(f"[BOT] Error: {str(e)}")
                        time.sleep(1)
                # ดึงข้อมูลบัญชี
                game_name = pyperclip.paste()
                os.makedirs("backup", exist_ok=True)
                # คัดลอกไฟล์บัญชี (ไม่แสดงผลลัพธ์)
                subprocess.run([
                    'bin/adb/adb.exe', "-s", devicsX, "shell", "su -c",
                    "'cp /data/data/com.linecorp.LGRGS/shared_prefs/_LINE_COCOS_PREF_KEY.xml /sdcard/temp_root_backup.xml'"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
                # ดึงไฟล์จากอุปกรณ์ (ไม่แสดงผลลัพธ์)
                subprocess.run([
                    'bin/adb/adb.exe', "-s", devicsX, "pull",
                    "/sdcard/temp_root_backup.xml",
                    f"backup/{hero_name_str}_{game_name}_LINE_COCOS_PREF_KEY.xml"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # ลบไฟล์ชั่วคราว (ไม่แสดงผลลัพธ์)
                subprocess.run([
                    'bin/adb/adb.exe', "-s", devicsX, "shell", "su -c",
                    "'rm /sdcard/temp_root_backup.xml'"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
            else:
                dv.shell("am force-stop com.linecorp.LGRGS")
                time.sleep(1)
if __name__ == '__main__':
    Login.LOGIN_MAIN1()
    Login.LOGO2()
    connector = MuMuADBConnector()
    connector.connect()
    clear_screen()
    MAX_EMULATORS = 50
    def get_connected_devices():
        """ฟังก์ชันตรวจสอบอุปกรณ์ที่เชื่อมต่อผ่าน ADB"""
        try:
            result = subprocess.run(['bin/adb/adb.exe', 'devices'], stdout=subprocess.PIPE, text=True, timeout=5)
            devices = []
            for line in result.stdout.splitlines():
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    # ตรวจสอบว่าไม่ใช่ 127.0.0.1:7555
                    if device_id != "127.0.0.1:7555":
                        devices.append(device_id)
            return devices[:MAX_EMULATORS]  # ตัดเฉพาะ 50 อันแรก
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []
    # ตรวจสอบการเชื่อมต่ออุปกรณ์ครั้งแรก
    emu_idpass = get_connected_devices()
    if emu_idpass:
        send_discord_notification(len(emu_idpass))
    if not emu_idpass:
        print(f"{Fore.RED}No devices connected!{Style.RESET_ALL}")
        time.sleep(1)
        print(f"{Fore.YELLOW}Use ADB_MANAGER TO CHECK.{Style.RESET_ALL}")
        time.sleep(10)
        sys.exit(1)
    # แจ้งเตือนหากมี Emulator เกินจำนวนที่กำหนด
    all_devices = subprocess.run(['bin/adb/adb.exe', 'devices'], stdout=subprocess.PIPE, text=True).stdout
    # นับเฉพาะ device ที่ไม่ใช่ 127.0.0.1:7555
    actual_count = sum(1 for line in all_devices.splitlines() if '\tdevice' in line and line.split('\t')[0] != "127.0.0.1:7555")
    if actual_count > MAX_EMULATORS:
        print(f"{Fore.YELLOW}Warning: Found {actual_count} devices, but the free version only allows up to {MAX_EMULATORS}.{Style.RESET_ALL}")
        time.sleep(5)
    # สร้างตัวแปรสถานะและ Thread สำหรับแต่ละบอท (ไม่เกิน MAX_EMULATORS)
    bot_status = {i: 0 for i in range(1, len(emu_idpass)+1)}
    bot_errors = {i: 0 for i in bot_status}
    bot_threads = {i: None for i in bot_status}
    last_device_count = len(emu_idpass)
    def bot_wrapper(device_id, bot_num):
        """ฟังก์ชันหลักสำหรับควบคุมการทำงานของบอทแต่ละตัว"""
        while globals().get(f'sw_emu{bot_num}', False):
            try:
                # ตรวจสอบจำนวนอุปกรณ์ก่อนทำงาน
                current_count = len(get_connected_devices())
                if current_count != last_device_count:
                    globals()[f'sw_emu{bot_num}'] = False
                    time.sleep(5)
                    return
                adb().botnumber1(device_id, bot_num)
                bot_errors[bot_num] = 0  # รีเซ็ตจำนวนข้อผิดพลาดเมื่อทำงานสำเร็จ
            except cv2.error as e:
                bot_errors[bot_num] = bot_errors.get(bot_num, 0) + 1
                if bot_errors[bot_num] <= 3:
                    print(f"{Fore.RED}BOT {bot_num} CV2 Error: {e} "
                        f"(Attempt {bot_errors[bot_num]}/3){Style.RESET_ALL}")
                time.sleep(5)
            except Exception as e:
                import traceback
                bot_errors[bot_num] = bot_errors.get(bot_num, 0) + 1
                if bot_errors[bot_num] <= 3:
                    print(f"{Fore.RED}BOT {bot_num} Unexpected Error: {e}")
                    traceback.print_exc()
                    print(f"(Attempt {bot_errors[bot_num]}/3){Style.RESET_ALL}")
                time.sleep(10)
            # ถ้า error เกิน 10 ครั้ง ให้หยุด thread แต่ไม่เปลี่ยน bot_status
            if bot_errors.get(bot_num, 0) > 20:
                print(f"{Fore.RED}BOT {bot_num} stopped due to too many errors!{Style.RESET_ALL}")
                globals()[f'sw_emu{bot_num}'] = False
                return
    def check_and_restart_bots():
        global emu_idpass, bot_status, bot_threads, bot_errors, last_device_count, AUTO_START
        while True:
            # โหลดค่า AUTO_START ใหม่ทุกครั้ง
            config = configparser.ConfigParser()
            config.read('bin/config.ini')
            AUTO_START = config.getboolean('SETTINGS', 'autoStart', fallback=False)
            #print(f"{Fore.MAGENTA}Current AUTO_START setting: {AUTO_START}{Style.RESET_ALL}")
            current_devices = get_connected_devices()
            current_count = len(current_devices)
            if current_count != last_device_count:
                clear_screen()
                print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}            [ BOT CONTROL PANEL ]{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}[!] Device count changed from {last_device_count} to {current_count}{Style.RESET_ALL}")
                removed = [d for d in emu_idpass if d not in current_devices]
                added = [d for d in current_devices if d not in emu_idpass]
                # หยุดบอทที่อุปกรณ์หายไป
                for idx, dev in enumerate(emu_idpass, start=1):
                    if dev in removed:
                        globals()[f'sw_emu{idx}'] = False
                        if bot_threads.get(idx):
                            bot_threads[idx].join(timeout=1)  # รอให้ thread จบการทำงาน
                # อัปเดตข้อมูลอุปกรณ์
                old_emu = emu_idpass
                emu_idpass = current_devices
                last_device_count = current_count
                # สร้าง mapping ใหม่
                new_status = {}
                new_errors = {}
                new_threads = {}
                device_mapping = {}  # เก็บการแมปจากอุปกรณ์เดิมไปใหม่
                # สร้าง mapping สำหรับอุปกรณ์เดิม
                for new_idx, dev in enumerate(emu_idpass, start=1):
                    if dev in old_emu:
                        old_idx = old_emu.index(dev) + 1
                        device_mapping[old_idx] = new_idx
                        new_status[new_idx] = bot_status[old_idx]
                        new_errors[new_idx] = bot_errors[old_idx]
                        new_threads[new_idx] = bot_threads[old_idx]
                    else:
                        new_status[new_idx] = 1 if AUTO_START else 0
                        new_errors[new_idx] = 0
                        new_threads[new_idx] = None
                bot_status = new_status
                bot_errors = new_errors
                bot_threads = new_threads
                # แสดงเมนู
                clear_screen()
                running_bots = sum(1 for st in bot_status.values() if st == 1)
                stopped_bots = len(emu_idpass) - running_bots
                print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}            [ BOT CONTROL PANEL ]{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}[+] Total Devices: {Fore.CYAN}{len(emu_idpass)}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}[*] Running: {running_bots}{Style.RESET_ALL}   |   {Fore.RED}[-] Stopped: {stopped_bots}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'-'*50}{Style.RESET_ALL}")
                
                for i in range(1, len(emu_idpass)+1):
                    st_text = "RUNNING" if bot_status[i] == 1 else "STOPPED"
                    st_color = Fore.GREEN if bot_status[i] == 1 else Fore.RED
                    icon = "[+]" if bot_status[i] == 1 else "[-]"
                    errors = bot_errors.get(i, 0)
                    print(f"  [{i:02d}] BOT {i:<2} {st_color}{icon} {st_text:<7}{Style.RESET_ALL} | Errors: {errors}")
                    
                print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}[1] Start All Bots{Style.RESET_ALL}")
                print(f"{Fore.RED}[2] Stop All Bots{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}[3] Individual Bot Control{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}[4] Refresh Connections (ADB){Style.RESET_ALL}")
                print(f"{Fore.WHITE}[0] Exit Program{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                # เริ่มบอทใหม่เฉพาะตัวที่เพิ่มมาและต้องการให้เริ่มอัตโนมัติ
                for dev in added:
                    idx = emu_idpass.index(dev) + 1
                    if AUTO_START:
                        #print(f"{Fore.GREEN}Starting BOT {idx} for new device {dev}{Style.RESET_ALL}")
                        globals()[f'sw_emu{idx}'] = True
                        bot_status[idx] = 1
                        bot_errors[idx] = 0
                        t = threading.Thread(
                            target=bot_wrapper,
                            args=(dev, idx),
                            daemon=True
                        )
                        bot_threads[idx] = t
                        t.start()
                    else:
                        time.sleep(1)
                        #print(f"{Fore.YELLOW}New device  {dev} detected (set to manual start){Style.RESET_ALL}")
                # รีสตาร์ทบอทที่ควรทำงานแต่หยุดไป
                for i, st in bot_status.items():
                    if st == 1:
                        th = bot_threads.get(i)
                        if th is None or not th.is_alive():
                            print(f"{Fore.YELLOW}Restarting BOT {i}{Style.RESET_ALL}")
                            globals()[f'sw_emu{i}'] = True
                            t = threading.Thread(
                                target=bot_wrapper,
                                args=(emu_idpass[i-1], i),
                                daemon=True
                            )
                            bot_threads[i] = t
                            t.start()
            else:
                # ตรวจสอบบอทที่หยุดทำงานระหว่างรอบ
                for i, st in bot_status.items():
                    if st == 1:
                        th = bot_threads.get(i)
                        if th is None or not th.is_alive():
                            print(f"{Fore.YELLOW}Restarting stopped BOT {i}{Style.RESET_ALL}")
                            globals()[f'sw_emu{i}'] = True
                            t = threading.Thread(
                                target=bot_wrapper,
                                args=(emu_idpass[i-1], i),
                                daemon=True
                            )
                            bot_threads[i] = t
                            t.start()
            time.sleep(10)
    # เริ่ม Thread ตรวจสอบ
    threading.Thread(target=check_and_restart_bots, daemon=True).start()
    # เมนูควบคุมหลัก
    while True:
        os.system('cls')
        running_bots = sum(1 for st in bot_status.values() if st == 1)
        stopped_bots = len(emu_idpass) - running_bots
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}            [ BOT CONTROL PANEL ]{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}[+] Total Devices: {Fore.CYAN}{len(emu_idpass)}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[*] Running: {running_bots}{Style.RESET_ALL}   |   {Fore.RED}[-] Stopped: {stopped_bots}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'-'*50}{Style.RESET_ALL}")
        
        for i in range(1, len(emu_idpass)+1):
            st_text = "RUNNING" if bot_status[i] == 1 else "STOPPED"
            st_color = Fore.GREEN if bot_status[i] == 1 else Fore.RED
            icon = "[+]" if bot_status[i] == 1 else "[-]"
            errors = bot_errors.get(i, 0)
            print(f"  [{i:02d}] BOT {i:<2} {st_color}{icon} {st_text:<7}{Style.RESET_ALL} | Errors: {errors}")
            
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[1] Start All Bots{Style.RESET_ALL}")
        print(f"{Fore.RED}[2] Stop All Bots{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}[3] Individual Bot Control{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[4] Refresh Connections (ADB){Style.RESET_ALL}")
        print(f"{Fore.WHITE}[0] Exit Program{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        try:
            choice = int(input(f"{Fore.CYAN}Select option >> {Style.RESET_ALL}"))
            if choice == 0:
                for i in bot_status:
                    globals()[f'sw_emu{i}'] = False
                print(f"{Fore.YELLOW}Stopping all bots before exit...{Style.RESET_ALL}")
                time.sleep(2)
                sys.exit(0)
            elif choice == 1:  # Start all
                for i in range(1, len(emu_idpass)+1):
                    if bot_status[i] == 0:
                        bot_status[i] = 1
                        globals()[f'sw_emu{i}'] = True
                        bot_errors[i] = 0
                        # สตาร์ทถ้ายังไม่มี thread หรือ thread ตาย
                        th = bot_threads.get(i)
                        if th is None or not th.is_alive():
                            t = threading.Thread(
                                target=bot_wrapper,
                                args=(emu_idpass[i-1], i),
                                daemon=True
                            )
                            bot_threads[i] = t
                            t.start()
                print(f"{Fore.GREEN}All bots started!{Style.RESET_ALL}")
                time.sleep(1)
            elif choice == 2:  # Stop all
                for i in bot_status:
                    bot_status[i] = 0
                    globals()[f'sw_emu{i}'] = False
                print(f"{Fore.RED}All bots stopped!{Style.RESET_ALL}")
                time.sleep(1)
            elif choice == 3:  # Individual control
                bot_num_input = input(f"{Fore.CYAN}Select bot number to Toggle Start/Stop (0 to cancel) >> {Style.RESET_ALL}")
                try:
                    bot_num = int(bot_num_input)
                except ValueError:
                    print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
                    time.sleep(1)
                    continue
                if bot_num == 0:
                    continue
                if bot_num < 1 or bot_num > len(emu_idpass):
                    print(f"{Fore.MAGENTA}Invalid bot number!{Style.RESET_ALL}")
                    time.sleep(1)
                    continue
                if bot_status[bot_num] == 1:
                    # stop this bot
                    bot_status[bot_num] = 0
                    globals()[f'sw_emu{bot_num}'] = False
                    print(f"{Fore.RED}BOT {bot_num} stopped!{Style.RESET_ALL}")
                else:
                    # start this bot
                    bot_status[bot_num] = 1
                    globals()[f'sw_emu{bot_num}'] = True
                    bot_errors[bot_num] = 0
                    th = bot_threads.get(bot_num)
                    if th is None or not th.is_alive():
                        t = threading.Thread(
                            target=bot_wrapper,
                            args=(emu_idpass[bot_num-1], bot_num),
                            daemon=True
                        )
                        bot_threads[bot_num] = t
                        t.start()
                    print(f"{Fore.GREEN}BOT {bot_num} started!{Style.RESET_ALL}")
                time.sleep(1)
            elif choice == 4:  # Manual refresh
                print(f"{Fore.YELLOW}Manually refreshing all connections...{Style.RESET_ALL}")
                # stop all threads
                for i in bot_status:
                    bot_status[i] = 0
                    globals()[f'sw_emu{i}'] = False
                time.sleep(2)
                # refresh device list
                new_emu_idpass = get_connected_devices()
                if not new_emu_idpass:
                    print(f"{Fore.RED}No devices found after refresh!{Style.RESET_ALL}")
                    time.sleep(2)
                    continue
                emu_idpass = new_emu_idpass
                bot_status = {i: 0 for i in range(1, len(emu_idpass)+1)}
                bot_errors = {}
                # รีเซ็ต bot_threads ให้มี key ใหม่ทั้งหมด
                bot_threads = {i: None for i in range(1, len(emu_idpass)+1)}
                last_device_count = len(emu_idpass)
                print(f"{Fore.GREEN}Manual refresh completed! Found {len(emu_idpass)} devices.{Style.RESET_ALL}")
                time.sleep(2)
            else:
                print(f"{Fore.YELLOW}Invalid option!{Style.RESET_ALL}")
                time.sleep(1)
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number!{Style.RESET_ALL}")
            time.sleep(1)