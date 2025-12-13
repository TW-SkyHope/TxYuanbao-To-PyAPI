# aiapi.py
from flask import Flask, request, jsonify
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from setbrowser import *
import json
import time
import os
import re
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import base64
import logging
import signal
import traceback
from collections import deque
import setbrowser

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# 全局变量管理多个浏览器标签页

tabs = deque()  # 存储可用标签页
tab_lock = threading.Lock()  # 标签页管理锁
tab_counter = 0  # 标签页计数器

class YuanbaoAutomation:
    def __init__(self, tab_id, max_retries=3):
        self.tab_id = tab_id
        self.driver = None
        self.max_retries = max_retries
        self.initialize_driver()
        
        self.lock = threading.Lock()
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.refresh_page, 'interval', seconds=600)
        self.scheduler.start()
    
    def initialize_driver(self):
        for attempt in range(1, self.max_retries + 1):
                logging.info(f"标签页 {self.tab_id}: 尝试初始化浏览器 ({attempt}/{self.max_retries})")
                self.driver = autoh('https://yuanbao.tencent.com/login')
                self.driver.refresh()
                logging.info(f"标签页 {self.tab_id}: 浏览器初始化完成")
                return
    
    def refresh_page(self):
        if not self.lock.acquire(blocking=False):
            logging.info(f"标签页 {self.tab_id}: 已有任务运行，跳过刷新")
            return
        
        try:
            logging.info(f"标签页 {self.tab_id}: 执行页面刷新")
            self.driver.refresh()
            time.sleep(2)
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 页面刷新失败: {str(e)}")
            try:
                self.driver.quit()
            except:
                pass
            self.initialize_driver()
        finally:
            self.lock.release()
    
    def wait_for_stable_text(self, element, wait_time=2, timeout=120):
        class TextChecker:
            def __init__(self, element, wait_time, tab_id):
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
                self.tab_id = tab_id
            
            def should_skip(self, text):
                for pattern in self.skip_patterns:
                    if re.search(pattern, text):
                        return True
                return False
            
            def __call__(self, driver):
                try:
                    current_text = self.element.text
                    logging.debug(f"标签页 {self.tab_id}: 当前文本内容: {current_text[:100]}...")
                    
                    if self.should_skip(current_text):
                        logging.debug(f"标签页 {self.tab_id}: 检测到中间状态文本，继续等待...")
                        return False
                        
                    if current_text != self.last_text:
                        self.last_text = current_text
                        self.stable_time = time.time()
                        return False
                    elif self.stable_time and (time.time() - self.stable_time) >= self.wait_time:
                        logging.debug(f"标签页 {self.tab_id}: 文本已稳定: {current_text[:100]}...")
                        return current_text
                    return False
                except Exception as e:
                    logging.warning(f"标签页 {self.tab_id}: 文本检查出错: {str(e)}")
                    return False
        
        try:
            return WebDriverWait(element.parent, timeout).until(
                TextChecker(element, wait_time, self.tab_id)
            )
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 等待文本超时: {str(e)}")
            try:
                return element.text
            except:
                raise TimeoutError(f"等待文本超时（{timeout}秒）")
    
    def get_new_message(self, timeout=120):
        logging.info(f"标签页 {self.tab_id}: 等待新消息...")
        try:
            initial_messages = self.driver.find_elements(By.CSS_SELECTOR, '.agent-chat__bubble__content')
            known_texts = {msg.text for msg in initial_messages}
            
            end_time = time.time() + timeout
            while time.time() < end_time:
                try:
                    current_messages = self.driver.find_elements(By.CSS_SELECTOR, '.agent-chat__bubble__content')
                    for msg in current_messages:
                        try:
                            msg_text = msg.text
                            if msg_text and msg_text not in known_texts:
                                logging.info(f"标签页 {self.tab_id}: 发现新消息: {msg_text[:50]}...")
                                return msg
                        except:
                            continue
                except Exception as e:
                    logging.warning(f"标签页 {self.tab_id}: 检查新消息时出错: {str(e)}")
                
                time.sleep(1)
            
            raise TimeoutError("等待新消息超时")
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 获取新消息失败: {str(e)}")
            raise
    
    def upload_image(self, image_data):
        logging.info(f"标签页 {self.tab_id}: 开始上传图片...")
        temp_file = None
        try:
            temp_file = f"temp_img_{int(time.time()*1000)}.png"
            
            # 尝试多种方式定位上传按钮
            selectors = [
                "span[class*='upload-icon']",
            ]
            
            upload_btn = None
            for selector in selectors:
                try:
                    upload_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not upload_btn:
                raise Exception("无法定位上传按钮")
                
            upload_btn.click()
            time.sleep(1)

            # 定位文件输入框
            
            file_input_selectors = [
                "input[accept*='capture=filesystem,.jpg,.jpeg,.png,.webp,.bmp,.gif']",
            ]
            
            file_input = None
            for selector in file_input_selectors:
                try:
                    file_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not file_input:
                raise Exception("无法定位文件输入框")
            
            # 创建临时文件
            with open(temp_file, "wb") as f:
                # 确保正确处理base64编码
                if image_data.startswith('data:image'):
                    # 移除base64前缀
                    header, encoded = image_data.split(",", 1)
                    image_bytes = base64.b64decode(encoded)
                else:
                    image_bytes = base64.b64decode(image_data)
                    
                f.write(image_bytes)
            
            # 上传文件
            file_input.send_keys(os.path.abspath(temp_file))
            time.sleep(5)
            
            logging.info(f"标签页 {self.tab_id}: 图片上传完成")
            return True
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 图片上传出错: {str(e)}")
            return False
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def upload_files(self, files, request_data):
        logging.info(f"标签页 {self.tab_id}: 准备上传 {len(files)} 个文件")
        temp_files = []
        try:
            image_types = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            
            # 尝试多种方式定位上传按钮
            selectors = [
                "span[class*='upload-icon']",
            ]
            
            upload_btn = None
            for selector in selectors:
                try:
                    upload_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not upload_btn:
                raise Exception("无法定位上传按钮")
                
            upload_btn.click()
            time.sleep(1)
            
            # 点击本地文件上传
            local_btn_selectors = [
                "span[class*='upload-icon']",
            ]
            
            local_btn = None
            for selector in local_btn_selectors:
                try:
                    local_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not local_btn:
                raise Exception("无法定位本地上传按钮")
                
            local_btn.click()
            time.sleep(1)
            
            # 定位文件输入框
            file_input_selectors = [
                "input[accept*='capture=filesystem,,.pdf,.xls,.xlsx,.ppt,.pptx,.doc,.docx,.txt,.csv,.text,.bat,.c,.cpp,.cs,.css,.go,.h,.hpp,.ini,.java,.js,.json,.log,.lua,.md,.php,.pl,.py,.rb,.sh,.sql,.swift,.tex,.toml,.vue,.yaml,.yml,.xml,.html']",
            ]
            
            file_input = None
            for selector in file_input_selectors:
                try:
                    file_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not file_input:
                raise Exception("无法定位文件输入框")
            
            # 解析 request_data：如果是字符串则解析为字典
            parsed_request_data = request_data
            if isinstance(request_data, str):
                try:
                    parsed_request_data = json.loads(request_data)
                    logging.info(f"标签页 {self.tab_id}: 成功解析JSON请求数据: {parsed_request_data}")
                except json.JSONDecodeError as e:
                    logging.error(f"标签页 {self.tab_id}: JSON解析失败: {str(e)}")
                    raise Exception(f"请求数据格式错误: {str(e)}")
            
            file_paths = []
            for i, (file_key, file_data) in enumerate(files.items(), 1):
                logging.info(f"标签页 {self.tab_id}: 处理文件 {i}/{len(files)}")
                
                # 安全获取文件名 - 支持字典和解析后的字典
                filename = f'file{i}'  # 默认值
                
                # 检查 parsed_request_data 的类型并获取文件名
                if isinstance(parsed_request_data, dict):
                    filename = parsed_request_data.get(f'filename{i}', f'file{i}')
                elif hasattr(parsed_request_data, 'get'):
                    filename = parsed_request_data.get(f'filename{i}', f'file{i}')
                else:
                    logging.warning(f"标签页 {self.tab_id}: 无法从请求数据中获取filename{i}，使用默认文件名")
                
                ext = os.path.splitext(filename)[1].lower()
                
                if ext in image_types:
                    logging.info(f"标签页 {self.tab_id}: 跳过图片文件: {filename}")
                    continue
                
                # 使用原始文件名（来自request_data）作为临时文件名
                temp_file = filename  # 直接使用request_data中的文件名
                temp_files.append(temp_file)
                
                logging.info(f"标签页 {self.tab_id}: 创建临时文件 {temp_file}")
                with open(temp_file, "wb") as f:
                    f.write(base64.b64decode(file_data))
                file_paths.append(os.path.abspath(temp_file))
            
            if file_paths:
                logging.info(f"标签页 {self.tab_id}: 开始上传文件")
                file_input.send_keys("\n".join(file_paths))
                time.sleep(5)
                
                # 检查上传错误
                error_selectors = [
                    ".upload-error-message",
                    ".error-message",
                    ".alert-danger"
                ]
                
                for selector in error_selectors:
                    try:
                        errors = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if errors:
                            error_msg = errors[0].text
                            logging.error(f"标签页 {self.tab_id}: 上传错误: {error_msg}")
                            raise Exception(error_msg)
                    except:
                        continue
            
            # 关闭上传窗口
            try:
                self.driver.find_element(By.TAG_NAME, 'body').click()
            except:
                pass
            time.sleep(1)
            
            logging.info(f"标签页 {self.tab_id}: 文件上传完成")
            return True
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 文件上传失败: {str(e)}")
            return False
        finally:
            # 清理临时文件
            for path in temp_files:
                if os.path.exists(path):
                    try:
                        print(f"删除临时文件: {path}")
                    except:
                        pass
    
    def change_model(self, model):
        logging.info(f"标签页 {self.tab_id}: 准备切换到 {model} 模型")
        try:
            # 修复：使用正确的元素定位方法
            selectors = self.driver.find_element(By.XPATH, "//div[@dt-button-id='model_switch' and @dt-mod-id='main_mod']")
            selectors.click()
            time.sleep(1)
            
            # 选择模型
            model_options = elements = self.driver.find_elements(By.XPATH, "//*[@class='ybc-model-select-dropdown-item-name']")

            found = False
            for option in model_options:
                try:
                    option_text = option.text
                    if model.lower() == "deepseek" and "DeepSeek" in option_text:
                        option.click()
                        found = True
                        break
                    elif model.lower() == "hunyuan" and "Hunyuan" in option_text:
                        option.click()
                        found = True
                        break
                except:
                    continue
            
            if not found:
                logging.error(f"标签页 {self.tab_id}: 未找到匹配的模型选项: {model}")
                return False
                
            time.sleep(1)
            logging.info(f"标签页 {self.tab_id}: 模型切换完成")
            return True
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 模型切换失败: {str(e)}")
            return False
    
    def handle_session(self, session_id):
        """处理会话切换 - 修复版本"""
        try:
            logging.info(f"标签页 {self.tab_id}: 处理会话: {session_id}")
            
            # 检查当前会话
            current_selectors = [
                ".yb-recent-conv-list__item.active",
                ".active-conversation",
                "[data-active='true']"
            ]
            
            current = None
            for selector in current_selectors:
                try:
                    logging.debug(f"标签页 {self.tab_id}: 检查当前会话选择器: {selector}")
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        current = elements
                        logging.debug(f"标签页 {self.tab_id}: 找到当前会话元素")
                        break
                except Exception as e:
                    logging.debug(f"标签页 {self.tab_id}: 检查当前会话选择器失败: {e}")
                    continue
            
            if current and current[0].get_attribute("dt-cid") == session_id:
                logging.info(f"标签页 {self.tab_id}: 已是当前会话")
                return True
            
            if session_id == "new":
                logging.info(f"标签页 {self.tab_id}: 创建新会话")
                # 尝试多种方式定位新建会话按钮
                new_btn_selectors = [
                    ".yb-tencent-yuanbao-list__item .yb-tencent-yuanbao-list__logo",
                    ".new-conversation",
                    "[data-testid='new-conversation']"
                ]
                
                new_btn = None
                for selector in new_btn_selectors:
                    try:
                        logging.debug(f"标签页 {self.tab_id}: 定位新建会话按钮选择器: {selector}")
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if buttons:
                            new_btn = buttons[0]
                            logging.info(f"标签页 {self.tab_id}: 找到新建会话按钮")
                            break
                    except Exception as e:
                        logging.debug(f"标签页 {self.tab_id}: 定位新建会话按钮失败: {e}")
                        continue
                
                if not new_btn:
                    raise Exception("无法定位新建会话按钮")
                    
                logging.info(f"标签页 {self.tab_id}: 点击新建会话按钮")
                new_btn.click()
                logging.info(f"标签页 {self.tab_id}: 等待2秒让页面响应")
                time.sleep(2)
                
                # 等待新会话加载 - 优化：缩短等待时间，添加详细日志
                greeting_selectors = [
                    ".agent-chat__bubble__content",  # 更通用的聊天内容选择器
                    ".agent-chat__conv--agent-homepage-v2__greeting",
                    ".welcome-message",
                    ".empty-state"
                ]
                
                logging.info(f"标签页 {self.tab_id}: 等待新会话加载")
                # 等待10秒后直接跳过
                time.sleep(10)
                logging.warning(f"标签页 {self.tab_id}: 新会话加载超时，跳过等待")
                # 不抛出异常，继续执行
            else:
                logging.info(f"标签页 {self.tab_id}: 切换到会话 {session_id}")
                # 尝试多种方式定位会话
                session_selectors = [
                    f"[dt-cid='{session_id}']",
                    f".conversation-item[data-id='{session_id}']",
                    f"[data-session-id='{session_id}']"
                ]
                
                session = None
                for selector in session_selectors:
                    try:
                        logging.debug(f"标签页 {self.tab_id}: 定位会话选择器: {selector}")
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            session = elements[0]
                            logging.info(f"标签页 {self.tab_id}: 找到会话元素")
                            break
                    except Exception as e:
                        logging.debug(f"标签页 {self.tab_id}: 定位会话失败: {e}")
                        continue
                
                if not session:
                    raise Exception(f"无法定位会话: {session_id}")
                    
                session.click()
                time.sleep(2)
            return True
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 会话操作失败: {str(e)}")
            logging.error(f"标签页 {self.tab_id}: 错误详情: {traceback.format_exc()}")
            return False
    
    def contains_keywords(self, text, query, min_keywords=2):
        """检查文本是否包含查询中的关键词"""
        if not text or not query:
            return False
        
        # 分词比较（简单实现）
        text_words = set(re.findall(r'\b\w+\b', text.lower()))
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        
        # 计算交集
        common_words = text_words.intersection(query_words)
        
        # 如果共同词汇达到一定数量，认为包含关键词
        return len(common_words) >= min(min_keywords, len(query_words))
    
    def validate_and_wait_for_response(self, original_text, request_data, timeout=180):
        """验证响应文本并与原始文本对比，如果相同则继续检测未稳定文本"""
        try:
            logging.info(f"标签页 {self.tab_id}: 开始验证响应文本")
            
            # 安全获取文本内容用于对比
            if isinstance(request_data, dict):
                original_query = request_data.get('text', '')
            elif hasattr(request_data, 'get'):
                original_query = request_data.get('text', '')
            else:
                original_query = str(request_data)
            
            logging.info(f"标签页 {self.tab_id}: 原始查询文本: {original_query[:100]}...")
            
            # 获取新消息
            new_msg = self.get_new_message(timeout=60)
            
            # 初始等待文本稳定
            initial_text = self.wait_for_stable_text(new_msg, wait_time=2, timeout=60)
            logging.info(f"标签页 {self.tab_id}: 初始稳定文本: {initial_text[:100]}...")
            
            # 文本验证逻辑
            validation_count = 0
            max_validations = 3
            current_text = initial_text
            
            while validation_count < max_validations:
                validation_count += 1
                logging.info(f"标签页 {self.tab_id}: 执行第 {validation_count} 次文本验证")
                time.sleep(2)
                
                # 检查条件1：响应文本与原始查询完全相同
                # 检查条件2：响应文本包含原始查询的关键词（防止误判）
                is_identical = (current_text.strip() == original_query.strip())
                contains_keywords = self.contains_keywords(current_text, original_query)
                
                logging.info(f"标签页 {self.tab_id}: 文本验证 - 相同: {is_identical}, 包含关键词: {contains_keywords}")
                
                # 如果文本完全相同，说明可能是卡顿或未生成完成
                if is_identical and len(current_text.strip()) > 0:
                    logging.warning(f"标签页 {self.tab_id}: 检测到响应文本与查询文本完全相同 (第{validation_count}次)，可能存在异常")
                    
                    # 额外等待更长时间
                    extra_wait_time = 3  # 增加等待时间
                    logging.info(f"标签页 {self.tab_id}: 额外等待 {extra_wait_time} 秒后重新检查...")
                    time.sleep(extra_wait_time)
                    
                    # 重新获取消息和文本
                    try:
                        new_msg = self.get_new_message(timeout=30)
                        current_text = self.wait_for_stable_text(new_msg, wait_time=3, timeout=60)
                        logging.info(f"标签页 {self.tab_id}: 重新获取文本: {current_text[:100]}...")
                        
                        # 再次验证
                        is_still_identical = (current_text.strip() == original_query.strip())
                        if not is_still_identical:
                            logging.info(f"标签页 {self.tab_id}: 文本已更新，退出验证循环")
                            break
                            
                    except Exception as e:
                        logging.error(f"标签页 {self.tab_id}: 重新获取消息失败: {str(e)}")
                        break
                        
                # 如果文本包含关键词但不完全相同，可能是正常响应
                elif contains_keywords and not is_identical:
                    logging.info(f"标签页 {self.tab_id}: 响应文本包含查询关键词，判断为正常响应")
                    break
                    
                # 如果文本完全不同，说明是正常的新响应
                elif not is_identical and not contains_keywords:
                    logging.info(f"标签页 {self.tab_id}: 响应文本与查询文本不同，判断为正常响应")
                    break
                    
                # 如果达到最大验证次数仍相同，强制返回当前文本
                if validation_count >= max_validations:
                    logging.warning(f"标签页 {self.tab_id}: 达到最大验证次数，强制返回当前文本")
                    break
            
            # 最终等待确保文本完全稳定
            final_text = self.wait_for_stable_text(new_msg, wait_time=3, timeout=60)
            logging.info(f"标签页 {self.tab_id}: 最终稳定文本: {final_text[:100]}...")
            
            logging.info(f"标签页 {self.tab_id}: 文本验证完成，最终文本长度: {len(final_text)}")
            return final_text
            
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 文本验证过程出错: {str(e)}")
            # 出错时返回原始文本
            try:
                return new_msg.text if new_msg else initial_text
            except:
                return initial_text
    
    def send_message(self, request_data):
        try:
            logging.info(f"标签页 {self.tab_id}: 输入文本")
            # 尝试多种方式定位输入框
            input_selectors = [
                ".ql-editor.ql-blank",
                ".message-input",
                "textarea[placeholder='输入你的问题']",
                "[contenteditable='true']"
            ]
            
            input_box = None
            for selector in input_selectors:
                try:
                    input_box = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not input_box:
                raise Exception("无法定位输入框")
                
            # 安全获取文本内容
            text_content = ""
            if isinstance(request_data, dict):
                text_content = request_data.get('text', '')
            elif hasattr(request_data, 'get'):
                text_content = request_data.get('text', '')
            else:
                text_content = str(request_data)
            
            input_box.clear()
            input_box.send_keys(text_content)
            
            logging.info(f"标签页 {self.tab_id}: 发送消息")
            # 尝试多种方式定位发送按钮
            send_btn_selectors = [
                "#yuanbao-send-btn"
            ]
            
            send_btn = None
            for selector in send_btn_selectors:
                try:
                    send_btn = WebDriverWait(self.driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not send_btn:
                raise Exception("无法定位发送按钮")
                
            send_btn.click()
            
            logging.info(f"标签页 {self.tab_id}: 等待回复")
            # 使用新的验证方法替代原来的简单等待
            final_text = self.validate_and_wait_for_response(text_content, request_data)
            
            logging.info(f"标签页 {self.tab_id}: 获取会话ID")
            # 尝试多种方式定位活动会话
            active_selectors = [
                ".yb-recent-conv-list__item.active",
                ".active-conversation",
                "[data-active='true']"
            ]
            
            active = None
            for selector in active_selectors:
                try:
                    active = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not active:
                raise Exception("无法定位活动会话")
                
            current_id = active.get_attribute("dt-cid")
            
            return {"id": current_id, "text": final_text}
        except Exception as e:
            logging.error(f"标签页 {self.tab_id}: 消息发送失败: {str(e)}")
            raise

# 初始化标签页管理器
def initialize_tabs():
    global tabs, tab_counter
    with tab_lock:
        # 创建初始标签页
        main_tab = YuanbaoAutomation(tab_id=tab_counter)
        tabs.append(main_tab)
        tab_counter += 1
        logging.info(f"初始化主标签页 {main_tab.tab_id}")

# 获取可用标签页
def get_available_tab():
    global tabs, tab_counter
    
    with tab_lock:
        # 检查是否有可用标签页
        available_tabs = [tab for tab in tabs if not tab.lock.locked()]
        if available_tabs:
            return available_tabs[0]
        
        # 没有可用标签页，检查是否可以创建新标签页
        if len(tabs) < MAX_TABS:
            new_tab = YuanbaoAutomation(tab_id=tab_counter)
            tabs.append(new_tab)
            tab_counter += 1
            logging.info(f"创建新标签页 {new_tab.tab_id}")
            return new_tab
        
        # 所有标签页都忙且达到最大数量
        logging.warning(f"所有标签页都忙且达到最大数量 {MAX_TABS}")
        return None

@app.route('/hunyuan', methods=['POST'])
def handle_request():
    logging.info("收到新请求")
    
    # 获取可用标签页
    tab = get_available_tab()
    if not tab:
        logging.warning("系统繁忙，所有标签页都忙")
        return jsonify({"error": "系统繁忙，请稍后再试"}), 429
    
    # 尝试获取标签页锁
    if not tab.lock.acquire(blocking=False):
        logging.warning(f"标签页 {tab.tab_id} 忙，尝试获取其他标签页")
        # 如果获取的标签页突然变忙，尝试获取其他标签页
        tab = get_available_tab()
        if not tab or not tab.lock.acquire(blocking=False):
            logging.warning("系统繁忙，无法获取可用标签页")
            return jsonify({"error": "系统繁忙，请稍后再试"}), 429
    
    try:
        # 安全解析JSON数据
        try:
            # 尝试直接获取JSON
            request_data = request.get_json()
            if request_data is None:
                # 如果get_json返回None，尝试手动解析
                data = request.data.decode('utf-8')
                if not data:
                    logging.warning("空请求体")
                    return jsonify({"error": "请求数据为空"}), 400
                request_data = json.loads(data)
        except Exception as e:
            logging.warning(f"JSON解析失败: {str(e)}")
            # 尝试手动解析
            data = request.data.decode('utf-8')
            if not data:
                logging.warning("空请求体")
                return jsonify({"error": "请求数据为空"}), 400
            try:
                request_data = json.loads(data)
            except:
                logging.warning("无效的JSON格式")
                return jsonify({"error": "无效的JSON格式"}), 400
        
        # 确保request_data是字典类型
        if not isinstance(request_data, dict):
            logging.warning(f"请求数据不是字典类型: {type(request_data)}")
            # 尝试转换或提取
            if isinstance(request_data, str):
                try:
                    request_data = json.loads(request_data)
                except:
                    logging.warning("无法将字符串转换为字典")
                    request_data = {"text": request_data}
            else:
                request_data = {"text": str(request_data)}
        
        logging.info(f"标签页 {tab.tab_id}: 处理请求: {json.dumps(request_data, ensure_ascii=False)[:200]}...")
        session_id = request_data.get('sequence', 'new')
        
        # 处理会话
        if not tab.handle_session(session_id):
            return jsonify({"error": "会话操作失败"}), 500
        
        # 切换模型
        mode = request_data.get('mode')
        if mode:
            logging.info(f"标签页 {tab.tab_id}: 切换模型到 {mode}")
            if not tab.change_model(mode):
                return jsonify({"error": "模型切换失败"}), 500
        
        # 上传图片
        picture = request_data.get('picture')
        if picture and picture != "new":
            logging.info(f"标签页 {tab.tab_id}: 上传图片")
            if not tab.upload_image(picture):
                return jsonify({"error": "图片上传失败"}), 500
        
        # 上传文件
        files = {}
        if isinstance(request_data, dict):
            files = {k: v for k, v in request_data.items() if re.match(r'file\d+', k)}
        elif hasattr(request_data, 'items'):
            files = {k: v for k, v in request_data.items() if re.match(r'file\d+', k)}
        
        if files:
            logging.info(f"标签页 {tab.tab_id}: 上传 {len(files)} 个文件")
            if not tab.upload_files(files, request_data):
                return jsonify({"error": "文件上传失败"}), 500
        
        # 发送消息并获取响应
        response = tab.send_message(request_data)
        logging.info(f"标签页 {tab.tab_id}: 请求处理完成: ID={response.get('id')}, 文本长度={len(response.get('text', ''))}")
        return jsonify(response)
        
    except TimeoutError as e:
        logging.error(f"标签页 {tab.tab_id}: 操作超时: {str(e)}")
        return jsonify({"error": str(e)}), 504
    except Exception as e:
        logging.exception(f"标签页 {tab.tab_id}: 处理出错: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500
    finally:
        tab.lock.release()
        logging.info(f"标签页 {tab.tab_id}: 释放锁")

@app.route('/health', methods=['GET'])
def health_check():
    try:
        status_list = []
        with tab_lock:
            for tab in tabs:
                try:
                    if tab.driver:
                        title = tab.driver.title
                        status_list.append({"id": tab.tab_id, "status": "ok", "title": title})
                    else:
                        status_list.append({"id": tab.tab_id, "status": "degraded", "message": "浏览器未初始化"})
                except:
                    status_list.append({"id": tab.tab_id, "status": "error", "message": "浏览器状态未知"})
        
        return jsonify({
            "total_tabs": len(tabs),
            "max_tabs": MAX_TABS,
            "tabs": status_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def shutdown_handler(signum, frame):
    logging.info("接收到终止信号，关闭服务...")
    exit(0)

if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # 初始化标签页
    initialize_tabs()
    
    logging.info(f"启动服务，最大标签页数量: {MAX_TABS}")
    app.run(host='0.0.0.0', port=PORT_RUNNING, threaded=True)

