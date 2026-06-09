"""
定制更高级的请求头,动态cookie和代理不能使用请求对象的定制
"""
import urllib.request

# 使用handler来访问百度
url = 'http://www.baidu.com'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
}

request = urllib.request.Request(url=url, headers=headers)
# 使用handler来处理请求
# 获取handler对象
handler = urllib.request.HTTPHandler()
# 通过handler获取opener对象
opener = urllib.request.build_opener(handler)
# 使用opener发送请求，获取响应
response = opener.open(request)

content = response.read().decode('utf-8')
print(content)