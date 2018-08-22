# -*- coding: utf-8 -*-
import scrapy
from bs4 import BeautifulSoup
from scrapy_splash import SplashRequest
import news_spider.spiders.similarity as similarity
import json
from news_spider.items import NewsItem
import time
from news_spider.spiders import tools


# 爬取新浪网
class sina_news_Spider(scrapy.Spider):
    name = 'sina_news'
    allowed_domains = ['news.sina.com.cn']
    start_urls = ['http://news.sina.com.cn/roll/']

    def __init__(self):
        cf = tools.load_config()
        self.threshold = float(cf.get('Section', 'threshold'))
        self.days = int(cf.get('Section', 'days'))
        self.maxPage = int(cf.get('Section', 'maxPage'))
        target_path = cf.get('Section', 'target_path')
        dict_path = cf.get('Section', 'corpus')
        stopwords_path = cf.get('Section', 'stopwords_path')
        self.decoding = cf.get('Section', 'decoding')
        self.s = similarity.TextSimilarity(target_path, stopwords_path, dict_path)
        # 扫描的批次
        self.scan_id = str(time.time())
        self.category_urls = []
        self.page = 1
        # url
        self.tech_url = 'http://news.sina.com.cn/roll/#pageid=153&lid=2515&page='
        # self.financial_url = 'http://news.sina.com.cn/roll/#pageid=153&lid=2516&page='

    # 将请求转换成splashRequest
    def start_requests(self):
        self.category_urls.append(self.tech_url + str(self.page))
        # 解析各类别新闻URL
        for url in self.category_urls:
            yield SplashRequest(url, self.parse_page,
                                args={'wait': 1}, dont_filter=True)

    # 解析每个类别的新闻列表
    def parse_page(self, response):
        soup = BeautifulSoup(response.body)
        soup.prettify()

        for item in soup.find_all('li'):
            yield SplashRequest(item.a['href'], self.parse_detail, args={'wait': 1}, dont_filter=True)

        url = response.url
        # 获取page
        self.page += 1
        if self.page < self.maxPage:
            next_url = url[0:55] + str(self.page)
            yield SplashRequest(next_url, self.parse_page, args={'wait': 1}, dont_filter=True)

    # 解析新闻内容
    def parse_detail(self, response):
        soup = BeautifulSoup(response.body)
        soup.prettify()
        try:
            # 获取新闻标题
            title = soup.select('h1[class="main-title"]')[0].get_text()
            # 获取新闻发布时间
            date = time.strftime("%Y-%m-%d %H:%M:%S",
                                 time.localtime(time.mktime(
                                     time.strptime(soup.select('span[class="date"]')[0].get_text(),
                                                   '%Y年%m月%d日 %H:%M'))))
            # 终止条件
            interval = tools.time_cmp(float(self.scan_id), date)
            if interval > self.days:
                print('______________过时新闻________________'.encode("utf-8").decode(self.decoding))
                return
            # 获取评论数
            hot_degree = int(soup.select('a[data-sudaclick="comment_sum_p"]')[0].get_text())
            # 获取新闻关键词
            keywords = []
            try:
                a_list = soup.find_all('div', attrs={'class': 'keywords'})[0].find_all('a')
                for item in a_list:
                    keywords.append(item.get_text())
            except:
                pass
            # 获取新闻URL
            url = response.url
            # 获取新闻内容
            comView = soup.select('div[class="article"]')[0]
            # 删除图片和JS
            try:
                comView.style.decompose()
            except:
                pass
            try:
                for i in comView.find_all('script'):
                    i.decompose()
                for i in comView.find_all('div'):
                    i.decompose()
                comView.find('p', attrs={'class': 'article-editor'}).decompose()
            except AttributeError:
                pass
            article = []
            for p in comView.find_all('p'):
                if p.get_text() is not None:
                    article.append(p.get_text().strip())
            article = '\n'.join(article)
            # 关键词摘要生成
            temp_keywords, abstract = tools.sina_keyword_abstract(article, 4, 5)
            if len(keywords) == 0:
                keywords = temp_keywords
            keywords = ' '.join(keywords)

            print('新浪网: '.encode("utf-8").decode(self.decoding), title.encode("utf-8").decode(self.decoding).strip())
            # 封装成item
            similar_list = self.s.cal_similarities(article)
            if max(similar_list) > self.threshold:
                item = NewsItem()
                item['title'] = title.strip()
                item['url'] = url.strip()
                item['net_name'] = '新浪网'
                item['ent_time'] = date
                item['keyword'] = keywords.strip()
                item['digest'] = abstract.strip()
                item['content'] = article.strip()
                item['hot_degree'] = str(tools.divide_hot_degree(self.name, hot_degree))
                item['scan_id'] = str(self.scan_id)
                return item
        except:
            try:
                # 获取新闻标题
                title = soup.select('h1[id="artibodyTitle"]')[0].get_text()
                # 获取新闻发布时间
                date = time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.localtime(
                                         time.mktime(
                                             time.strptime(soup.select('span[id="pub_date"]')[0].get_text().strip(),
                                                           '%Y-%m-%d %H:%M:%S'))))
                # 终止条件
                interval = tools.time_cmp(float(self.scan_id), date)
                if interval > self.days:
                    print('______________过时新闻________________'.encode("utf-8").decode(self.decoding))
                    return
                # 获取评论数
                hot_degree = int(soup.select('a[data-sudaclick="comment_sum_p"]')[0].get_text())
                # 获取新闻关键词
                keywords = []
                try:
                    a_list = soup.find_all('p', attrs={'class': 'art_keywords'})[0].find_all('a')
                    for item in a_list:
                        keywords.append(item.get_text())
                except:
                    pass
                # 获取新闻URL
                url = response.url
                # 获取新闻内容
                comView = soup.select('div[id="artibody"]')[0]
                # 删除图片和JS
                try:
                    comView.style.decompose()
                except:
                    pass
                try:
                    for i in comView.find_all('script'):
                        i.decompose()
                    for i in comView.find_all('div'):
                        i.decompose()
                        comView.find('p', attrs={'class': 'article-editor'}).decompose()
                except AttributeError:
                    pass
                # 保存新闻内容
                article = []
                for p in comView.find_all('p'):
                    if p.get_text() is not None:
                        article.append(p.get_text().strip())
                article = '\n'.join(article)
                # 关键词摘要
                temp_keywords, abstract = tools.sina_keyword_abstract(article, 4, 5)
                if len(keywords) == 0:
                    keywords = temp_keywords
                keywords = ' '.join(keywords)

                print('新浪网: '.encode("utf-8").decode(self.decoding),
                      title.encode("utf-8").decode(self.decoding).strip())
                # 封装成item
                similar_list = self.s.cal_similarities(article)
                if max(similar_list) > self.threshold:
                    item = NewsItem()
                    item['title'] = title.strip()
                    item['url'] = url.strip()
                    item['net_name'] = '新浪网'
                    item['ent_time'] = date
                    item['keyword'] = keywords.strip()
                    item['digest'] = abstract.strip()
                    item['content'] = article.strip()
                    item['hot_degree'] = str(tools.divide_hot_degree(self.name, hot_degree))
                    item['scan_id'] = str(self.scan_id)
                    return item
            except:
                pass


