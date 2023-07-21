import csv

from flask import Flask, render_template, request, send_file, url_for
import pandas as pd
import cx_Oracle
from datetime import datetime

from werkzeug.utils import secure_filename, redirect, send_from_directory

from vo.PagingVO import PagingVO
import matplotlib.pyplot as plt
import mpld3

import random
import string
import os

import numpy as np

app = Flask(__name__)

# # Oracle 데이터베이스에 연결, JOINUS와 임시 연결
con = cx_Oracle.connect("spring_project", "1234", "localhost:1521/xe", encoding="UTF-8")
cursor = con.cursor()

realtimeData = {}

# 실시간 센서데이터 저장
realtile_sensor_cols = set()
realtile_sensor_rows = {}

columns = set() # 실시간 센서 + csv파일 추가의 속성들을 담기위함
rows = {} # 실시간 센서 + csv파일 추가의 데이터들을 담기위함

# DB에 과업데이터는 안돼겠다. 데이터가 너무 큼

# 기본데이터 추가
@app.route("/dummy")
def dummy():
    cursor.execute("select * from user_table where taskNumber = 4")
    taskPath = cursor.fetchone()

    data = pd.read_csv(taskPath[3])

    colList = [col for col in data.columns if data.iloc[1][col] != 0]

    for col in colList[1:]:
        columns.add(col)
    for idx in data.index:
        date = HoursTenUnder(data.iloc[idx]['DATE'])
        for col in colList[1:]:
            if date not in rows:
                rows[date] = {}
            rows[date][col] = data.iloc[idx][col]
    print("속성 : ", columns, " | 행 : ", rows)
    print("정렬 : ", sorted(columns))
    return render_template("main.html");

# 계측 건출물 등록 화면으로 이동
@app.route("/createbuild")
def createbuild():
    return render_template("create-building.html");

# 메인화면(계측 건축물 리스트 화면)
@app.route("/")
def buildingList():
    # 저장된 정보를 화면에 표시하기 위해 데이터 조회
    cursor.execute("SELECT bno, b_name, b_addr, b_image FROM building_table")
    buildList = cursor.fetchall()  # 건설물 정보 가져오기
    reversed_list = list(reversed(buildList))

    nowPage = request.args.get("nowPage", 1)   # 현재 페이지
    cntPerPage = request.args.get("cntPerPage", 6) # 페이지 단위

    paging = PagingVO(len(buildList), int(nowPage), int(cntPerPage), int(cntPerPage));

    return render_template("buildings.html", buildList=reversed_list,
                           listLength=len(buildList),
                           nowPage=int(paging.nowPage),
                           lastPage=int(paging.lastPage),
                           startPage=int(paging.startPage),
                           endPage=int(paging.endPage),
                           cntPage=int(paging.cntPage),
                           cntPerPage=int(paging.cntPerPage));

# 계측 건축물 과업 리스트 화면으로 이동
@app.route("/task/<bno>")
def main(bno):
    # 과업 전부 가져오기
    cursor.execute("SELECT taskNumber, task, name, pwd, bno FROM user_table WHERE bno = :bno", {"bno": bno})
    taskNameList = cursor.fetchall()  # 과업주소 전부 가져오기
    cursor.execute("select b_image from building_table where bno = :bno", {"bno":bno})
    b_image = cursor.fetchone()

    # 페이징 처리(10개 단위로)
    nowPage = request.args.get("nowPage", 1)    # 현재 페이지
    cntPerPage = request.args.get("cntPerPage", 10) # 페이지 단위

    paging = PagingVO(len(taskNameList), int(nowPage), int(cntPerPage), int(cntPerPage))

    return render_template("main.html",
                           taskNameList=taskNameList,
                           b_image=b_image[0],
                           listLength=len(taskNameList),
                           nowPage=int(paging.nowPage),
                           lastPage=int(paging.lastPage),
                           startPage=int(paging.startPage),
                           endPage=int(paging.endPage),
                           cntPage=int(paging.cntPage),
                           cntPerPage=int(paging.cntPerPage),
                           bno=bno)

