import urllib.request
import urllib.parse
from lxml import etree

url = 'https://www.baidu.com'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
}

request = urllib.request.Request(url=url, headers=headers)
response = urllib.request.urlopen(request)
baidu_html = response.read().decode('utf-8')

# 解析服务器响应的文件
tree = etree.HTML(baidu_html)
# xpath的返回值是列表
baidu_word = tree.xpath('//button[@id="chat-submit-button"]/text()')[0]

print(baidu_word)