################################################################################
# 爬取雷锋网
class leiphone_Spider(scrapy.Spider):
    name = 'leiphone_news'
    allowed_domains = ['www.leiphone.com']

    def __init__(self):
        cf = tools.load_config()
        self.threshold = float(cf.get('Section', 'threshold'))
        self.days = int(cf.get('Section', 'days'))
        self.maxPage = int(cf.get('Section', 'maxPage'))
        target_path = cf.get('Section', 'target_path')
        stopwords_path = cf.get('Section', 'stopwords_path')
        dict_path = cf.get('Section', 'corpus')
        self.decoding = cf.get('Section', 'decoding')
        self.s = similarity.TextSimilarity(target_path, stopwords_path, dict_path)
        # 扫描的批次
        self.scan_id = str(time.time())

    def start_requests(self):
        for i in range(0, self.maxPage + 1):
            yield scrapy.Request('https://www.leiphone.com/site/AjaxLoad/page/' + str(i), callback=self.parse)

    def parse(self, response):
        html = json.loads(response.body)['html']
        soup = BeautifulSoup(html)
        news_list = soup.find_all('a', attrs={'class': 'headTit'})
        for item in news_list:
            yield scrapy.Request(item['href'], self.parse_content)

    def parse_content(self, response):
        soup = BeautifulSoup(response.body)
        # 获取新闻发布时间
        date = soup.select('td[class="time"]')[0].get_text().strip()
        date = time.strftime("%Y-%m-%d %H:%M:%S",
                             time.localtime(time.mktime(time.strptime(date, '%Y-%m-%d %H:%M'))))
        # 终止条件
        interval = tools.time_cmp(float(self.scan_id), date)
        if interval > self.days:
            print('______________过时新闻________________'.encode("utf-8").decode(self.decoding))
            return

        # 获取新闻标题
        title = soup.select('h1[class="headTit"]')[0].get_text().strip()
        # 获取新闻导语
        leadword = soup.select('div[class="article-lead"]')[0].get_text().strip()
        # 获取收藏数
        hot_degree = int(soup.find('a', attrs={'class': 'collect collect-no'}).find('span').get_text().strip())
        # 获取新闻URL
        url = response.url
        # 获取关键词
        keywords = []
        try:
            for i in soup.find('div', attrs={'class': 'related-link clr'}).children:
                keywords.append(i.string.strip())
        except:
            pass
        # 获取新闻内容
        comView = soup.select('div[class="lph-article-comView"]')[0]
        # 删除模版和JS
        try:
            [s.extract() for s in comView(['script', 'strong'])]
        except AttributeError:
            pass
        article = []
        for p in comView.find_all('p'):
            if p.get_text() is not None:
                article.append(p.get_text().strip())
        article = '\n'.join(article)
        temp_keywords, abstract = tools.leiphone_keyword_abstract(article, 3, 3)
        if len(keywords) == 0:
            keywords = temp_keywords
        keywords = ' '.join(keywords)

        print('雷锋网: '.encode("utf-8").decode(self.decoding), title.encode("utf-8").decode(self.decoding).strip())
        # 封装成item
        similar_list = self.s.cal_similarities(article)
        if max(similar_list) > self.threshold:
            item = NewsItem()
            item['ent_time'] = date
            item['title'] = title.strip()
            item['url'] = url.strip()
            item['net_name'] = '雷锋网'
            item['keyword'] = keywords.strip()
            item['digest'] = abstract.strip()
            item['content'] = article.strip()
            item['hot_degree'] = str(tools.divide_hot_degree(self.name, hot_degree))
            item['scan_id'] = self.scan_id
            return item