# 과업생성 화면으로 이동
@app.route("/createTask/<bno>/<b_image>")
def createTask(bno,b_image):
    return render_template("insert.html" ,bno=bno , b_image=b_image)

# 특정 폴더에 이미지 저장 반환
@app.route("/uploadImage", methods=['POST'])
def upload():
    image = request.files['image']
    image_path = 'c:/upload/image.jpg'
    return image_path

# 과업정보와 생성자 정보를 DB에 삽입
@app.route("/insert", methods=['POST'])
def insert():
    task = request.form.get('task') # 과업이름
    floorPlan = request.files['floorPlan']  # 도면 파일저장주소
    data = request.files['data']    # 과업정보 파일저장주소
    name =  request.form.get('name')    # 관리자 성명
    phone =  request.form.get('phone')  # 관리자 전화번호
    email = request.form.get('email')   # 관리자 이메일
    pwd = request.form.get('pwd')   # 관리자 비밀번호
    bno = request.form.get('bno')   # 계측 건축물 번호
    b_image = request.form.get('b_image')   # 계측 건축물 이미지정보

    # 중복방지 랜덤값
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    # 중복방지 키워드 + 파일이름
    file_name = random_string + "." + secure_filename(floorPlan.filename)
    # 파일 주소 : "./task_images/파일이름 (현 프로젝트의 static으로 저장)
    file_path = os.path.join(app.static_folder, 'task_images', file_name)
    # 파일 주소 : "C:/upload_csv/"
    csv_path = 'C:/upload_csv/';

    # user_table에 데이터 저장
    u_data = (task, file_name, csv_path + data.filename, name, phone, email, pwd, bno)
    query = "insert into user_table values(task_seq.nextval, :1, :2, :3, :4, :5, :6, :7, :8)"
    cursor.execute(query, u_data)
    con.commit()
    
    # csv파일을 "C:/upload_csv/"에 저장
    upload_folder = 'C:/upload_csv/' # 파일을 저장할 폴더 경로를 지정해야 합니다.
    data.save(os.path.join(upload_folder, data.filename))
    # 도면파일을 "./task_images/"에 저장
    floorPlan.save(file_path)
    
    return redirect(url_for('main', bno=bno, b_image=b_image))

# 과업 상세정보 조회
@app.route("/get/<taskNumber>")
def get(taskNumber):
    # 과업번호를 비교하여 과업정보 조회
    cursor.execute("select * from user_table where taskNumber = :taskNumber", {'taskNumber': taskNumber})
    taskPath = cursor.fetchall()    # 과업주소 전부 가져오기
    taskList = list(taskPath[0])    # 0번째 원소를 불러옴으로써 튜플 제거
    return render_template("get.html", task=taskPath, b_image=taskList[2])

@app.route("/temp")
def temp():
    cursor.execute("select * from user_table where taskNumber = 4")
    taskPath = cursor.fetchone()

    data = pd.read_csv(taskPath[3])

    colList = [col for col in data.columns if data.iloc[1][col] != 0]

    # colList2 = sorted(columns)
    # print("col : ", colList2)
    # rowList2 = [[date[sensor] for sensor in date.keys()] for date in rows.values()]
    # print("row : ", rowList2)

    # matrix = np.array(rowList2)
    # rowList3 = np.transpose(matrix)
    cols = sorted(columns)
    cols.remove('BATT')
    cols.remove('TEMP')
    cols.insert(0, 'BATT')
    cols.insert(1, 'TEMP')
    return render_template("temp.html", cols=cols, rows=rows, dates=sorted(rows.keys()))

