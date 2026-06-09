# 使用urllib获取百度首页的源码
import urllib.request

# 定义一个url
url = "http://www.baidu.com"

# 模拟浏览器向服务器发送请求
# response中不止包含源码
response = urllib.request.urlopen(url)

# 获取服务器响应的源码
# read方法获取的是二进制数据，需要解码成字符串
content = response.read().decode("utf-8")

# 打印源码
print(content)