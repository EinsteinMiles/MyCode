# 使用urllib获取百度首页的源码
import urllib.request

# 定义一个url
url = "http://www.baidu.com"

# 模拟浏览器向服务器发送请求
# response中不止包含源码
response = urllib.request.urlopen(url)

# 获取服务器响应的源码
# 一个类型和六个方法

# 类型：HTTPResponse
print(type(response))

# 六个方法：

# read()是一字节一字节的去读
print(response.read().decode("utf-8"))
# readline()是一行一行的去读,只能读取一行
print(response.readline().decode("utf-8"))
# readlines()是一行一行的去读,返回一个列表
print(response.readlines().decode("utf-8"))

# getcode()获取状态码,返回200表示成功
print(response.getcode())

# geturl()获取请求的url
print(response.geturl())

# getheaders()获取响应头,返回一个列表
print(response.getheaders())