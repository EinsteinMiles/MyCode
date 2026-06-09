"""
1.xpath:能够获取网页部分数据的方式
2.xpath语法
    1.路径查询
        1. /  表示当前节点的直接子节点
        2. // 表示当前节点的所有子节点,不考虑层级关系
    2.谓词查询
        1. //div[@id]
        2. //div[@id='div1']
    3.属性查询
        //@class
    4.模糊查询
        //div[contains(@class,'div1')]
        //div[starts-with(@class,'div1')]
    5.逻辑查询
        //div[@class='div1' or/and @class='div2']
        //title | //price   (针对的是标签)
3.xpath可以解析本地文件,也可以解析网络文件
"""

from lxml import etree

# 解析本地文件
tree = etree.parse('Program\Python\爬虫\\1_html结构.html')

# xpath路径
# 查找ul下面的li
li_list = tree.xpath('//li/text()')
print(len(li_list))
print(li_list)

# 查找所有有id属性的li标签
# text获取标签中的内容
li_list = tree.xpath('//li[@id]/text()')
print(len(li_list))
print(li_list)

# 查找id为l1的li标签
li_list = tree.xpath('//li[@id="l1"]/text()')
print(li_list)

# 查询id为l4的li标签的class的属性值
li = tree.xpath('//li[@id="l4"]/@class')
print(li)

# 查询id标签中包含l的li标签
li_list = tree.xpath('//li[contains(@id,"l")]/text()')
print(li_list)

# 查询id标签中以l开头的li标签
li_list = tree.xpath('//li[starts-with(@id,"l")]/text()')
print(li_list)


# 解析网络文件
# html_tree = etree.HTML()
