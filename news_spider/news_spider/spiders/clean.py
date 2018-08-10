# -*- coding: utf-8 -*-
"""
Created on Thu Jul 12 09:13:20 2018

@author: Administrator
"""
import re
import warnings
from scrapy.utils.project import get_project_settings
warnings.filterwarnings(action='ignore', category=UserWarning, module='gensim')
import jieba
import jieba.analyse
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from collections import defaultdict
from sklearn import decomposition
from sklearn.cluster import AffinityPropagation
import numpy as np
import pymysql
import time
import configparser
import copy

# 文档预处理
def preprocess(doc, stoppath):
    doc = str(doc)
    doc = re.findall(u'[\u4e00-\u9fa5].+?', doc)
    re_h = re.compile(r'</?\w+[^>]*>')
    doc = str(doc)
    doc = re_h.sub('', doc)  # 去除html字符
    doc = re.sub('\s', '', doc)
    jieba.load_userdict(load_config().get('Section', 'dict_path'))
    data = jieba.cut(doc)  # jieba分词
    stopwords = [line.strip() for line in open(stoppath, mode='r', encoding='UTF-8').readlines()]  # 加载停用词
    output = ''
    for word in data:  # 去除停用词
        if word not in stopwords:
            if word != '\t':
                output += word
                output += " "
    return output


# tfidf权值计算
def tfidf_value(data_num, cont, stoppath):
    corpus = []
    for i in cont:
        content = preprocess(i, stoppath)
        corpus.append(content)  # 获取语料
    vectorizer = CountVectorizer()  # 将文本中的词语转换为词频矩阵
    transformer = TfidfTransformer()  # 统计每个词语的tfidf权值
    tfidf = transformer.fit_transform(vectorizer.fit_transform(corpus))  # 第一个fit_transform计算tfidf，第二个是将文本转换为词频矩阵
    return (tfidf)


# PCA
def test_pca(weight, components_num):
    kpca = decomposition.KernelPCA(components_num, degree=3, kernel='rbf', gamma=4)
    principle_weight = kpca.fit_transform(weight)
    return (principle_weight)


# AffinityPropagation 亲和力传播算法
def AP(weight, damp):
    simi = []
    for m in weight:  ##每个数字与所有数字的相似度列表，即矩阵中的一行
        temp = []
        for n in weight:
            s = -np.sqrt((m[0] - n[0]) ** 2 + (m[1] - n[1]) ** 2)  ##采用负的欧式距离计算相似度
            temp.append(s)
        simi.append(temp)
    p = np.min(simi)  # p值为参考度
    # p = np.median(simi) #将所有相似度高的文章分为一类，其余一篇为一类
    ap = AffinityPropagation(damping=damp, max_iter=800, convergence_iter=30,
                             preference=p).fit(weight)  # damping为阻尼系数，取值为【0.5-1.0】
    y = ap.labels_
    return (y)


# 获取聚类后的各个类
def list_duplicates(seq):
    tally = defaultdict(list)
    for i, item in enumerate(seq):
        tally[item].append(i)
    return ((key, locs) for key, locs in tally.items()
            if len(locs) >= 1)


def similarity(tfidf, cluster_result, text_content, dictionary):
    dict2 = copy.deepcopy(dictionary)
    SimMatrix = (tfidf * tfidf.T).A
    for dup in sorted(list_duplicates(cluster_result)):
        print(dup)
        text_class = dup[1]
        for i in range(len(text_class)):  # 一一计算相似度（类似冒泡法）
            sims = []
            num = 0
            for j in range(i + 1, len(text_class)):
                sim = SimMatrix[text_class[i], text_class[j]]
                key_list = []
                value_list = []
                if sim > 0.8:  # 删除相似度高于阈值的文本
                    print('the ' + str(text_class[j] + 1) + ' th text is similar with the ' + str(text_class[i] + 1) +
                          ' th text, it should be deleted!')
                    for key, val in dict2.items():
                        key_list.append(key)
                        value_list.append(val)
                    get_value_index = value_list.index(text_content[text_class[j]])
                    url_del = key_list[get_value_index]  # 获取重复文本的url
                    if url_del in dictionary:
                        dictionary.pop(url_del)
                    num += 1  # 每个文本的重复个数，是否可作为热度？
                sims.append(sim)
            print('The number of repetitions of the ' + str(text_class[i] + 1) + ' th text is ' + str(num) + '.')
    return (dictionary)


