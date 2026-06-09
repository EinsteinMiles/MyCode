"""
效率没有lxml高
接口人性化,使用方便
可以解析网页文件,也可以解析本地文件
"""

from bs4 import BeautifulSoup

# 通过解析本地来件来学习基础语法
# 加载文件,默认打开的文件编码格式是gbk
soup = BeautifulSoup(open('Python/爬虫/爬虫基础/2.解析/3.bs4.html','r',encoding='utf-8'),'lxml')

# 根据标签名查找节点
# 找到是第一个符合条件的数据
print(soup.a)
# 返回的是标签的属性和属性值
print(soup.a.attrs)

# bs4的一些函数

# find:返回第一个符合条件的数据
print(soup.find('a'))
# 根据title的值找到对应的a
print(soup.find('a',title = 'A3'))
# 不能直接使用class,因为他是关键字
print(soup.find('a',class_ = 'A3'))

# find_all：返回所有符合条件的数据的列表
print(soup.find_all('a'))
# 检索多个标签的数据，需要将他们变成列表
print(soup.find_all(['a','span']))
# limit：查找前几个数据
print(soup.find_all('li',limit=2))

# select(recommend)
# 返回多个数据的列表
print(soup.select('a'))
# 搜索class,在数据前加个.类选择器
print(soup.select('.A3'))
# 通过id来搜索
print(soup.select('#name'))
# 属性选择器
# 查找li标签中有id的标签
print(soup.select('li[id]'))
# 查找li标签中有id为victim的标签
print(soup.select('li[id="victim"]'))
# 层级选择器
# 后代选择器 div下的li，通过空格来表示
print(soup.select('div li'))
# 子代选择器 div下的直接子li，通过>来表示
print(soup.select('div > ul > li'))
# 找到a标签和li标签的所有对象
# 逗号表示或，无需加列表
print(soup.select('a,li'))

# 节点信息
