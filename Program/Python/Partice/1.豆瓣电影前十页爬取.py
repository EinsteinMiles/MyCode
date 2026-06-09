import urllib.request
import urllib.parse

def create_request(page):
    base_url = 'https://movie.douban.com/j/chart/top_list?type=11&interval_id=100%3A90&action=&'

    data = {
        'start': (page-1) * 20,
        'limit': 20
    }
    data = urllib.parse.urlencode(data)

    url = base_url + data
    headers = {
    'Cookie':'bid=ZJW2UT6M1kQ; __utmz=30149280.1780727370.1.1.utmcsr=sec.douban.com|utmccn=(referral)|utmcmd=referral|utmcct=/; dbcl2="295489917:QRwIgJQISXg"; ck=9Oh8; _pk_ref.100001.4cf6=%5B%22%22%2C%22%22%2C1780897482%2C%22https%3A%2F%2Faccounts.douban.com%2F%22%5D; _pk_id.100001.4cf6=c5bc7242557a00b8.1780897482.; _pk_ses.100001.4cf6=1; push_noty_num=0; push_doumail_num=0; __utma=30149280.620897114.1780727370.1780727370.1780897496.2; __utmb=30149280.0.10.1780897496; __utmc=30149280; __utma=223695111.1789831980.1780897496.1780897496.1780897496.1; __utmb=223695111.0.10.1780897496; __utmc=223695111; __utmz=223695111.1780897496.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __yadk_uid=Ob6vDoU4TscB88QE2QFyGKtv5Pojrb1i',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
    }

    request = urllib.request.Request(url=url, headers=headers)
    return request

def get_data(request):
    response = urllib.request.urlopen(request)
    content = response.read().decode('utf-8')
    return content
def save_data(content,page):
    with open('douban' + str(page) + '.json', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    start_page = int(input('请输入起始页：'))
    end_page = int(input('请输入结束页：'))

    for page in range(start_page, end_page+1):
        request = create_request(page)
        content = get_data(request)
        save_data(content,page)