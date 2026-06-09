import urllib.request
import ssl

# 下载一个网页
url_page = "http://www.baidu.com"
# url_page:下载的路径，"baidu.html":下载后的文件名
urllib.request.urlretrieve(url_page, "baidu.html")
print("下载成功")

# 下载图片
url_img = "http://www.baidu.com/img/bd_logo1.png"
urllib.request.urlretrieve(url_img, "baidu.jpg")
print("下载成功")

# 下载视频
url_video = "http://vod.v.jstv.com/2025/09/01/JSTV_JSGGNEW_1756730917831_1c7SAd4_1823.mp4"

try:
    # 创建SSL上下文，禁用证书验证（仅用于测试）
    ssl_context = ssl._create_unverified_context()
    
    # 设置请求头，模拟浏览器访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # 创建请求对象
    req = urllib.request.Request(url_video, headers=headers)
    
    # 使用自定义的SSL上下文打开URL
    with urllib.request.urlopen(req, context=ssl_context) as response:
        # 读取视频数据
        video_data = response.read()
        
        # 保存到文件
        with open("video.mp4", "wb") as f:
            f.write(video_data)
    
    print("视频下载成功")
except Exception as e:
    print(f"视频下载失败: {e}")