# csv파일 내용 [표]로 보여주기
@app.route("/get/chart")
def chart():
    taskNumber = request.args.get("taskNumber") # 과업번호
    nowPage = int(request.args.get('nowPage', 1))   # 현재 페이지
    cntPerPage = int(request.args.get('cntPerPage', 20))    # 페이지 단위

    # user_table에서 csv파일주소(속성:data)를 조회
    cursor.execute("select data from user_table where taskNumber = :1", taskNumber)
    taskPath = cursor.fetchone()
    data = pd.read_csv(taskPath[0]) # DB에서 가져온 데이터는 튜플이므로 tuple[0]으로 제거

    # 날짜 최솟값, 최댓갑 구하기
    minimum = data['DATE'].iloc[0].split(' ')[0]    # csv파일 첫행 날짜
    maximum = data['DATE'].iloc[-1].split(' ')[0]   # csv파일 마지막행 날짜

    # csv파일의 첫행을 가져와서 값이 0이 아닌 것들의 속성들을 묶음
    colList = [col for col in data.columns if data.iloc[1][col] != 0]
    # colList의 속성들을 이용하여 csv파일에서 범위에 맞는 행을 가져옴
    rowList = [data[col].iloc[(nowPage-1) * cntPerPage:nowPage * cntPerPage] for col in colList]

    # 날짜로 나눠진 데이터들을 속성끼리 묶음
    matrix = np.array(rowList)
    transposed_matrix = np.transpose(matrix)

    # 페이지 정보를 저장(startPage, lastPage 등 구한다)
    paging = PagingVO(len(data), nowPage, cntPerPage, cntPerPage);

    # 현재 시간 가져오기(초단위 까지)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    return render_template("data.html",
                           colList=colList,
                           taskNumber=taskNumber,
                           rowList=transposed_matrix,
                           minimum=minimum,
                           maximum=maximum,
                           nowPage=int(paging.nowPage),
                           lastPage=int(paging.lastPage),
                           startPage=int(paging.startPage),
                           endPage=int(paging.endPage),
                           cntPage=int(paging.cntPage),
                           cntPerPage=int(paging.cntPerPage),
                           realtimeData=realtimeData,
                           now=current_time);

@app.route("/get/chart/search")
def search():
    taskNumber = request.args.get("taskNumber")  # 과업번호
    nowPage = int(request.args.get('nowPage', 1))  # 현재 페이지
    cntPerPage = int(request.args.get('cntPerPage', 20))  # 페이지 단위
    selectedDate = request.args.get('selectedDate') # 선택날짜

    # user_table에서 csv파일주소(속성:data)를 조회
    cursor.execute("select data from user_table where taskNumber = :1", taskNumber)
    taskPath = cursor.fetchone()
    data = pd.read_csv(taskPath[0])  # DB에서 가져온 데이터는 튜플이므로 tuple[0]으로 제거

    # 날짜 최솟값, 최댓갑 구하기
    minimum = data['DATE'].iloc[0].split(' ')[0]  # csv파일 첫행 날짜
    maximum = data['DATE'].iloc[-1].split(' ')[0]  # csv파일 마지막행 날짜

    # csv파일에서 선택 날짜의 데이터만 가져오기
    data['DATE'] = pd.to_datetime(data['DATE']) # String -> datetime형태로 변환
    filtered_data = data[data['DATE'].dt.date == pd.to_datetime(selectedDate).date()]   # csv파일 데이터와 선택날짜를 비교하여 맞는 날짜만 저장

    # csv파일의 첫행을 가져와서 값이 0이 아닌 것들의 속성들을 묶음
    colList = [col for col in data.columns if data.iloc[1][col] != 0]
    # colList의 속성들을 이용하여 선별한 데이터에서 범위에 맞는 행을 가져옴
    rowList = [filtered_data[col].iloc[(nowPage-1) * cntPerPage:nowPage * cntPerPage] for col in colList]
    # 날짜 데이터를 datetime -> String형태로 변환
    rowList[0] = [date.strftime("%Y-%m-%d %H:%M") for date in rowList[0]]

    # 날짜로 나눠진 데이터들을 속성끼리 묶음
    matrix = np.array(rowList)
    transposed_matrix = np.transpose(matrix)    # 행렬 바꾸기

    # 페이지 정보를 저장(startPage, lastPage 등 구한다)
    paging = PagingVO(len(data), nowPage, cntPerPage, cntPerPage);

    # 현재 시간 가져오기(초단위 까지)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render_template("data.html",
                           colList=colList,
                           taskNumber=taskNumber,
                           selectedDate=selectedDate,
                           rowList=transposed_matrix,
                           minimum=minimum,
                           maximum=maximum,
                           nowPage=int(paging.nowPage),
                           lastPage=int(paging.lastPage),
                           startPage=int(paging.startPage),
                           endPage=int(paging.endPage),
                           cntPage=int(paging.cntPage),
                           cntPerPage=int(paging.cntPerPage),
                           realtimeData=realtimeData,
                           now=current_time);

