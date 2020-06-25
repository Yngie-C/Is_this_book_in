# 필요한 모듈 임포트하기(1, Flask / MySQL / os / re)
from flask import Flask, render_template, request, redirect, session, url_for
import os
from datetime import date
import re
from flaskext.mysql import MySQL
from flask_restful import Resource, Api, reqparse

# 필요한 모듈 임포트하기(2, Crawling)
import requests
from bs4 import BeautifulSoup
from urllib import parse
import urllib

app = Flask(__name__)
api = Api(app)

# DB 정보 입력하기
mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'Username'
app.config['MYSQL_DATABASE_PASSWORD'] = 'DB_Password'
app.config['MYSQL_DATABASE_DB'] = 'DB_Name'
app.config['MYSQL_DATABASE_HOST'] = 'Hostname'
mysql.init_app(app)

app.secret_key = 'anything'
today = date.today()


# 로그인 페이지 구성하기
@app.route('/', methods=['GET','POST'])
def joinin():
    if request.method == 'GET':
        return render_template('joininPage.html')
    else:
        userid = request.form.get('userid')     # 로그인 정보 1: 인스타그램 ID
        session['userid'] = userid              
        password = request.form.get('pwd')      # 로그인 정보 2: 생년월일
        try:
            conn = mysql.connect()
            cur = conn.cursor()
            cur.execute(f'select password from user_tb where userid="{userid}"')
            chk_pwd = cur.fetchall()[0][0]
            # ID와 생년월일이 맞는지 DB에서 비교한다.

            if password in chk_pwd:
                return redirect('/main')
            else:
                return render_template('error.html', msg='아이디 또는 휴대전화 번호를 확인해 주세요')
        except Exception as ex:
            return render_template('error.html', msg='본인의 아이디가 맞는지 확인해 주세요')


# 로그아웃
@app.route('/logout')
def logout():
    session.pop('userid', None)
    return redirect(url_for('joinin'))


# 회원가입 페이지 구성하기
@app.route('/joinon', methods=['GET','POST'])
def joinon():
    conn = mysql.connect()
    cur = conn.cursor()
    
    if request.method == 'GET':
        return render_template('joinOnPage.html')
    else:
        try:
            userid = request.form.get('userid')     # 회원가입 정보 1 : 인스타그램 ID
            password = request.form.get('pwd')      # 회원가입 정보 2 : 생년월일
            gender = request.form.get('gender')     # 회원가입 정보 3 : 성별
            age = request.form.get('age')           # 회원가입 정보 4 : 연령대
            joinDate = today                        # 회원가입 정보 5 : 가입일
            
            cur.execute('select userid from user_tb')
            unique_id = cur.fetchall()
            chk_id = []
            for i in unique_id:
                chk_id.append(*i)
            cur.execute('select password from user_tb')
            unique_pwd = cur.fetchall()
            chk_pwd = []
            for i in unique_pwd:
                chk_pwd.append(*i)
            comp = re.compile('[가-힣]')
            
            # 회원가입 시 발생하는 각종 예외사항 처리
            if userid is '':
                return render_template('error.html', msg='양식에 맞는 ID를 입력 해 주세요')
            elif re.findall(comp, userid) != []:
                return render_template('error.html', msg='양식에 맞는 ID를 입력 해 주세요')
            elif userid in unique_id:
                return render_template('error.html', msg='이미 있는 아이디입니다')
            elif not (len(password) == 11 and password.startswith('010')):
                return render_template('error.html', msg='올바른 휴대전화 번호를 입력 해 주세요')
            elif not (userid and password):
                return render_template('error.html', msg='아이디/휴대전화 번호를 잘 입력 해 주세요')
            elif password in unique_pwd:
                return render_template('error.html', msg='이미 있는 휴대전화 번호입니다')
            elif not (gender and age):
                return render_template('error.html', msg='성별/연령대를 잘 선택 해 주세요')
            else: # 모두 입력이 정상적으로 되었다면 DB에 입력됨
                try:
                    cur.execute('select userid from user_tb')
                    unique_id = cur.fetchall()
                    chk_lst = []
                    for i in unique_id:
                        chk_lst.append(*i)

                    if userid not in chk_lst:
                        cur.execute(f'insert into user_tb (userid, password, gender, age, joinDate) values ("{userid}","{password}","{gender}","{age}","{joinDate}")')
                        conn.commit()
                    else:
                        return render_template('error.html', msg='이미 있는 ID입니다. 다른 ID로 가입해 주세요')

                except Exception as ex:
                    pass

        except Exception as ex:
            render_template('error.html', msg='아이디/휴대전화 번호에 이상한 문자가 끼어있어요')
        return redirect('/')



