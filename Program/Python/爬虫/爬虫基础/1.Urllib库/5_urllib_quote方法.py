# https://cn.bing.com/search?q=%E5%88%98%E4%BA%A6%E8%8F%B2(这一串是unicode编码)
# 获取https://cn.bing.com/search?q=刘亦菲的网页源码

import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

url = "https://cn.bing.com/search?q="
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36 Edg/89.0.774.54"
}
# 对姓名进行URL编码,将刘亦菲三个字变成unicode编码
name = urllib.parse.quote("刘亦菲")

request = urllib.request.Request(url=url+name, headers=headers)
response = urllib.request.urlopen(request)
content = response.read().decode("utf-8")

soup = BeautifulSoup(content, 'html.parser')
print(soup.prettify())