# 한자릿 수 숫자 앞에 '0' 붙여주기('3' -> '03')
def HoursTenUnder(date):
    # 문자열에서 시간 구하기
    date_parts = date.split(' ')  # 공백을 기준으로 문자열 분할
    time_parts = date_parts[1].split(':')  # 시간 부분을 ':'를 기준으로 분할

    # 시간의 문자열 길이가 1이면 앞에 '0'을 붙여 2개의 문자로 만듦
    if len(time_parts[0]) == 1:
        time_parts[0] = '0' + time_parts[0]
        
    # 변경된 시간 부분을 다시 조합
    return date_parts[0] + ' ' + ':'.join(time_parts)

@app.route('/get/graph')
def graph():
    start = request.args.get("start")   # 선택날짜(처음)
    end = request.args.get("end")   # 선택날짜(끝)
    taskNumber = request.args.get("taskNumber") # 과업번호

    # user_table에서 csv파일주소(속성:data)를 조회
    cursor.execute("select data from user_table where taskNumber = :1", taskNumber);
    dataPath = cursor.fetchone()
    data = pd.read_csv(dataPath[0], sep=",")    # DB에서 가져온 데이터는 튜플이므로 tuple[0]으로 제거

    # 날짜 최솟값, 최댓갑 구하기
    minimum = data['DATE'].iloc[0].split(' ')[0]  # csv파일 첫행 날짜
    maximum = data['DATE'].iloc[-1].split(' ')[0]  # csv파일 마지막행 날짜

    # 날짜선택을 하지 않은 경우(선택오류, 첫 그래프 페이지 이동 시)
    if start == None or end == None:
        start = data.iloc[0]['DATE']    # csv파일의 첫행의 날짜를 가져옴
        end = pd.to_datetime(data.iloc[0]['DATE']) + pd.DateOffset(hours=1) # start에서 한달을 더함
        end = end.strftime('%Y-%m-%d %H:%M:%S') # datetime -> String형태로 변환

    # 기간 지정
    data['DATE'] = pd.to_datetime(data['DATE']) # csv파일 날짜를 String -> datetime으로 변환
    start_time = pd.Timestamp(start)    # 선택날짜(처음) 시간 저장
    end_time = pd.Timestamp(end)    # 선택날짜(처음) 시간 저장
    filtered_data = data[(data['DATE'] >= start_time) & (data['DATE'] <= end_time)] # start ~ end까지의 날짜에 맞는 데이터 분류

    # csv파일의 첫행을 가져와서 값이 0이 아닌 것들의 속성들을 묶음
    colList = [col for col in data.columns if data.iloc[1][col] != 0]
    # colList의 속성들을 이용하여 선별한 데이터에서 범위에 맞는 행을 가져옴
    rowList = [filtered_data[col].tolist() for col in colList]
    # 현재 시간 가져오기
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render_template("graph.html",
                           colList=colList,
                           rowList=rowList,
                           minimum=minimum,
                           maximum=maximum,
                           taskNumber=taskNumber,
                           start=start,
                           end=end,
                           realtimeData=realtimeData,
                           now=current_time)