################################################################################
# 爬取36kr
class _36_kr_Spider(scrapy.Spider):
    name = '_36kr_news'
    page = 1
    start_urls = ['http://36kr.com/api/search-column/mainsite?per_page=20&page=' + str(page)]

    def __init__(self):
        cf = tools.load_config()
        self.threshold = float(cf.get('Section', 'threshold'))
        self.days = int(cf.get('Section', 'days'))
        self.maxPage = int(cf.get('Section', 'maxPage'))
        target_path = cf.get('Section', 'target_path')
        stopwords_path = cf.get('Section', 'stopwords_path')
        dict_path = cf.get('Section', 'corpus')
        self.decoding = cf.get('Section', 'decoding')
        self.s = similarity.TextSimilarity(target_path, stopwords_path, dict_path)
        # 扫描的批次
        self.scan_id = str(time.time())
        self.page = 1

    def parse(self, response):
        data = json.loads(response.body)['data']
        news_list = data['items']
        for item in news_list:
            id = item['id']
            date = item['published_at']
            if id > 50000:
                yield SplashRequest('http://36kr.com/p/' + str(id) + '.html', callback=self.parse_content,
                                    args={'wait': 1.5}, meta={'date': date})
        # 获取page
        self.page += 1
        if self.page < self.maxPage:
            next_url = 'http://36kr.com/api/search-column/mainsite?per_page=20&page=' + str(self.page)
            yield scrapy.Request(next_url, callback=self.parse)

    def parse_content(self, response):
        try:
            soup = BeautifulSoup(response.body)
            # 获取时间
            date = response.meta['date']
            # 终止条件
            interval = tools.time_cmp(float(self.scan_id), time.strftime("%Y-%m-%d %H:%M:%S",
                                                                         time.localtime(time.mktime(
                                                                             time.strptime(date,
                                                                                           "%Y-%m-%dT%H:%M:%S+08:00")))))
            if interval > self.days:
                print('______________过时新闻________________'.encode("utf-8").decode(self.decoding))
                return
            # 获取标题
            title = soup.find('div', attrs={'class': 'mobile_article'}).find('h1').get_text()
            # 获取文章
            textblock = soup.find('section', attrs={'class': 'textblock'})
            try:
                if textblock.find('p').get_text().strip().startswith('编者'):
                    textblock.find('p').find('p').decompose()
            except:
                pass
            article = []
            for p in textblock.find_all('p'):
                if p.get_text() is not None:
                    article.append(p.get_text().strip())
            article = '\n'.join(article)
            # 获取总结
            summary = soup.find('section', attrs={'class': 'summary'}).get_text().strip()
            # 获取点赞数
            hot_degree = int(soup.find('b', attrs={'class': 'count-min'}).get_text().strip())
            # 获取关键词和摘要
            keywords, abstract = tools._36r_keyword_abstract(article, 3, 3)
            raw_keywords = []
            for item in soup.find_all('a', attrs={'class': 'kr-tag-gray'}):
                raw_keywords.append(item.get_text())
            if len(raw_keywords) != 0:
                keywords = raw_keywords
            keywords = ' '.join(keywords)
            print('36氪: '.encode("utf-8").decode(self.decoding), title.encode("utf-8").decode(self.decoding).strip())
            # 封装成item
            similar_list = self.s.cal_similarities(article)
            if max(similar_list) > self.threshold:
                item = NewsItem()
                item['title'] = title.strip()
                item['url'] = response.url.strip()
                item['net_name'] = '36氪'
                item['ent_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(
                    time.mktime(time.strptime(date, "%Y-%m-%dT%H:%M:%S+08:00"))))
                item['keyword'] = keywords.strip()
                item['digest'] = abstract.strip()
                item['content'] = article.strip()
                item['hot_degree'] = str(tools.divide_hot_degree(self.name, hot_degree))
                item['scan_id'] = str(self.scan_id)
                return item
        except:
            pass


