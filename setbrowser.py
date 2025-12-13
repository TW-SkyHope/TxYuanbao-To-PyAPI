from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.options import Options
import time
import json
import os

#aiapi.py配置
MAX_TABS = 5  # 最大标签页数量，即最大线程数量
PORT_RUNNING = 8000  # 运行端口
def autoh(url):
    
    # 配置浏览器选项
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-insecure-localhost')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 创建浏览器实例
    service = Service()
    options = webdriver.EdgeOptions()
    driver = webdriver.Edge(service=service, options=options)
    
    # 尝试加载保存的 cookies
    cookie_file = "cookies.json"
    if os.path.exists(cookie_file):
        driver.get("https://yuanbao.tencent.com/login")  # 先访问一个页面以设置域
        with open(cookie_file, "r") as f:
            cookies = json.load(f)
            for cookie in cookies:
                # 跳过无效的cookie属性
                if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                    cookie['expiry'] = int(cookie['expiry'])
                # 添加cookie到浏览器
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"添加cookie失败: {e}")
        # 刷新页面以应用cookie
        driver.refresh()
    
    # 访问目标 URL
    driver.get(url)
    
    # 检查是否需要登录
    def is_logged_in():
        """检查是否已经登录成功"""
        try:
            # 检查是否存在登录后才会显示的元素
            # 例如：检查是否存在聊天输入框、用户头像等登录后才有的元素
            # 或者检查URL是否已经跳转到登录后的页面
            current_url = driver.current_url
            if "login" not in current_url.lower():
                # 检查页面中是否存在聊天相关元素
                driver.find_element(by="css selector", value=".agent-chat__bubble__content")
                return True
            return False
        except Exception as e:
            print(f"检查登录状态失败: {e}")
            return False
    
    # 检查登录状态
    if not is_logged_in():
        print("需要登录，请手动完成登录...")
        input("登录完成后按回车键继续...")
        
        # 用户按回车键后，直接保存cookies，不检查登录状态
        cookies = driver.get_cookies()
        if cookies:
            with open(cookie_file, "w") as f:
                json.dump(cookies, f, indent=2)
            print("Cookies 已保存")
        else:
            print("未获取到有效的cookies")
    else:
        print("已登录，使用保存的cookies")
    
    return driver