# 메인 페이지(등록 키워드 및 크롤링 정보 출력) 구성하기
@app.route('/main', methods=['GET','POST'])
def main():
    conn = mysql.connect()
    cur = conn.cursor()
    
    userid = session['userid']
    if request.method == 'GET':
        cur.execute(f'select keyword from key_tb where userid = "{userid}" and actDeact="1"')
        keys_tuple = cur.fetchall()
        keywords = []
        for i in keys_tuple:
            keywords.append(*i)

        # 검색주소 url 인코딩 함수 정의   
        def searchUrl(searchString):
            url_f = {"SearchTarget":"UsedStore", "SearchWord":searchString, "x":0, "y":0}
            url = "https://www.aladin.co.kr/search/wsearchresult.aspx?"+ urllib.parse.urlencode(url_f, encoding = "cp949")
            return url

        # 크롤링하기 위한 함수 정의 
        def aladinBooks(url):
            req = requests.get(url)
            html = req.text
            soup = BeautifulSoup(html, "html.parser")
            books_info = []
            try:
                for i in range(1, 8):
                    book_info = []
                    book = soup.select_one('#Search3_Result > div:nth-child('+str(i)+') > table')
                    book_info.append(book.find('img')['src']) # 책 표지
                    book_info.append(book.find('b').get_text()) # 책 제목
                    book_info.append(book.find_all('li')[1].get_text()) # 서지정보
                    if book.find_all('div')[-2].get_text() != '':
                        book_info.append(book.find_all('div')[-2].get_text()) # 보유지점 및 재고소진 안내
                    else:
                        book_info.append("죄송합니다. 판매 종료된 상품입니다.")
                    books_info.append(book_info)
            except Exception as ex:
                pass
            return books_info
        books_info = []
        for key in keywords:
            book_info = aladinBooks(searchUrl(key))
            books_info.append(book_info)
        return render_template('mainPage.html', msg=f'{userid}', keywords=(keywords, books_info))


# 키워드 관리 페이지 구성하기
@app.route('/keyword', methods=['GET', 'POST'])
def keyword():
    conn = mysql.connect()
    cur = conn.cursor()
    userid = session['userid']
    cur.execute(f'select keyword from key_tb where userid = "{userid}" and actDeact="1"')
    keys_tuple = cur.fetchall()
    keywords = []
    for i in keys_tuple:
        keywords.append(*i)
    return render_template('keywordPage.html', keywords=keywords)


# 키워드를 추가하는 경우
@app.route('/add', methods=['POST'])
def add():
    conn = mysql.connect()
    cur = conn.cursor()
    userid = session['userid']
    keyword = request.form.get('key')
    if keyword == '':
        return render_template('error.html', msg='키워드를 제대로 입력해주세요.')
    else:
        keyAddDate = today
        cur.execute(f'select keyword from key_tb where actDeact=1 and userid="{userid}"')
        keynum_tuple = cur.fetchall()
        keyword_num = []
        for i in keynum_tuple:
            keyword_num.append(*i)

        # 최대 10개까지 키워드를 등록하게 하고 10개가 넘어갈 경우 에러 메시지 출력
        if len(keyword_num) > 9:
            return render_template('error.html', msg='최대 10개의 키워드를 등록하셨습니다.')
        else:
            cur.execute(f'insert into key_tb (userid, keyword, keyAddDate) values ("{userid}","{keyword}","{keyAddDate}")')
            conn.commit()
            cur.execute(f'select keyword from key_tb where userid = "{userid}" and actDeact="1"')
            keys_tuple = cur.fetchall()
            keywords = []
            for i in keys_tuple:
                keywords.append(*i)
            return render_template('keywordPage.html', keywords=keywords)


# 키워드를 제거하는 경우
@app.route('/delete', methods=['POST'])
def delete():
    conn = mysql.connect()
    cur = conn.cursor()
    userid = session['userid']
    
    # 키워드를 지운 뒤 새로고침을 했을 때 발생하는 에러 방지
    try:
        keyword = request.form.get('deact').replace("['",'').replace("']",'')
        key_add_date = today
        cur.execute(f'select idx from key_tb where keyword="{keyword}" and userid="{userid}" and actDeact="1"')
        key_idx = cur.fetchone()[0]

        # 해당 키워드의 활성화 상태(actDeact)를 0으로 변경
        cur.execute(f'update key_tb set actDeact = "0" where idx = {key_idx}')
        conn.commit()

        # actDeact=1인 키워드만 리스트에 저장하여 반환
        cur.execute(f'select keyword from key_tb where userid = "{userid}" and actDeact="1"')
        keys_tuple = cur.fetchall()
        keywords = []
        for i in keys_tuple:
            keywords.append(*i)
        return render_template('keywordPage.html', keywords=keywords)

    except Exception:
        return render_template('error.html', msg='지울 키워드가 없습니다.')


# 첫 사용자를 위한 가이드 띄우기
@app.route('/firstguide')
def firstguide():
    return render_template('firstGuide.html')


# 실행하기 위한 함수 
if __name__ == '__main__':

    # 헤로쿠 포트 동적 할당을 위한 설정
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)