# 爬取腾讯网
class tencent_news(scrapy.Spider):
    name = 'tencent_news'
    start_urls = []

    def __init__(self):
        cf = tools.load_config()
        self.threshold = float(cf.get('Section', 'threshold'))
        self.days = int(cf.get('Section', 'days'))
        self.maxPage = int(cf.get('Section', 'maxPage'))
        self.decoding = cf.get('Section', 'decoding')
        target_path = cf.get('Section', 'target_path')
        stopwords_path = cf.get('Section', 'stopwords_path')
        dict_path = cf.get('Section', 'corpus')
        self.s = similarity.TextSimilarity(target_path, stopwords_path, dict_path)
        # 扫描的批次
        self.scan_id = str(time.time())
        # 首页
        self.science_url = 'https://pacaio.match.qq.com/irs/rcd?cid=58&token=c232b098ee7611faeffc46409e836360&ext=tech&page='
        # 互联网
        self.internet_url = 'https://pacaio.match.qq.com/irs/rcd?cid=52&token=8f6b50e1667f130c10f981309e1d8200&ext=614,603,605,611,612,613,615,620,618&page=1'
        # IT
        self.it_url = 'https://pacaio.match.qq.com/irs/rcd?cid=52&token=8f6b50e1667f130c10f981309e1d8200&ext=604,609&page='
        # 区块链
        self.blockchain_url = 'https://pacaio.match.qq.com/tags/tag2articles?id=276813&num=15&page='
        # AI
        self.ai_url = 'https://pacaio.match.qq.com/irs/rcd?cid=52&token=8f6b50e1667f130c10f981309e1d8200&ext=602,608,622&page='
        # 创业创新
        self.innovate_url = 'https://pacaio.match.qq.com/irs/rcd?cid=52&token=8f6b50e1667f130c10f981309e1d8200&ext=619,617,610&page='
        # 前沿科技
        self.leadingSci_url = 'https://pacaio.match.qq.com/irs/rcd?cid=52&token=8f6b50e1667f130c10f981309e1d8200&ext=607,616,623,624&page='
        # 添加进start_urls
        self.start_urls.append(self.science_url)
        self.start_urls.append(self.internet_url)
        self.start_urls.append(self.it_url)
        self.start_urls.append(self.blockchain_url)
        self.start_urls.append(self.ai_url)
        self.start_urls.append(self.innovate_url)
        self.start_urls.append(self.leadingSci_url)

    def start_requests(self):
        for url in self.start_urls:
            for i in range(0, self.maxPage + 1):
                yield scrapy.Request(url + str(i), callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body)
        try:
            news_list = json.loads(soup.get_text())['data']
            for item in news_list:
                yield SplashRequest(item['vurl'], self.parse_content,
                                    args={'wait': 1}, meta={'comment_num': item['comment_num'],
                                                            'publish_time': item[
                                                                'publish_time'],
                                                            'keywords': [k[0] for k in
                                                                         item[
                                                                             'tag_label']]})
        except:
            pass

    def parse_content(self, response):
        try:
            soup = BeautifulSoup(response.body)
            date = time.strftime("%Y-%m-%d %H:%M:%S",
                                 time.localtime(
                                     time.mktime(time.strptime(response.meta['publish_time'], "%Y-%m-%d %H:%M:%S"))))
            # 终止条件
            interval = tools.time_cmp(float(self.scan_id), date)
            if interval > self.days:
                print('______________过时新闻________________'.encode("utf-8").decode(self.decoding))
                return
            title = soup.find('div', attrs={'class': 'LEFT'}).find('h1').get_text()
            hot_degree = int(response.meta['comment_num'])
            keywords = ' '.join(response.meta['keywords'])
            # 删除div节点
            soup.find('div', attrs={'class': 'content-article'}).find('div').decompose()
            article = []
            for p in soup.find('div', attrs={'class': 'content-article'}).find_all('p'):
                if p.get_text() is not None:
                    article.append(p.get_text().strip())
            article = '\n'.join(article)
            abstract = tools.tencent_keyword_abstract(article, 4)
            # 封装成item
            similar_list = self.s.cal_similarities(article)
            print('腾讯网: '.encode("utf-8").decode(self.decoding), title.encode("utf-8").decode(self.decoding).strip())
            if max(similar_list) > self.threshold:
                item = NewsItem()
                item['title'] = title.strip()
                item['url'] = response.url.strip()
                item['net_name'] = '腾讯'
                item['ent_time'] = date
                item['keyword'] = keywords.strip()
                item['digest'] = abstract.strip()
                item['content'] = article.strip()
                item['hot_degree'] = str(tools.divide_hot_degree(self.name, hot_degree))
                item['scan_id'] = str(self.scan_id)
                return item
        except:
            pass