# [표]에 있는 데이터를 다운로드폴더에 저장
@app.route('/downloadFile', methods=['POST'])
def download_file():
    # AJAX에서 보낸 파일 받기
    data = request.get_json()

    # taskNumber와 selectedDate 추출
    taskNumber = data.get('taskNumber')
    downloadStart = data.get('download_start')
    downloadEnd = data.get('download_end')

    # user_table에서 csv파일주소(속성:data)를 조회
    cursor.execute("select * from user_table where taskNumber = :1", taskNumber)
    task = cursor.fetchone()
    data = pd.read_csv(task[3]) # DB에서 가져온 데이터는 튜플이므로 tuple[0]으로 제거

    fileName = task[1] + ".csv"
    # 선택날짜(시작, 종료)가 csv파일 첫날 ~ 마지막날일 때
    if downloadStart == data['DATE'].iloc[0].split(' ')[0] and downloadEnd == data['DATE'].iloc[-1].split(' ')[0]:
        download_data = data
    else:
        fileName = task[1] + "(" + downloadStart + "~" + downloadEnd + ").csv"
        downloadEnd = pd.to_datetime(downloadEnd) + pd.DateOffset(days=1)  # 날짜데이터에 하루을 더함
        downloadEnd = downloadEnd.strftime('%Y-%m-%d')  # datetime -> String형태로 변환
        # 기간 지정
        data['DATE'] = pd.to_datetime(data['DATE'])  # csv파일 날짜를 String -> datetime으로 변환
        start_time = pd.Timestamp(downloadStart)  # 선택날짜(처음) 시간 저장
        end_time = pd.Timestamp(downloadEnd)  # 선택날짜(처음) 시간 저장
        download_data = data[(data['DATE'] >= start_time) & (data['DATE'] < end_time)]  # start ~ end까지의 날짜에 맞는 데이터 분류

    download_folder = os.path.expanduser("~") + "/Downloads"    # Downloads 폴더위치 저장
    filePath = os.path.join(download_folder, fileName)  # 다운로드 폴더 + 파일이름
    download_data.to_csv(filePath, index=False) # 해당 폴더에 csv파일 생성

    return "DOWNLOAD SUCCESS"


@app.route("/insertBuildingPost", methods=['POST'])
def insertBuildingPost():
    # 폼에서 전달된 데이터 가져오기
    b_name = request.form.get('b_name')
    b_addr = request.form.get('b_addr')
    b_image = request.files['b_image']

    # 파일 저장 경로 설정
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    file_name = random_string + "." + secure_filename(b_image.filename)
    file_path = os.path.join(app.static_folder, 'library_images', file_name)

    # 데이터베이스에 저장
    data = (b_name, b_addr, file_name)
    query = "INSERT INTO building_table VALUES (build_seq.nextval, :1, :2, :3)"
    cursor.execute(query, data)
    con.commit()

    # 파일 저장
    b_image.save(file_path)

    # 저장된 정보를 화면에 표시하기 위해 데이터 조회
    cursor.execute("SELECT bno, b_name, b_addr, b_image FROM building_table")
    buildList = cursor.fetchall()  # 건설물 정보 가져오기

    return redirect(url_for('buildingList'))

@app.route('/show_image/<filename>')
def show_image(filename):
    image_path = 'library_images/' + filename
    return send_from_directory('static', image_path)

# 센서의 측정 데이터 받기
@app.route('/sensor', methods=['POST'])
def handle_post_request():
    global realtimeData
    realtimeData = request.get_json()  # Get the JSON data from the request
    print("나오나 : ", realtimeData)
    # Extract the required values from the JSON data
    api_key = realtimeData.get('api_key')
    sensor = realtimeData.get('sensor')
    temp = realtimeData.get('temp')
    humi = realtimeData.get('humi')

    realtile_sensor_cols.add(sensor)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if now not in realtile_sensor_rows:
        realtile_sensor_rows[now] = {}
    if sensor not in realtile_sensor_rows[now]:
        realtile_sensor_rows[now][sensor] = temp

    # 불러올 때마다 등록(센서가 바뀔 수도 있으므로 속성과 데이터 둘다 추가)
    for col in realtile_sensor_cols:
        columns.add(col)
    rows.update(realtile_sensor_rows)

    # Process the data as needed
    # 예: 데이터베이스에 저장하거나 다른 작업 수행
    return "Success"

# 현재 시간, 센서이름, 온도 표시
@app.route('/realtimeSensor', methods=['POST'])
def realtimeSensor():
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('realtime-sensor.html', realtimeData=realtimeData, now=current_time)

