from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import time

# 配置浏览器选项，当然你使用其他浏览器也ok
def autoh(url):
# 设置EdgeDriver路径
    edge_driver_path = "msedgedriver.exe"  # Windows系统

    # 创建服务
    service2 = Service(edge_driver_path)

    # 启动
    driver = webdriver.Edge(service=service2)

    url = url
    driver.get(url)
    print(f"已成功打开: {url}")
        
    input("登录完腾讯元宝后enter键下一步")
    time.sleep(3)
    return driver