################################################################################
# 爬取微信公众号
# class wechat_Spider(scrapy.Spider):
#     name = 'wechat_news'
#     allowed_domains = ['http://weixin.sogou.com']
#     keyword = '互联网新技术新应用动态'
#     start_urls = ['http://weixin.sogou.com/weixin?type=1&s_from=input&query=' + keyword]
#
#     def parse(self, response):
#         soup = BeautifulSoup(response.body)
#         request = Request(soup.find_all('p', attrs={'class': 'tit'})[0].a['href'], self.parse_list,
#                           dont_filter=True)
#         request.meta['PhantomJS'] = True
#         yield request
#
#     def parse_list(self, response):
#         soup = BeautifulSoup(response.body)
#         for item in soup.find_all('h4', attrs={'class': 'weui_media_title'}):
#             request = Request('https://mp.weixin.qq.com' + item['hrefs'], self.parse_content,
#                               dont_filter=True)
#             request.meta['PhantomJS'] = True
#             yield request
#
#     def parse_content(self, response):
#         soup = BeautifulSoup(response.body)
#         try:
#             title = soup.select('h2[class="rich_media_title"]')[0].get_text().strip()
#             content = soup.select('div[class="rich_media_content "]')[0].get_text().strip()
#             print('-----------------------------------------------')
#             print('标题：', title)
#             print(content)
#             print('-----------------------------------------------')
#         except:
#             pass
