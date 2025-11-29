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
                driver.add_cookie(cookie)
    
    # 访问目标 URL
    driver.get(url)
    
    # 检查是否需要登录

   # print("需要登录，请手动完成登录...")
   # input("登录完成后按回车键继续...")
        
        # 保存 cookies
    with open(cookie_file, "w") as f:
        json.dump(driver.get_cookies(), f)
    print("Cookies 已保存")
    
    return driver