def main_func(cur, stop_path, data_num, damping):
    whole_content = list(cur.fetchall())  # 获取数据表中所有字段
    temp_content = []
    urls = []
    for m in whole_content:
        urls.append(m[2])
    contents = []
    for n in whole_content:
        contents.append(n[7])
    dict_url = dict(zip(urls, whole_content))
    tfidf = tfidf_value(data_num, contents, stop_path)
    weight = tfidf.toarray()  # tfidf权重
    # components = 20
    # decomp_result = text_simi.test_pca(weight,components) #降维
    # print(decomp_result)
    result = AP(weight, damping)
    print(result)  # 聚类后结果
    source = result
    dict_url = similarity(tfidf, source, whole_content, dict_url)
    for value in dict_url.values():
        temp_content.append(value)
    print(len(temp_content))

    # wipe_table = 'truncate financial.netfin_filtered_message'
    # cur.execute(wipe_table)

    source_urlselect = '''select url from netfin_filtered_message'''
    url_list = []
    # 获取数据库的URL
    cur.execute(source_urlselect)
    for r in cur:
        url_list.append(r[0])

    for content in temp_content:
        # 避免插入重复新闻
        if len(url_list) != 0:
            if content[2] in url_list:
                continue
        source_messageInsert = '''insert into netfin_filtered_message(title,url,net_name,ent_time,keyword,digest,content,hot_degree,scan_id)
                            values('{title}','{url}','{net_name}','{ent_time}','{keyword}','{digest}','{content}','{hot_degree}','{scan_id}')'''

        sqltext = source_messageInsert.format(title=pymysql.escape_string(content[1]),
                                              url=pymysql.escape_string(content[2]),
                                              net_name=pymysql.escape_string(content[3]),
                                              ent_time=pymysql.escape_string(
                                                  time.strftime("%Y-%m-%d %H:%M:%S", content[4].timetuple())),
                                              keyword=pymysql.escape_string(content[5]),
                                              digest=pymysql.escape_string(content[6]),
                                              content=pymysql.escape_string(content[7]),
                                              hot_degree=pymysql.escape_string(str(content[8])),
                                              scan_id=pymysql.escape_string(str(content[9]))
                                              )
        cur.execute(sqltext)


def setup():
    settings = get_project_settings()
    conn = pymysql.connect(
            host=settings.get('MYSQL_HOST'),
            port=settings.get('MYSQL_PORT'),
            db=settings.get('MYSQL_DBNAME'),
            user=settings.get('MYSQL_USER'),
            passwd=settings.get('MYSQL_PASSWD'),
            charset='utf8',
            use_unicode=True)  # 创建与mysql的连接
    conn.autocommit(True)
    cur = conn.cursor()  # 获取操作游标，cursor为游标位置
    print('succeed!')
    cf = load_config()
    stoppath = cf.get('Section', 'stopwords_path')
    select_sql = 'select * from netfin_source_message'  # SQL语句
    cur.execute(select_sql)  # 执行该SQL语句
    data_number = cur.rowcount
    print('There are ' + str(data_number) + ' news.')
    damping = 0.6  # 阻尼系数，0.5-1之间
    main_func(cur, stoppath, data_number, damping)

# 读取配置文件
def load_config():
    cf = configparser.ConfigParser()
    cf.read('news_spider/spiders/config.cfg')
    return cf