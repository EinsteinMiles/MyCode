# urlencode应用场景：将多个参数转换为unicode编码

# 获取https://cn.bing.com/search?q=刘亦菲&sex=女

import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

data = {
    'q': '刘亦菲',
    'sex': '女'
}

data = urllib.parse.urlencode(data)

# 获取网页源码
url = 'https://cn.bing.com/search?' + data
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 请求对象的定制
request = urllib.request.Request(url=url, headers=headers)

# 模拟浏览器向服务器发送请求
response = urllib.request.urlopen(request)
# 获取网页源码
content = response.read().decode('utf-8')
# 输出源码
soup = BeautifulSoup(content, 'lxml')
print(soup)