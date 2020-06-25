# 크롤링 libraries
import requests
from bs4 import BeautifulSoup
from urllib import parse
import urllib

# mysql load
import pymysql

import imageio
imageio.plugins.ffmpeg.download()

# instagram api and apscheduler load
from InstagramAPI import InstagramAPI
import os
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler


# MySQL DATA load
class mysqlData:
    def connect_sql(self):
        connect = pymysql.connect(host='hostname',
                        port=3306,
                        user='username',
                        password='db_password',
                        db='db_name')   # pymysql을 사용하여 DB와 연결
        cur = connect.cursor()
        return cur
    def bring_user(self, cur):
        cur.execute('select userid from user_tb')   # 유저 목록 불러오기
        user = cur.fetchall()
        users = [i[0] for i in user]
        return users
    def bring_keyword(self, cur):
        cur.execute('select userid, keyword from key_tb where actDeact="1"')    # 해당되는 유저의 키워드 불러오기
        keywords = cur.fetchall()
        return keywords
    def dict_users(self, users, keywords):
        users_keyword = []
        for i in users:
            keyword = []
            for j in keywords:
                if i == j[0]:
                    keyword.append(j[1])
            users_keyword.append([i, keyword])
        user_dict = {}
        for i in users_keyword:
            user_dict.update({i[0]:i[1]})   #유저를 key로, 키워드 리스트를 value로 하는 딕셔너리 만들기
        return user_dict

# crawling 함수 정의
def searchUrl(searchString):
    url_f = {"SearchTarget":"UsedStore", "SearchWord":searchString, "x":0, "y":0}
    url = "https://www.aladin.co.kr/search/wsearchresult.aspx?"+ urllib.parse.urlencode(url_f, encoding = "cp949")
    return url

def aladinBooks(url):
    req = requests.get(url)
    html = req.text
    soup = BeautifulSoup(html, "html.parser")
    books_info = ''     # list자료형은 encode, decode가 되지 않으므로 string으로 생성
    try:
        for i in range(1, 8):
            book_info = ''
            book = soup.select_one('#Search3_Result > div:nth-child('+str(i)+') > table')
            book_info += '책 이름 : ' + book.find('b').get_text() # 책 제목
            book_info += '\n'
            book_info += '서지 정보 : ' + book.find_all('li')[1].get_text() # 서지정보
            book_info += '\n'
            if book.find_all('div')[-2].get_text() != '':
                book_info += '재고 보유매장 : ' + book.find_all('div')[-2].get_text() # 보유지점 및 재고소진 안내
                book_info += '\n\n'
            else:
                book_info += "*판매 완료*" # 보유지점 및 재고소진 안내
                book_info += '\n\n'
            books_info += book_info
    except Exception as ex:
        pass
    return books_info


# 크롤링 및 인스타그램 DM 전송
class instaDM:
    def __init__(self, user_dict):
        self.user_dict = user_dict

    def crawl_and_dm(self):
        for key, values in self.user_dict.items():
            for value in values:
                books_info = '등록 키워드 : '+value+'\n\n'
                tmp = aladinBooks(searchUrl(value))
                if tmp != '':
                    books_info += tmp
                else:
                    books_info += '키워드로 등록된 책 없음'
                api = InstagramAPI("Instagram ID", "Instagram PWD")  # (DM을 보낼) 본인 인스타그램 계정의 ID와 비밀번호 입력
                api.login()
                api.searchUsername(key)
                response = api.LastJson
                user_id = response['user']['pk']
                text=(books_info).encode('utf-8')
                api.direct_message(text.decode('latin-1'), user_id)

            api= InstagramAPI("Instagram ID", "Instagram PWD")  # (DM을 보낼) 본인 인스타그램 계정의 ID와 비밀번호 입력
            api.login()
            api.searchUsername(key)
            response = api.LastJson
            user_id = response['user']['pk']
            text=('위 알림 메세지는 책 들어와써?(https://isthisbookin.herokuapp.com)에 등록하신 키워드를 바탕으로 전송됩니다. 만약 알림을 중지하시려면 등록하신 키워드를 모두 지워주세요.').encode('utf-8')
            api.direct_message(text.decode('latin-1'), user_id)


# APscheduler를 사용하여 크롤링 실행하기 (cron방식)
if __name__ == '__main__':
    sql = mysqlData()                           # mysqlData 함수 할당
    cur = sql.connect_sql()                     # mysql에 연결하기
    users = sql.bring_user(cur)                 # user data select
    keyword = sql.bring_keyword(cur)            # keyword data select
    user_dict = sql.dict_users(users, keyword)  # dictionary로 combine

    instadm = instaDM(user_dict)                # user_dict를 변수로 하는 instaDM 함수 할당

    sched = BlockingScheduler()                 # BlockingScheduler 함수 할당

    sched.add_job(
        instadm.crawl_and_dm(),
        'cron',
        hour=9,
        minute=30
    )
    
    sched.add_job(
        instadm.crawl_and_dm,
        'cron',
        hour=18,
        minute=30
    )
    # 크롤링 및 DM 보내기 일정 추가
    
    try:
        sched.start()
    except KeyboardInterrupt:
        print("End")
        pass