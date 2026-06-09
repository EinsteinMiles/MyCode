"""
数据采集的时候绕过登陆进入到某个页面
个人信息页面是utf-8编码,但还报编码错误,是因为并没有进入到个人信息页面,而是进入到登陆页面,所以需要设置cookie
"""
import urllib.request

url = 'https://weibo.com/u/4087310005'

# referer:判断当前路径是不是由上一个路径进来的。一般情况下，做图片防盗链时，referer必须设置成图片的来源地址。
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36',
    # 'Cookie':''
}


request = urllib.request.Request(url=url, headers=headers)
response = urllib.request.urlopen(request)

content = response.read().decode('utf-8')

# 将数据保存到本地
with open('weibo.html', 'w', encoding='utf-8') as fp:
    fp.write(content)