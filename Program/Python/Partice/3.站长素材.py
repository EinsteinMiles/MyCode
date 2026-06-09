from lxml import etree
import urllib.request
import os
import ssl
import gzip

base_url = 'https://sc.chinaz.com/tupian/chengshijingguantupian_'

# 创建请求
def create_request(page):
    if page == 1:
        url = 'https://sc.chinaz.com/tupian/chengshijingguantupian.html'
    else:
        url = base_url + str(page) + '.html'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Referer': 'https://sc.chinaz.com/',
        'Upgrade-Insecure-Requests': '1'
    }

    request = urllib.request.Request(url=url, headers=headers)

    return request

# 获取网页源码
def get_content(request):
    # 创建SSL上下文，跳过证书验证
    ssl_context = ssl._create_unverified_context()
    response = urllib.request.urlopen(request, context=ssl_context)
    
    # 检查是否使用了gzip压缩
    content_bytes = response.read()
    try:
        content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # 如果是gzip压缩，进行解压
        content = gzip.decompress(content_bytes).decode('utf-8')

    return content

# 解析数据
def analyze_data(content):
    tree = etree.HTML(content)
    
    # 一般涉及图片的网站都会进行懒加载，观察下图片的src值
    # 站长素材使用 data-original 属性存储真实图片URL
    img_list = tree.xpath('//img[@data-original]/@data-original')
    name_list = tree.xpath('//img[@data-original]/@alt')

    print(f"找到 {len(img_list)} 张图片")
    
    downloaded_count = 0
    for i in range(len(img_list)):
        try:
            name = name_list[i] + '.jpg' if i < len(name_list) else f'image_{i}.jpg'
            src = img_list[i]
            
            # 判断是否需要添加协议头
            if src.startswith('//'):
                img_url = 'https:' + src
            elif src.startswith('http'):
                img_url = src
            else:
                img_url = 'https:' + src
            
            # 清理文件名中的非法字符
            name = name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            
            print(f'正在下载第{i+1}张图片: {name}')
            
            # 创建下载请求，添加请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://sc.chinaz.com/'
            }
            req = urllib.request.Request(url=img_url, headers=headers)
            ssl_context = ssl._create_unverified_context()
            resp = urllib.request.urlopen(req, context=ssl_context)
            
            # 保存图片
            folder_path = 'Program\Python\Partice\city_img'
            file_path = os.path.join(folder_path, name)
            with open(file_path, 'wb') as f:
                f.write(resp.read())
            
            downloaded_count += 1
        except Exception as e:
            print(f'下载第{i+1}张图片失败: {str(e)}')
            continue
    
    print(f'本页成功下载 {downloaded_count} 张图片')
    return downloaded_count


if __name__ == '__main__':
    start_page = int(input("请输入起始页码："))
    end_page = int(input("请输入结束页码："))
    for page in range(start_page, end_page+1):
        # 创建请求对象
        request = create_request(page)
        # 获取网页源码
        content = get_content(request)
        # 获取响应数据
        analyze_data(content)