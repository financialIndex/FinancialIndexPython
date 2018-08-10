# -*- coding: utf-8 -*-

from scrapy import cmdline
import os
from news_spider.spiders.clean import setup
os.system("scrapy crawl leiphone_news")
os.system("scrapy crawl _36kr_news")
os.system("scrapy crawl sina_news")

# 文本去重
setup()

