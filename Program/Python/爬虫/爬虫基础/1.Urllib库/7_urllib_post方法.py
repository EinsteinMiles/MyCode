import urllib.request
import urllib.parse
import json

url = 'https://fanyi.baidu.com/sug'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
}

data = {
    'kw': 'spider'
}

# post的数据需要编码,不会拼接在url中,而是放在请求体中
data = urllib.parse.urlencode(data).encode('utf-8')
request = urllib.request.Request(url=url, data=data, headers=headers)

response = urllib.request.urlopen(request)
content = response.read().decode('utf-8')
obj = json.loads(content)

print(obj)