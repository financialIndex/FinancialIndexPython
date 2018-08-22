# -*- coding: utf-8 -*-
import time
import datetime
import configparser
import re
from textrank4zh import TextRank4Keyword, TextRank4Sentence


# 划分hot_degree
def divide_hot_degree(net_name, hot_degree):
    if net_name == 'leiphone_news':
        if hot_degree == 0:
            return 0
        elif hot_degree > 0 and hot_degree <= 2:
            return 1
        elif hot_degree > 2 and hot_degree <= 4:
            return 2
        elif hot_degree > 4 and hot_degree <= 6:
            return 3
        elif hot_degree > 6 and hot_degree <= 8:
            return 4
        else:
            return 5
    else:
        if hot_degree == 0:
            return 0
        elif hot_degree > 0 and hot_degree <= 20:
            return 1
        elif hot_degree > 20 and hot_degree <= 40:
            return 2
        elif hot_degree > 40 and hot_degree <= 60:
            return 3
        elif hot_degree > 60 and hot_degree <= 80:
            return 4
        else:
            return 5


# 比较时间的大小
def time_cmp(now_date, article_date):
    now_date = time.strftime("%Y-%m-%d %H:%M:%S",
                             time.localtime(now_date))
    d1 = datetime.datetime.strptime(now_date, '%Y-%m-%d %H:%M:%S')
    d2 = datetime.datetime.strptime(article_date, '%Y-%m-%d %H:%M:%S')
    return (d1 - d2).days


# 读取配置文件
def load_config():
    cf = configparser.ConfigParser()
    cf.read('news_spider/spiders/config.cfg')
    return cf


# 去掉文章的空格
def fix_content(s):
    return re.sub('\s', '', s)


# 根据文章抽取关键词和摘要 leiphone
def leiphone_keyword_abstract(article, keywords_len, sentences_len):
    # 抽取关键词
    tr4w = TextRank4Keyword()
    tr4w.analyze(text=article, lower=True, window=2)
    keywords = []
    for item in tr4w.get_keywords(keywords_len, word_min_len=1):
        keywords.append(item.word)
    # 抽取摘要
    sentences = article.split('。')
    first_sentence = sentences[0]
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=article, lower=True, source='all_filters')
    abstract = []
    abstract.append(first_sentence + '。')
    for item in tr4s.get_key_sentences(num=sentences_len):
        if item.sentence != first_sentence:
            abstract.append(item.sentence + '。')
    abstract = '\n'.join(abstract)
    return keywords, abstract


# 根据文章抽取关键词和摘要 sina
def sina_keyword_abstract(article, keywords_len, sentences_len):
    # 抽取关键词
    tr4w = TextRank4Keyword()
    tr4w.analyze(text=article, lower=True, window=2)
    keywords = []
    for item in tr4w.get_keywords(keywords_len, word_min_len=1):
        keywords.append(item.word)
    # 抽取摘要
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=article, lower=True, source='all_filters')
    abstract = []
    for item in tr4s.get_key_sentences(num=sentences_len):
        if str(item.sentence).startswith('原标题') or str(item.sentence).startswith('责任编辑') or str(
                item.sentence).startswith('来源'):
            continue
        abstract.append(item.sentence + '。')
    abstract = '\n'.join(abstract)
    return keywords, abstract


# 根据文章抽取关键词和摘要 36r
def _36r_keyword_abstract(article, keywords_len, sentences_len):
    # 抽取关键词
    tr4w = TextRank4Keyword()
    tr4w.analyze(text=article, lower=True, window=2)
    keywords = []
    for item in tr4w.get_keywords(keywords_len, word_min_len=1):
        keywords.append(item.word)
    # 抽取摘要
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=article, lower=True, source='all_filters')
    abstract = []
    for item in tr4s.get_key_sentences(num=sentences_len):
        abstract.append(item.sentence + '。')
    abstract = '\n'.join(abstract)
    return keywords, abstract


# 根据文章抽取摘要 tencent
def tencent_keyword_abstract(article, sentences_len):
    # 抽取摘要
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=article, lower=True, source='all_filters')
    abstract = []
    for item in tr4s.get_key_sentences(num=sentences_len):
        abstract.append(item.sentence + '。')
    abstract = '\n'.join(abstract)
    return abstract


