# jsonpath只能解析本地文件
import json
import jsonpath

obj = json.load(open('Program\Python\爬虫\\2_jsonpath.json','r',encoding='utf-8'))

# 书店所有书的作者
author_list = jsonpath.jsonpath(obj,'$.store.book[*].author')
print(author_list)

# 所有的作者
author_list = jsonpath.jsonpath(obj,'$..author')
print(author_list)

# store下面的所有元素
tag_list = jsonpath.jsonpath(obj,'$.store.*')
print(tag_list)

# store里面所有的钱
price_list = jsonpath.jsonpath(obj,'$.store..price')
print(price_list)

# 第三本书
book = jsonpath.jsonpath(obj,'$..book[2].title')
print(book)

# 最后一本书
book = jsonpath.jsonpath(obj,'$..book[(@.length-1)].title')
print(book)

# 前两本书
book = jsonpath.jsonpath(obj,'$..book[:2].title')
print(book)

# 过滤出所有含有isbn的书
# 条件过滤需要在()前加一个？
book_isbn = jsonpath.jsonpath(obj,'$..book[?(@.isbn)]')
print(book_isbn)

# 超过10块钱的书
book_price = jsonpath.jsonpath(obj,'$..book[?(@.price>10)]')
print(book_price)