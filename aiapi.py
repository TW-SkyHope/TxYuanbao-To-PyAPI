from flask import Flask, request, jsonify
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from setbrowser import *
import imghdr
import json
import time
import os
import re
import glob
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import base64

app = Flask(__name__)
lock = threading.Lock()

# 初始化浏览器
driver = autoh('https://yuanbao.tencent.com/login')
driver.refresh()
print("浏览器初始化完成")

def validate_image(file_stream):
    """检查图片格式是否有效"""
    file_type = imghdr.what(None, h=file_stream.read(1024))
    file_stream.seek(0)
    return file_type in {'jpeg', 'png', 'gif', 'webp', 'jpg', 'bmp'}

def wait_for_stable_text(element, wait_time=2, timeout=999):
    """等待文本稳定"""
    class TextChecker:
        def __init__(self, element, wait_time):
            self.element = element
            self.wait_time = wait_time
            self.last_text = None
            self.stable_time = None
            self.skip_patterns = [
                r'找到\d+相关资料',
                r'正在分析',
                r'正在处理',
                r'正在生成'
            ]
        
        def should_skip(self, text):
            for pattern in self.skip_patterns:
                if re.search(pattern, text):
                    return True
            return False
        
        def __call__(self, driver):
            current_text = self.element.text
            print(f"当前文本内容: {current_text}")
            
            if self.should_skip(current_text):
                print("检测到中间状态文本，继续等待...")
                return False
                
            if current_text != self.last_text:
                self.last_text = current_text
                self.stable_time = time.time()
                return False
            elif self.stable_time and (time.time() - self.stable_time) >= self.wait_time:
                print(f"文本已稳定: {current_text}")
                return current_text
            return False
    
    try:
        return WebDriverWait(element.parent, timeout).until(
            TextChecker(element, wait_time)
        )
    except Exception as e:
        print(f"等待文本超时: {str(e)}")
        raise TimeoutError(f"等待文本超时（{timeout}秒）")

def get_new_message(driver, timeout=999):
    """获取新消息"""
    print("等待新消息...")
    initial_messages = driver.find_elements(By.CSS_SELECTOR, '.agent-chat__bubble__content')
    known_texts = {msg.text for msg in initial_messages}
    
    class NewMessage:
        def __init__(self, known_texts):
            self.known_texts = known_texts
        
        def __call__(self, driver):
            current_messages = driver.find_elements(By.CSS_SELECTOR, '.agent-chat__bubble__content')
            for msg in current_messages:
                if msg.text not in self.known_texts:
                    print(f"发现新消息: {msg.text}")
                    return msg
            return False
    
    try:
        return WebDriverWait(driver, timeout).until(
            NewMessage(known_texts)
        )
    except Exception:
        print("等待新消息超时")
        raise TimeoutError("等待新消息超时")

def upload_image(driver, image_data):
    """上传图片文件"""
    print("开始上传图片...")
    try:
        temp_file = f"temp_img_{int(time.time()*1000)}.png"
        main_window = driver.current_window_handle
        
        print("点击上传按钮")
        upload_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".index__upload-item___I2o3F"))
        )
        upload_btn.click()
        time.sleep(1)

        print("定位文件输入框")
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".index__input-uploader___L9wop input[type='file']"))
        )

        print("创建临时文件")
        with open(temp_file, "wb") as f:
            f.write(base64.b64decode(image_data))
        
        print("上传文件")
        file_input.send_keys(os.path.abspath(temp_file))
        #虽然这个关闭可能没啥用
        print("关闭上传窗口")
        driver.find_element(By.TAG_NAME, 'body').click()
        driver.switch_to.window(main_window)
        time.sleep(3)
        
        print("清理临时文件")
        os.remove(temp_file)
        print("图片上传完成")
        return True
    except Exception as e:
        print(f"图片上传出错: {str(e)}")
        for temp_file in glob.glob("temp_img_*.png"):
            if os.path.exists(temp_file):
                os.remove(temp_file)
        return False

def upload_files(driver, files):
    """上传多个文件"""
    print(f"准备上传 {len(files)} 个文件")
    try:
        image_types = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        print("打开上传界面")
        upload_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".index__upload-item___ywIAD"))
        )
        upload_btn.click()
        time.sleep(1)
        
        print("点击本地文件上传")
        local_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".index__upload-btn___wGp7B"))
        )
        local_btn.click()
        time.sleep(1)
        
        print("定位文件输入框")
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".index__input-uploader___Vvv7x input[type='file']"))
        )
        
        file_paths = []
        for i, (file_key, file_data) in enumerate(files.items(), 1):
            print(f"处理文件 {i}/{len(files)}")
            original_name = request_data.get(f'filename{i}', 'file')
            ext = os.path.splitext(original_name)[1].lower()
            
            if ext in image_types:
                print(f"跳过图片文件: {original_name}")
                continue
            
            ext = ext if ext else '.bin'
            temp_file = f"temp_{int(time.time()*1000)}_{i}{ext}"
            
            print(f"创建临时文件 {temp_file}")
            with open(temp_file, "wb") as f:
                f.write(base64.b64decode(file_data))
            file_paths.append(os.path.abspath(temp_file))
        
        if file_paths:
            print("开始上传文件")
            file_input.send_keys("\n".join(file_paths))
            time.sleep(2)
            
            errors = driver.find_elements(By.CSS_SELECTOR, ".upload-error-message")
            if errors:
                print(f"上传错误: {errors[0].text}")
                raise Exception(errors[0].text)
        
        print("关闭上传窗口")
        driver.find_element(By.TAG_NAME, 'body').click()
        time.sleep(1)
        
        print("清理临时文件")
        for path in file_paths:
            if os.path.exists(path):
                os.remove(path)
        
        print("文件上传完成")
        return True
    except Exception as e:
        print(f"文件上传失败: {str(e)}")
        for temp_file in glob.glob("temp_*"):
            if os.path.exists(temp_file):
                os.remove(temp_file)
        return False

