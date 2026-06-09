import urllib.request
import urllib.parse
'''
get和post的区别:
get请求,
    1.请求数据放在url中
    2.发送请求的时候，需要将数据进行编码
    3.获取数据时,获取到的数据为bytes类型
post请求:
    1.请求数据放在请求体中
    2.发送请求的时候，需要将数据进行编码
    3.获取数据时,获取到的数据为bytes类型
'''

def create_request(page):
    base_url = 'https://www.kfc.com.cn/kfccda/ashx/GetStoreList.ashx?op=cname'

    data = {
        'cname': '杭州',
        'pid': '',
        'pageIndex': page,
        'pageSize': '10'
    }
    data = urllib.parse.urlencode(data).encode('utf-8')

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
    }
    request = urllib.request.Request(url=base_url, data=data, headers=headers)

    return request

def get_oject(request):
    response = urllib.request.urlopen(request)
    content = response.read().decode('utf-8')
    return content
def down_load(page, content):
    with open('kfc_' + str(page) + '.json', 'w', encoding='utf-8') as fp:
        fp.write(content)  

if __name__ == '__main__':
    start_page = int(input('请输入起始页码：'))
    end_page = int(input('请输入结束页码：'))

    for page in range(start_page, end_page+1):
        request = create_request(page)
        content = get_oject(request)
        down_load(page, content)