# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymysql
from scrapy.utils.project import get_project_settings
import time


class NewsPipeline(object):
    source_messageInsert = '''insert into netfin_source_message(title,url,net_name,ent_time,keyword,digest,content,hot_degree,scan_id)
                            values('{title}','{url}','{net_name}','{ent_time}','{keyword}','{digest}','{content}','{hot_degree}','{scan_id}')'''
    source_scanInsert = '''insert into netfin_scanlog(id,net_name,status,ent_time,fail_result)
                                    values('{scan_id}','{net_name}','{status}','{ent_time}','{fail_result}')'''
    source_urlselect = '''select url from netfin_source_message'''
    source_updateSpiderStatus = '''update netfin_spider set status = '{status}', ent_time = '{ent_time}' where net_name = \'{net_name}\''''
    url_list = []

    def __init__(self):
        settings = get_project_settings()
        # 连接数据库
        self.connect = pymysql.connect(
            host=settings.get('MYSQL_HOST'),
            port=settings.get('MYSQL_PORT'),
            db=settings.get('MYSQL_DBNAME'),
            user=settings.get('MYSQL_USER'),
            passwd=settings.get('MYSQL_PASSWD'),
            charset='utf8',
            use_unicode=True)

        # 通过cursor执行增删查改
        self.cursor = self.connect.cursor()
        self.connect.autocommit(True)

        # 获取数据库的URL
        self.cursor.execute(self.source_urlselect)
        for r in self.cursor:
            self.url_list.append(r[0])

    def process_item(self, item, spider):
        if item['url'] in self.url_list:
            print('______________重复新闻________________'.encode("utf-8").decode("latin1"))
            return
        sqltext = self.source_messageInsert.format(title=pymysql.escape_string(item['title']),
                                                   url=pymysql.escape_string(item['url']),
                                                   net_name=pymysql.escape_string(item['net_name']),
                                                   ent_time=pymysql.escape_string(item['ent_time']),
                                                   keyword=pymysql.escape_string(item['keyword']),
                                                   digest=pymysql.escape_string(item['digest']),
                                                   content=pymysql.escape_string(item['content']),
                                                   hot_degree=pymysql.escape_string(item['hot_degree']),
                                                   scan_id=pymysql.escape_string(item['scan_id'])
                                                   )
        # spider.log(sqltext)
        self.cursor.execute(sqltext)

        return item

    def open_spider(self, spider):
        sqltext = self.source_scanInsert.format(scan_id=pymysql.escape_string(spider.scan_id),
                                                net_name=pymysql.escape_string(spider.name),
                                                status=pymysql.escape_string('1'),
                                                ent_time=pymysql.escape_string(
                                                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))),
                                                fail_result=pymysql.escape_string('started')
                                                )
        # spider.log(sqltext)
        self.cursor.execute(sqltext)

    def close_spider(self, spider):
        sqltext = self.source_scanInsert.format(scan_id=pymysql.escape_string(spider.scan_id),
                                                net_name=pymysql.escape_string(spider.name),
                                                status=pymysql.escape_string('2'),
                                                ent_time=pymysql.escape_string(
                                                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))),
                                                fail_result=pymysql.escape_string('finished')
                                                )

        self.cursor.execute(sqltext)
        # spider.log(sqltext)
        self.cursor.close()
        self.connect.close()