@app.route('/sensor/chart')
def realtimeSensorChart():

    bno = request.args.get('bno')
    nowPage = int(request.args.get('nowPage', 1))
    cntPerPage = int(request.args.get('cntPerPage', 20))

    dates = sorted([key for key in rows.keys()])

    if len(dates) != 0:
        minimum = dates[0].split(' ')[0]
        maximum = dates[-1].split(' ')[0]
    else:
        minimum = None
        maximum = None

    paging_dates = dates[(nowPage - 1) * cntPerPage:nowPage * cntPerPage]
    paging_rows = {date: rows[date] for date in paging_dates}
    cols = sorted(columns)
    if 'BATT' in cols and 'TEMP' in cols:
        cols.remove('BATT')
        cols.remove('TEMP')
        cols.insert(0, 'BATT')
        cols.insert(1, 'TEMP')

    paging = PagingVO(len(dates), nowPage, cntPerPage, cntPerPage);

    if len(paging_rows) == 0:
        null_data = True
    else:
        null_data = False

    return render_template("sensor-chart.html",
                           bno=bno,
                           null_data=null_data,
                           cols=cols,
                           paging_rows=paging_rows,
                           paging_dates=paging_dates,
                           minimum=minimum,
                           maximum=maximum,
                           nowPage=int(paging.nowPage),
                           lastPage=int(paging.lastPage),
                           startPage=int(paging.startPage),
                           endPage=int(paging.endPage),
                           cntPage=int(paging.cntPage),
                           cntPerPage=int(paging.cntPerPage));

@app.route('/sensor/chart/search')
def realtimeSensorChartSearch():
    bno = request.args.get('bno')
    nowPage = int(request.args.get('nowPage', 1))
    cntPerPage = int(request.args.get('cntPerPage', 20))
    selectedDate = request.args.get('selectedDate')

    # 불러올 때마다 등록(센서가 바뀔 수도 있으므로 속성과 데이터 둘다 추가)
    for col in realtile_sensor_cols:
        columns.add(col)
    rows.update(realtile_sensor_rows)

    dates = sorted([key for key in rows.keys()])

    filter_dates = [date for date in dates if selectedDate in date]

    if len(dates) != 0:
        minimum = dates[0].split(' ')[0]
        maximum = dates[-1].split(' ')[0]
    else:
        minimum = None
        maximum = None

    paging_dates = filter_dates[(nowPage - 1) * cntPerPage:nowPage * cntPerPage]
    paging_rows = {date: rows[date] for date in paging_dates}
    cols = sorted(columns)
    if 'BATT' in cols and 'TEMP' in cols:
        cols.remove('BATT')
        cols.remove('TEMP')
        cols.insert(0, 'BATT')
        cols.insert(1, 'TEMP')

    paging = PagingVO(len(paging_dates), nowPage, cntPerPage, cntPerPage);

    if len(paging_rows) == 0:
        null_data = True
    else:
        null_data = False

    return render_template("sensor-chart.html",
                           bno=bno,
                           null_data=null_data,
                           cols=cols,
                           paging_rows=paging_rows,
                           paging_dates=paging_dates,
                           minimum=minimum,
                           maximum=maximum,
                           nowPage=int(paging.nowPage),
                           lastPage=int(paging.lastPage),
                           startPage=int(paging.startPage),
                           endPage=int(paging.endPage),
                           cntPage=int(paging.cntPage),
                           cntPerPage=int(paging.cntPerPage));

@app.route('/sensor/graph')
def realtimeSensorGraph():
    dates = sorted([date for date in rows.keys()])

    # 월(기본) 일 별 단위

    start = request.args.get("start", dates[0])   # 선택날짜(처음)
    if start == "":
        start = dates[0]
    end = request.args.get("end", dates[-1])   # 선택날짜(끝)
    if end == "":
        end = dates[-1]
    bno = request.args.get("bno")
    time = request.args.get("time", "day")

    if len(dates) != 0:
        minimum = dates[0]
        maximum = dates[-1]
    else:
        minimum = None
        maximum = None

    # 날짜선택을 하지 않은 경우(선택오류, 첫 그래프 페이지 이동 시)

    cols = sorted(columns)
    if 'BATT' in cols and 'TEMP' in cols:
        cols.remove('BATT')
        cols.remove('TEMP')
        cols.insert(0, 'BATT')
        cols.insert(1, 'TEMP')

    filter_dates = [date for date in dates if date >= start and date <= end]

    if time == "hour":
        div_dates = sorted(set(div[0] + ' ' + div[1].split(':')[0] for div in [date.split(" ") for date in filter_dates]))
    elif time == "day":
        div_dates = sorted(set(date.split(" ")[0] for date in filter_dates))
    else:
        div_dates = filter_dates

    filter_rows = []

    for col in cols:
        arr = []
        for div_date in div_dates:
            total = 0
            count = 0
            for date in filter_dates:
                if div_date in date:
                    count += 1
                    if col in rows[date]:
                        total += float(rows[date][col])
            arr.append(round(total / count, 2))
        filter_rows.append(arr)

    filter_dates = div_dates


    print("첫날 : ", dates[0])
    print("날짜 : ", rows.keys())
    return render_template("sensor-graph.html",
                           cols=cols,
                           filter_dates=filter_dates,
                           filter_rows=filter_rows,
                           minimum=minimum,
                           maximum=maximum,
                           bno=bno,
                           time=time,
                           start=start,
                           end=end)


