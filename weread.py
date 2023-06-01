# -*- coding: utf-8 -*-
"""
Created on Fri May 26 09:19:25 2023

@author: 

helpdoc:
https://readwise.io/api_deets
https://github.com/zhaohongxuan/obsidian-weread-plugin/blob/main/docs/weread-api.md
https://github.com/peixian/zotfile-to-readwise/blob/main/annotations.py

"""

import json
import logging
import argparse
import re
import time
import requests
from requests.utils import cookiejar_from_dict
from http.cookies import SimpleCookie
from datetime import datetime
import hashlib
import pytz


WEREAD_URL = "https://weread.qq.com/"
WEREAD_NOTEBOOKS_URL = "https://i.weread.qq.com/user/notebooks"
WEREAD_BOOKMARKLIST_URL = "https://i.weread.qq.com/book/bookmarklist"
WEREAD_CHAPTER_INFO = "https://i.weread.qq.com/book/chapterInfos"
WEREAD_READ_INFO_URL = "https://i.weread.qq.com/book/readinfo"
WEREAD_REVIEW_LIST_URL = "https://i.weread.qq.com/review/list"
WEREAD_BOOK_INFO = "https://i.weread.qq.com/book/info"


def parse_cookie_string(cookie_string):
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    cookies_dict = {}
    cookiejar = None
    for key, morsel in cookie.items():
        cookies_dict[key] = morsel.value
        cookiejar = cookiejar_from_dict(
            cookies_dict, cookiejar=None, overwrite=True
        )
    return cookiejar


def get_bookmark_list(bookId):
    """获取我的划线"""
    params = dict(bookId=bookId)
    r = session.get(WEREAD_BOOKMARKLIST_URL, params=params)
    if r.ok:
        updated = r.json().get("updated")
        updated = sorted(updated, key=lambda x: (
            x.get("chapterUid", 1), int(x.get("range").split("-")[0])))
        return r.json()["updated"]
    return None


def get_read_info(bookId):
    params = dict(bookId=bookId, readingDetail=1,
                  readingBookIndex=1, finishedDate=1)
    r = session.get(WEREAD_READ_INFO_URL, params=params)
    if r.ok:
        return r.json()
    return None


def get_bookinfo(bookId):
    """获取书的详情"""
    params = dict(bookId=bookId)
    r = session.get(WEREAD_BOOK_INFO, params=params)
    isbn = ""
    if r.ok:
        data = r.json()
        isbn = data["isbn"]
        newRating = data["newRating"]/1000
    return (isbn, newRating)


def get_review_list(bookId):
    """获取笔记"""
    params = dict(bookId=bookId, listType=11, mine=1, syncKey=0)
    r = session.get(WEREAD_REVIEW_LIST_URL, params=params)
    reviews = r.json().get("reviews")
    summary = list(filter(lambda x: x.get("review").get("type") == 4, reviews))
    reviews = list(filter(lambda x: x.get("review").get("type") == 1, reviews))
    reviews = list(map(lambda x: x.get("review"), reviews))
    reviews = list(map(lambda x: {**x, "note": x.pop("content")}, reviews))
    reviews = list(map(lambda x: {**x, "markText": x.get("abstract",x.get('note'))}, reviews))    
    return summary, reviews


def get_table_of_contents():
    """获取目录"""
    return {
        "type": "table_of_contents",
        "table_of_contents": {
            "color": "default"
        }
    }


def get_heading(level, content):
    if level == 1:
        heading = "heading_1"
    elif level == 2:
        heading = "heading_2"
    else:
        heading = "heading_3"
    return {
        "type": heading,
        heading: {
            "rich_text": [{
                "type": "text",
                "text": {
                    "content": content,
                }
            }],
            "color": "default",
            "is_toggleable": False
        }
    }


def get_quote(content):
    return {
        "type": "quote",
        "quote": {
            "rich_text": [{
                "type": "text",
                "text": {
                    "content": content
                },
            }],
            "color": "default"
        }
    }


def get_callout(content, style, colorStyle, reviewId):
    # 根据不同的划线样式设置不同的emoji 直线type=0 背景颜色是1 波浪线是2
    emoji = "🌟"
    if style == 0:
        emoji = "💡"
    elif style == 1:
        emoji = "⭐"
    # 如果reviewId不是空说明是笔记
    if reviewId != None:
        emoji = "✍️"
    color = "default"
    # 根据划线颜色设置文字的颜色
    if colorStyle == 1:
        color = "red"
    elif colorStyle == 2:
        color = "purple"
    elif colorStyle == 3:
        color = "blue"
    elif colorStyle == 4:
        color = "green"
    elif colorStyle == 5:
        color = "yellow"
    return {
        "type": "callout",
        "callout": {
            "rich_text": [{
                "type": "text",
                "text": {
                    "content": content,
                }
            }],
            "icon": {
                "emoji": emoji
            },
            "color": color
        }
    }