def change_model(driver, model):
    """切换模型"""
    print(f"准备切换到 {model} 模型")
    try:
        print("点击模型切换按钮")
        switch_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".style__switch-model--arrow___LxKWQ"))
        )
        switch_btn.click()
        time.sleep(1)
        
        print("选择模型")
        # 修改后的选择器，更可靠地定位模型选项
        if model.lower() == "deepseek":
            # 使用包含特定文本的元素
            model_options = driver.find_elements(By.XPATH, "//*[contains(@class, 't-dropdown__item')]")
            for option in model_options:
                if "DeepSeek" in option.text:
                    option.click()
                    break
        elif model.lower() == "hunyuan":
            model_options = driver.find_elements(By.XPATH, "//*[contains(@class, 't-dropdown__item')]")
            for option in model_options:
                if "Hunyuan" in option.text:
                    option.click()
                    break
        else:
            return False
        
        time.sleep(1)
        print("模型切换完成")
        return True
    except Exception as e:
        print(f"模型切换失败: {str(e)}")
        return False
    
def refresh_page():
    """定时刷新页面，防检测(虽然我也不知道有没有检测)"""
    if not lock.acquire(blocking=False):
        print("已有任务运行，跳过刷新")
        return
    try:
        print("执行页面刷新")
        driver.refresh()
    finally:
        lock.release()

scheduler = BackgroundScheduler()
scheduler.add_job(refresh_page, 'interval', seconds=1000)
scheduler.start()

@app.route('/hunyuan', methods=['POST'])
def handle_request():
    """处理请求"""
    print("收到新请求")
    if not lock.acquire(blocking=False):
        print("系统繁忙")
        return "系统繁忙，请稍后再试", 429
    
    try:
        global request_data
        request_data = json.loads(request.get_json())
        if not request_data:
            print("空请求")
            return jsonify({"error": "请求数据不能为空"}), 400
        
        print("处理请求数据")
        response = {}
        session_id = request_data.get('sequence')
        
        current = driver.find_elements(By.CSS_SELECTOR, ".yb-recent-conv-list__item.active")
        if current and current[0].get_attribute("dt-cid") == session_id:
            print("已是当前会话")
        else:
            if session_id == "new":
                print("创建新会话")
                try:
                    new_btn = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".yb-common-nav__new-chat.J_UseGuideNewChat0"))
                    )
                    new_btn[0].click()
                    time.sleep(2)
                    
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".agent-chat__conv--agent-homepage-v2__greeting"))
                    )
                except Exception as e:
                    print(f"创建会话失败: {str(e)}")
                    return jsonify({"error": f"创建会话失败: {str(e)}"}), 500
            else:
                print(f"切换到会话 {session_id}")
                try:
                    session = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"[dt-cid='{session_id}']"))
                    )
                    session[0].click()
                    time.sleep(2)
                except Exception as e:
                    print(f"切换会话失败: {str(e)}")
                    return jsonify({"error": f"切换会话失败: {str(e)}"}), 500
        
        if request_data.get('mode'):
            print(f"切换模型到 {request_data['mode']}")
            if not change_model(driver, request_data['mode']):
                return jsonify({"error": "模型切换失败"}), 500
            

        if request_data.get('picture') and request_data['picture'] != "new":
            print("上传图片")
            if not upload_image(driver, request_data['picture']):
                return jsonify({"error": "图片上传失败"}), 500
        
        files = {k: v for k, v in request_data.items() if re.match(r'file\d+', k)}
        if files:
            print(f"上传 {len(files)} 个文件")
            if not upload_files(driver, files):
                return jsonify({"error": "文件上传失败"}), 500
        
        try:
            print("输入文本")
            input_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ql-editor.ql-blank"))
            )
            input_box.send_keys(request_data.get('text'))
            
            print("发送消息")
            send_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".style__send-btn___ZsLmU"))
            )
            send_btn.click()
            
            print("等待回复")
            new_msg = get_new_message(driver)
            final_text = wait_for_stable_text(new_msg)
            
            print("获取会话ID")
            active = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".yb-recent-conv-list__item.active"))
            )
            current_id = active.get_attribute("dt-cid")
            
            response["id"] = current_id
            response["text"] = final_text
            print("请求处理完成")
            return jsonify(response)
            
        except Exception as e:
            print(f"消息发送失败: {str(e)}")
            return jsonify({"error": f"消息发送失败: {str(e)}"}), 500
            
    except Exception as e:
        print(f"处理出错: {str(e)}")
        return jsonify({"error": f"处理出错: {str(e)}"}), 500
    finally:
        lock.release()
        print("释放锁")

if __name__ == '__main__':
    print("启动服务")
    app.run(host='0.0.0.0', port=8000)