# [표]에 있는 데이터를 다운로드폴더에 저장
@app.route('/downloadSensorFile', methods=['POST'])
def download_sensor_file():
    # AJAX에서 보낸 파일 받기
    data = request.get_json()

    downloadStart = data.get('download_start')
    downloadEnd = data.get('download_end')

    fileName = "SensorData(" + downloadStart + "~" + downloadEnd + ").csv"
    downloadEnd = pd.to_datetime(downloadEnd) + pd.DateOffset(days=1)  # 날짜데이터에 하루을 더함
    downloadEnd = downloadEnd.strftime('%Y-%m-%d')  # datetime -> String형태로 변환

    rowList = []

    cols = sorted(columns)
    if 'BATT' in cols and 'TEMP' in cols:
        cols.remove('BATT')
        cols.remove('TEMP')
        cols.insert(0, 'BATT')
        cols.insert(1, 'TEMP')
    cols.insert(0, 'DATE')


    dates = sorted(rows.keys())

    for date in dates:
        arr = [date]
        for col in cols[1:]:
            if rows[date].get(col) is not None:
                arr.append(rows[date][col])
            else:
                arr.append(0)
        rowList.append(arr)

    csv_data = pd.DataFrame(rowList, columns=cols)

    # 기간 지정
    csv_data['DATE'] = pd.to_datetime(csv_data['DATE'])
    start_time = pd.Timestamp(downloadStart)  # 선택날짜(처음) 시간 저장
    end_time = pd.Timestamp(downloadEnd)  # 선택날짜(처음) 시간 저장
    download_data =csv_data[(csv_data['DATE'] >= start_time) & (csv_data['DATE'] < end_time)]  # start ~ end까지의 날짜에 맞는 데이터 분류

    download_folder = os.path.expanduser("~") + "/Downloads"    # Downloads 폴더위치 저장
    filePath = os.path.join(download_folder, fileName)  # 다운로드 폴더 + 파일이름
    download_data.to_csv(filePath, index=False) # 해당 폴더에 csv파일 생성
    return "DOWNLOAD SUCCESS"

@app.route("/addData", methods=['POST'])
def addData():
    file = request.files['file']
    csv_path = 'C:/upload_csv/add/'
    file.save(os.path.join(csv_path, file.filename))
    data = pd.read_csv(csv_path+file.filename)

    colList = [col for col in data.columns if data.iloc[1][col] != 0]

    for col in colList[1:]:
        columns.add(col)
    for idx in data.index:
        date = HoursTenUnder(data.iloc[idx]['DATE'])
        for col in colList[1:]:
            if date not in rows:
                rows[date] = {}
            rows[date][col] = data.iloc[idx][col]

    return "ADD DATA SUCCESS"

@app.route("/delData", methods=['POST'])
def delData():
    global columns
    global rows

    columns = set()
    rows = {}
    columns = realtile_sensor_cols
    rows = realtile_sensor_rows

    return "DEL PLUS DATA"

if __name__ == '__main__':
    app.run(debug=True, host="192.168.0.55", port=5000) # host="자신의 IP주소"

cursor.close()
con.close()

# 오라클 연결
# 1. pip install cx_Oracle
