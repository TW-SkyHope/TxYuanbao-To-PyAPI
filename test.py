import requests
import json
import base64

def file_to_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# 测试数据
test_data = {
    "sequence": "new",  # 或现有会话ID
    "text": "请分析这些文件",#提问捏
    # 图片文件
    "picture": file_to_base64("sb.png"),#替换为你der图片(相对路径)
    # 其他文件（支持除图片外任意扩展名）
    "file1": file_to_base64("wc.py"),#替换为你der文件(相对路径)
    "filename1": "llq.py",
    "file2": file_to_base64("nb.txt"),#替换为你der文件(相对路径)
    "filename2": "666.py",
    "mode":"hunyuan"
}

try:
    response = requests.post(
        "http://127.0.0.1:8000/hunyuan",
        json=json.dumps(test_data, ensure_ascii=False),
        headers={"Content-Type": "application/json"}
    )
    print("响应状态码:", response.status_code)
    print("响应内容:", response.json())
    
except Exception as e:
    print("请求失败:", str(e))
