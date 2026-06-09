import urllib.request
import random

proxiy = {
    'http': '221.227.143.12:16315'
}
proxies_pool = [
    {'http': '221.227.143.12:16123'},
    {'http': '221.227.143.12:16315'}
]

proxies = random.choice(proxies_pool)

url = 'https://cn.bing.com/search?q=ip'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
}
request = urllib.request.Request(url=url, headers=headers)

# handler = urllib.request.ProxyHandler(proxies=proxy)
handler = urllib.request.ProxyHandler(proxies=proxies)
opener = urllib.request.build_opener(handler)
response = opener.open(request)
content = response.read().decode('utf-8')

with open('01.html', 'w', encoding='utf-8') as fp:
    fp.write(content)