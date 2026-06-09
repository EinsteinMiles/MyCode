import urllib.request
from bs4 import BeautifulSoup

'''
url的组成
协议:http/https
域名:www.baidu.com
端口:默认80/443;mysql:3306,oracle:1521,mongodb:27017,redis:6379
路径:/
参数:?name=xxx&age=18
锚点:#
'''

url = 'https://www.baidu.com'

# 反爬：UA伪装
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
}
# 因为urlopen函数不支持headers参数，所以需要创建一个Request对象来设置请求头
# 因为参数顺序问题，所以需要关键词传参
request = urllib.request.Request(url=url, headers=headers)
response = urllib.request.urlopen(request)

content = response.read().decode('utf-8')

# 方法1：使用BeautifulSoup格式化HTML（需要安装bs4）
try:
    soup = BeautifulSoup(content, 'html.parser')
    print(soup.prettify())
except:
    # 方法2：如果没有安装bs4，直接打印原始内容
    print(content)