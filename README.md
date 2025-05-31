# TxYuanbao-To-PyAPI
<h2>基于Python Selenium的Flask API，用于使用Python脚本操控腾讯AI元宝网页的输入上传发送等操作并检测元宝AI的输出将其返回为json，以创建一个腾讯元宝驱动的AI API接口</h2>  
原理就是拿你的电脑挂着腾讯元宝网页当api用  

---
<h3>演示效果如下</h3>


py环境3.0以上即可，已提供源代码，需要修改或打包等请自行操作  

---
<h3>部署api方法(直接使用源代码,Windows操作)：</h3>  
git仓库或将代码文件aiapi.py，setbrowser.py复制至同一目录下后，打开cmd窗口，cd至目录  
输入python aiapi.py，等待元宝页面打开后自行使用账号登录(放心，我还不至于搁这小脚本上贪你的账号)  
返回cmd窗口，enter键继续，等待Flask运行即可    
以上步骤不要太频繁，之后保持窗口运行  

---
<h3>访问api方式：</h3>  
具体参照test.py，Post传输方式  

接收json格式：{  
  &emsp;#必填  
  &emsp;"text": "(请输入你要输入到元宝输入框的内容)",  
  &emsp;#必填  
  &emsp;"sequence": "(new或现有会话ID)",  
  &emsp;#选填  
  &emsp;"mode":"(hunyuan或deepseek，不填为hunyuan)",  
  &emsp;#选填  
  &emsp;"picture": "(请输入你要上传到元宝的图片，base64格式)",  
  &emsp;#选填，可输入多个filename,file字段  
  &emsp;"file(1-50依次)": "(请输入你要上传到元宝的文件，base64格式)",  
  &emsp;"filename(1-50依次)": "(请输入你要上传到元宝的文件名)",  
}  

返回json格式：{  
  &emsp;"text": "(元宝输出的内容)",  
  &emsp;"id": "(会话id)",  
  &emsp;#若发生错误则返回  
  &emsp;"error": "(错误信息)",  
}  

<h3>注意事项：api目前为单线程运行，同时间多个访问会返回错误</h3>  
若您正在使用我的项目对我的项目有新的需求或发现bug请向于本项目内报告

---
<h3>作者的话：我tm服了为什么市赛不用ai，省赛直接ai漫天飞？？？这私人题目还必须得用ai搞，老子还没钱充ai的api，勾吧信息比赛(赛名我就不说了)，密码的我直接做个api挂nat机上，花钱是不可能的！</h3>