def get_notebooklist():
    """获取笔记本列表"""
    r = session.get(WEREAD_NOTEBOOKS_URL)
    if r.ok:
        data = r.json()
        books = data.get("books")
        books.sort(key=lambda x: x["sort"])
        return books
    else:
        print(r.text)
    return None



def transform_id(book_id):
    id_length = len(book_id)

    if re.match("^\d*$", book_id):
        ary = []
        for i in range(0, id_length, 9):
            ary.append(format(int(book_id[i:min(i + 9, id_length)]), 'x'))
        return '3', ary

    result = ''
    for i in range(id_length):
        result += format(ord(book_id[i]), 'x')
    return '4', [result]

def calculate_book_str_id(book_id):
    md5 = hashlib.md5()
    md5.update(book_id.encode('utf-8'))
    digest = md5.hexdigest()
    result = digest[0:3]
    code, transformed_ids = transform_id(book_id)
    result += code + '2' + digest[-2:]

    for i in range(len(transformed_ids)):
        hex_length_str = format(len(transformed_ids[i]), 'x')
        if len(hex_length_str) == 1:
            hex_length_str = '0' + hex_length_str

        result += hex_length_str + transformed_ids[i]

        if i < len(transformed_ids) - 1:
            result += 'g'

    if len(result) < 20:
        result += digest[0:20 - len(result)]

    md5 = hashlib.md5()
    md5.update(result.encode('utf-8'))
    result += md5.hexdigest()[0:3]
    return result

def ctime2utc(ctime):

    # 将 Unix 时间戳转换为 datetime 对象
    dt_object = datetime.fromtimestamp(ctime)
    
    # 设置时区为东八区
    timezone = pytz.timezone('Asia/Shanghai')
    dt_object = timezone.localize(dt_object)
    
    # 将 datetime 对象转换为 ISO 8601 格式的字符串
    iso_format = dt_object.isoformat()
    
    return iso_format  # 输出：2016-09-28T15:50:12+08:00

#%%远程版本


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("weread_cookie")
    parser.add_argument("readwise_token")
    options = parser.parse_args()
    weread_cookie = options.weread_cookie
    readwise_token = options.readwise_token
    session = requests.Session()
    session.cookies = parse_cookie_string(weread_cookie)
    session.get(WEREAD_URL)
    books = get_notebooklist()
    
    
    #提取书籍和笔记的数量
    querystring = {
        'page_size':1000,
        "category": "books",
        "source":"weread_app",
        
    }
    
    response = requests.get(
        url="https://readwise.io/api/v2/books/",
        headers={"Authorization": f"Token {readwise_token}"},
        params=querystring
    )
    
    data = response.json()
    readwise_book_num=data['count']
    readwise_book = {book['title']:book['num_highlights'] for book in data['results']}
    
    
    #开始导入
    if (books != None):
        for book in books[:]:
            #无笔记跳过
            if book.get("noteCount",0)+book.get("reviewCount",0)==0:
                continue
            sort = book["sort"]
            book = book.get("book")
            title = book.get("title").replace('/','').replace(':','')
            cover = book.get("cover")
            bookId = book.get("bookId")
            author = book.get("author")
            
            bookmark_list = get_bookmark_list(bookId)
            summary, reviews = get_review_list(bookId)
            bookmark_list.extend(reviews)
            #print(title,bookId)
            
            if title in readwise_book and len(bookmark_list)==readwise_book[title]:
                print("跳过",title,bookId)
                continue
            else:
                annotations = []
                
            
            bookmark_list = sorted(bookmark_list, key=lambda x: (
                x.get("chapterUid", 1), 0 if (x.get("range", "") == "" or x.get("range").split("-")[0]=="" ) else int(x.get("range").split("-")[0])))
            
                
            for bookmark in bookmark_list:
                time.sleep(0.3)
                
                params = {
                    "text": bookmark['markText'],
                    "title": title,
                    "author": author,
                    "source_type": "weread_app",
                    "category": "books",
                    # "location": bookmark['range'],
                    # "location_type": ,
                    'image_url':cover,
                    'source_url':f"https://weread.qq.com/web/reader/{calculate_book_str_id(bookId)}",
                    "highlighted_at": ctime2utc(bookmark['createTime']),#"2020-07-14T20:11:24+00:00",
                    
                }
                if 	'note' in bookmark:
                    params['note'] = bookmark.get('note')
                    reviewId  =  bookmark.get('reviewId')
                    params['highlight_url'] = f'https://weread.qq.com/review-detail?reviewid={reviewId}&type=1'
                    
                annotations.append(params)
    
            
    
           
            resp = requests.post(
                url="https://readwise.io/api/v2/highlights/",
                headers={"Authorization": f"Token {readwise_token}"},
                # headers={"Authorization": f"Token {readwise_token}"},
                json={
                    "highlights": annotations
                }
            )
            # print(resp)
            time.sleep(8)
