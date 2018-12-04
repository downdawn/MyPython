# coding=utf-8
from urllib.parse import urlencode
import requests
import json
from hashlib import md5
import re
import os
from requests.exceptions import ConnectionError
import pymongo

MONGO_URL = 'localhost'
MONGO_DB = 'toutiao'
MONGO_TABLE = 'toutiao' #数据集合Collection
client = pymongo.MongoClient(MONGO_URL)  # MongoClient 对象，并且指定连接的 URL 地址
db = client[MONGO_DB] #要创建的数据库名


class ToutiaoSpider:
    def __init__(self,offset,keyword):
        self.offset = offset
        self.keyword = keyword
        self.url = "https://www.toutiao.com/search/?" + urlencode({'keyword': '{}'.format(self.keyword)})
        self.headers ={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36",
            "referer": "{}".format(self.url)
        }

    def url_list(self):  # 构造每页链接
        url_list = []
        for i in range(0,self.offset*20,20):
            params = {
                'offset': '{}'.format(i),
                'format': 'json',
                'keyword': '{}'.format(self.keyword),
                'autoload': 'true',
                'count': '20',
                'cur_tab': '3',
                'from': 'gallery',
            }
            url = 'https://www.toutiao.com/search_content/?' + urlencode(params)
            print(url)
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    url_list.append(response.text)
            except ConnectionError:
                print('Error occurred')
                return ""
        return url_list

    def parse_url(self,url):  # 解析url，获取每页的图片链接和标题
        data = json.loads(url)
        content_list =[]
        for item in data.get("data"):
            article_url = item.get("article_url")
            title = item.get("title")
            content_list.append([title,article_url])
        return content_list

    def get_content_list(self, html_str):  # 获取图片链接
        content = requests.get(html_str[1], headers=self.headers)
        images_pattern = re.compile('gallery: JSON.parse\("(.*)"\)', re.S)
        result = re.search(images_pattern, content.text)
        if result:
            data = json.loads(result.group(1).replace('\\', ''))
            sub_images = data.get('sub_images')
            for i in sub_images:  # MongoDB储存需要字典格式
                yield {
                    "url": i.get("url")
                }

    def save_content(self,content_list,html_str):  # 下载图片保存到本地
        for i in range(0, len(content_list)):
            content = requests.get(content_list["url"], headers=self.headers).content  # 图片要储存为二进制，故用content
            img_path = self.keyword + os.path.sep + html_str[0]  # 获取链接title
            if not os.path.exists(img_path):
                os.makedirs(img_path)
            file_path = img_path + os.path.sep +'{0}.{1}'.format(md5(content).hexdigest(), 'jpg')  # md5加密，图片去重
            print("储存到本地：" + file_path )
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    f.write(content)
                    f.close()

    def save_mongo(self,content_list):  # 保存到数据库
        print(content_list)
        if db[MONGO_TABLE].insert(content_list):
            print('储存到MONGODB成功', content_list)
        return False

    def run(self):  # 实现主要逻辑
        # 1、构造请求地址url
        url_list = self.url_list()
        # 2、发送请求，获取响应
        for url in url_list:
            html_str_list = self.parse_url(url)
            # 3、提取数据
            for html_str in html_str_list:
                content_generator = self.get_content_list(html_str)
                # 4、 保存数据
                for content_list in content_generator:  # yield返回一个发生器，遍历写入数据
                    self.save_content(content_list,html_str)
                    self.save_mongo(content_list)


if __name__ == '__main__':
    spider = ToutiaoSpider(1,"街拍")
    spider.run()

