import os
import base64
import json
import sqlite3
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, date, timedelta
from functools import wraps

import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# ===================== 配置 =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db1', 'attendance.db')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

MODEL_DIR = os.path.join(BASE_DIR, 'face_recognition_score2026', 'Algorithm')
MODEL_PATH = os.path.join(MODEL_DIR, 'face_recognizer_model.xml')
LABEL_MAPPING_PATH = os.path.join(MODEL_DIR, 'label_mapping.json')

app = Flask(__name__)
app.secret_key = 'face_attendance_system_2026_secret'

# ===================== 日志系统 =====================
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = logging.Formatter(
    '%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 主应用日志 — 每日轮转,保留30天
app_logger = logging.getLogger('FaceAttendance')
app_logger.setLevel(logging.INFO)

file_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, 'app.log'),
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8'
)
file_handler.setFormatter(LOG_FORMAT)
app_logger.addHandler(file_handler)

# 签到专用日志 — 单独文件,记录每次签到事件
checkin_logger = logging.getLogger('Checkin')
checkin_logger.setLevel(logging.INFO)
checkin_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, 'checkin.log'),
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8'
)
checkin_handler.setFormatter(LOG_FORMAT)
checkin_logger.addHandler(checkin_handler)

# 错误日志 — 记录所有异常
error_logger = logging.getLogger('Error')
error_logger.setLevel(logging.WARNING)
error_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, 'error.log'),
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8'
)
error_handler.setFormatter(LOG_FORMAT)
error_logger.addHandler(error_handler)

# Debug 模式下 Flask 会启动 reloader,reloader 子进程才是真正的服务器
_is_server = os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or \
             'WERKZEUG_RUN_MAIN' not in os.environ

# 控制台输出 — 仅子进程输出,避免 reloader 父进程重复
console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMAT)
if _is_server:
    app_logger.addHandler(console_handler)

# Flask 内置 access log — 文件始终写,控制台仅 server 输出
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.handlers = []
werkzeug_logger.addHandler(file_handler)
if _is_server:
    werkzeug_logger.addHandler(console_handler)

# ===================== 人脸识别模型初始化 =====================
face_recognizer = None
label_mapping = {}
face_detector = None
profile_detector = None
model_loaded = False

def load_face_model():
    global face_recognizer, label_mapping, face_detector, profile_detector, model_loaded
    try:
        face_recognizer = cv2.face.LBPHFaceRecognizer_create()
        face_recognizer.read(MODEL_PATH)
        with open(LABEL_MAPPING_PATH, encoding='utf-8') as f:
            label_mapping = json.load(f)['id_to_name']
        face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')
        profile_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_profileface.xml')
        model_loaded = True
        app_logger.info('人脸识别模型加载成功')
    except Exception as e:
        app_logger.warning(f'人脸识别模型加载失败: {e}')
        error_logger.warning(f'模型加载失败: {e}')
        model_loaded = False

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.text_factory = lambda b: b.decode('utf-8', errors='replace')
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE student ADD COLUMN password TEXT NOT NULL DEFAULT '123456'")
    except sqlite3.OperationalError:
        pass
    cur.execute('''
        CREATE TABLE IF NOT EXISTS checkin_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

if _is_server:
    load_face_model()
    init_db()

# ===================== 登录装饰器 =====================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

# ===================== 人脸识别函数 =====================
def recognize_face(image_base64):
    """对 base64 图片进行人脸识别，返回 (predicted_student_id, confidence) 或 (None, None)"""
    if not model_loaded:
        return None, None
    try:
        img_data = base64.b64decode(image_base64.split(',')[1]
                                    if ',' in image_base64 else image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        gray = cv2.equalizeHist(gray)
        faces = face_detector.detectMultiScale(
            gray, scaleFactor=1.03, minNeighbors=5, minSize=(40, 40))
        if len(faces) == 0:
            faces = profile_detector.detectMultiScale(
                gray, scaleFactor=1.03, minNeighbors=5, minSize=(40, 40))
        if len(faces) == 0:
            return None, None
        x, y, w, h = faces[0]
        y1 = max(0, y - int(0.15 * h))
        y2 = min(gray.shape[0], y + h + int(0.15 * h))
        x1 = max(0, x - int(0.15 * w))
        x2 = min(gray.shape[1], x + w + int(0.15 * w))
        face_roi = gray[y1:y2, x1:x2]
        face_roi = cv2.resize(face_roi, (92, 112))
        label, confidence = face_recognizer.predict(face_roi)
        predicted_id = label_mapping.get(str(label))
        return predicted_id, confidence
    except Exception as e:
        error_logger.error(f'人脸识别异常: {e}')
        return None, None

# ===================== 页面路由 =====================
@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/student')
@login_required
def student_page():
    if session.get('role') != 'student':
        return redirect(url_for('login_page'))
    return render_template('student.html')

@app.route('/teacher')
@login_required
def teacher_page():
    if session.get('role') != 'teacher':
        return redirect(url_for('login_page'))
    return render_template('teacher.html')

# ===================== API: 登录 =====================
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    role = data.get('role')
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': '请输入账号和密码'})

    conn = get_db()
    cur = conn.cursor()

    if role == 'student':
        cur.execute(
            'SELECT id, name, class, password FROM student WHERE id=?',
            (username,))
        row = cur.fetchone()
        conn.close()
        if not row:
            app_logger.warning(f'学生登录失败: 学号 {username} 不存在')
            return jsonify({'success': False, 'message': '学号不存在'})
        if row['password'] != password:
            app_logger.warning(f'学生登录失败: {username} {row["name"]} 密码错误')
            return jsonify({'success': False, 'message': '密码错误'})
        session['user_id'] = row['id']
        session['user_name'] = row['name']
        session['user_class'] = row['class']
        session['role'] = 'student'
        app_logger.info(f'学生登录: {row["id"]} {row["name"]} ({row["class"]}班)')
        return jsonify({'success': True, 'redirect': '/student'})

    elif role == 'teacher':
        cur.execute(
            'SELECT username, password FROM admin_user WHERE username=?',
            (username,))
        row = cur.fetchone()
        conn.close()
        if not row:
            app_logger.warning(f'教师登录失败: 账号 {username} 不存在')
            return jsonify({'success': False, 'message': '教师账号不存在'})
        if row['password'] != password:
            app_logger.warning(f'教师登录失败: {username} 密码错误')
            return jsonify({'success': False, 'message': '密码错误'})
        session['user_id'] = row['username']
        session['user_name'] = row['username']
        session['role'] = 'teacher'
        app_logger.info(f'教师登录: {username}')
        return jsonify({'success': True, 'redirect': '/teacher'})

    conn.close()
    return jsonify({'success': False, 'message': '无效的角色'})

# ===================== API: 登出 =====================
@app.route('/api/logout')
def api_logout():
    session.clear()
    return redirect(url_for('login_page'))

# ===================== API: 签到状态 =====================
@app.route('/api/checkin-status')
@login_required
def api_checkin_status():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT id, is_active FROM checkin_session ORDER BY id DESC LIMIT 1')
    row = cur.fetchone()
    conn.close()
    active = row['is_active'] == 1 if row else False
    session_id = row['id'] if row else 0
    return jsonify({'active': active, 'session_id': session_id})

# ===================== API: 人脸签到 =====================
@app.route('/api/checkin', methods=['POST'])
@login_required
def api_checkin():
    if session.get('role') != 'student':
        return jsonify({'success': False, 'message': '仅学生可签到'})

    conn = get_db()
    cur = conn.cursor()
    # 获取当前会话信息
    cur.execute(
        'SELECT id, start_time, is_active FROM checkin_session ORDER BY id DESC LIMIT 1')
    session_row = cur.fetchone()
    if not session_row or session_row['is_active'] != 1:
        conn.close()
        return jsonify({'success': False, 'message': '教师尚未开启签到'})

    student_id = session['user_id']
    today_str = date.today().strftime('%Y-%m-%d')
    now_str = datetime.now().strftime('%H:%M:%S')
    session_start = session_row['start_time']

    # 检查是否已在当前会话签到
    cur.execute(
        'SELECT id FROM face_recognition_record '
        'WHERE student_id=? AND record_date=? AND recognition_time >= ?',
        (student_id, today_str, session_start))
    if cur.fetchone():
        conn.close()
        checkin_logger.info(f'本会话已签到: {student_id} {session["user_name"]}')
        return jsonify({'success': False, 'message': '本会话已签到，无需重复签到'})

    # 人脸识别
    image_data = request.get_json().get('image', '')
    predicted_id, confidence = recognize_face(image_data)

    if predicted_id is None:
        conn.close()
        checkin_logger.warning(f'签到失败-未检测到人脸: {student_id} {session["user_name"]}')
        return jsonify({'success': False, 'message': '未检测到人脸，请对准摄像头'})

    if predicted_id != student_id:
        conn.close()
        checkin_logger.warning(
            f'签到失败-身份不匹配: {student_id} {session["user_name"]} 识别为 {predicted_id}')
        return jsonify({'success': False, 'message': '人脸验证失败，请确认是本人'})

    if confidence is not None and confidence >= 125:
        conn.close()
        checkin_logger.warning(
            f'签到失败-置信度不足: {student_id} {session["user_name"]} confidence={confidence:.0f}')
        return jsonify({'success': False, 'message': '人脸匹配度不足，请调整光线和角度'})

    # 签到成功，始终插入新记录(支持一天多次签到，保留全部历史)
    cur.execute(
        'INSERT INTO face_recognition_record '
        '(student_id, record_date, recognition_time, is_signed) '
        'VALUES (?, ?, ?, 1)',
        (student_id, today_str, now_str))
    conn.commit()
    conn.close()

    checkin_logger.info(
        f'签到成功: {student_id} {session["user_name"]} 时间={now_str} confidence={confidence:.0f if confidence else "N/A"}')
    app_logger.info(f'签到成功: {student_id} {session["user_name"]} {now_str}')

    return jsonify({
        'success': True,
        'message': f'签到成功！{session["user_name"]} {now_str}',
        'time': now_str
    })

# ===================== API: 学生今日签到状态 =====================
@app.route('/api/student/today-status')
@login_required
def api_student_today_status():
    if session.get('role') != 'student':
        return jsonify({'signed': False, 'time': ''})
    student_id = session['user_id']
    today_str = date.today().strftime('%Y-%m-%d')
    conn = get_db()
    cur = conn.cursor()
    # 获取当前活跃会话开始时间
    cur.execute(
        'SELECT start_time FROM checkin_session WHERE is_active=1 ORDER BY id DESC LIMIT 1')
    session_row = cur.fetchone()
    if session_row:
        session_start = session_row['start_time']
        cur.execute(
            'SELECT recognition_time FROM face_recognition_record '
            'WHERE student_id=? AND record_date=? AND recognition_time >= ? '
            'ORDER BY id DESC LIMIT 1',
            (student_id, today_str, session_start))
        row = cur.fetchone()
        conn.close()
        if row:
            return jsonify({'signed': True, 'time': row['recognition_time'] or ''})
    conn.close()
    return jsonify({'signed': False, 'time': ''})

# ===================== API: 学生查看自己的签到记录 =====================
@app.route('/api/student/records')
@login_required
def api_student_records():
    if session.get('role') != 'student':
        return jsonify([])
    student_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT record_date, recognition_time, is_signed '
        'FROM face_recognition_record '
        'WHERE student_id=? ORDER BY record_date DESC LIMIT 30',
        (student_id,))
    rows = cur.fetchall()
    conn.close()
    records = []
    for r in rows:
        records.append({
            'date': r['record_date'],
            'time': r['recognition_time'] or '',
            'status': '已签到' if r['is_signed'] else '未签到'
        })
    return jsonify(records)

# ===================== API: 教师开关签到 =====================
@app.route('/api/teacher/toggle-checkin', methods=['POST'])
@login_required
def api_toggle_checkin():
    if session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '无权限'})

    data = request.get_json()
    action = data.get('action')  # 'start' or 'stop'
    today_str = date.today().strftime('%Y-%m-%d')
    now_str = datetime.now().strftime('%H:%M:%S')

    conn = get_db()
    cur = conn.cursor()

    if action == 'start':
        # 先结束之前的活跃会话
        cur.execute(
            "UPDATE checkin_session SET is_active=0, end_time=? WHERE is_active=1",
            (now_str,))
        # 创建新会话
        cur.execute(
            'INSERT INTO checkin_session (session_date, start_time, is_active) VALUES (?, ?, 1)',
            (today_str, now_str))
        # 为所有学生补全今日记录(仅未签到状态用于初始显示)
        cur.execute('SELECT id FROM student')
        all_ids = [row['id'] for row in cur.fetchall()]
        cur.execute(
            'SELECT student_id FROM face_recognition_record WHERE record_date=?',
            (today_str,))
        existing = set(row['student_id'] for row in cur.fetchall())
        for sid in all_ids:
            if sid not in existing:
                cur.execute(
                    'INSERT INTO face_recognition_record '
                    '(student_id, record_date, recognition_time, is_signed) '
                    'VALUES (?, ?, NULL, 0)',
                    (sid, today_str))
        conn.commit()
        conn.close()
        app_logger.info(f'教师 {session["user_name"]} 开启签到 [{today_str} {now_str}]')
        return jsonify({'success': True, 'message': '签到已开启', 'active': True})

    elif action == 'stop':
        cur.execute(
            "UPDATE checkin_session SET is_active=0, end_time=? WHERE is_active=1",
            (now_str,))
        conn.commit()
        conn.close()
        app_logger.info(f'教师 {session["user_name"]} 结束签到 [{today_str} {now_str}]')
        return jsonify({'success': True, 'message': '签到已结束', 'active': False})

    conn.close()
    return jsonify({'success': False, 'message': '无效操作'})

# ===================== API: 教师获取学生列表 =====================
@app.route('/api/teacher/students')
@login_required
def api_teacher_students():
    if session.get('role') != 'teacher':
        return jsonify([])
    class_filter = request.args.get('class', '')
    conn = get_db()
    cur = conn.cursor()
    if class_filter and class_filter != '全部':
        cur.execute('SELECT id, name, class FROM student WHERE class=? ORDER BY id',
                    (class_filter,))
    else:
        cur.execute('SELECT id, name, class FROM student ORDER BY id')
    rows = cur.fetchall()
    conn.close()
    return jsonify([{'id': r['id'], 'name': r['name'], 'class': r['class']}
                    for r in rows])

# ===================== API: 教师获取班级列表 =====================
@app.route('/api/teacher/classes')
@login_required
def api_teacher_classes():
    if session.get('role') != 'teacher':
        return jsonify([])
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT class FROM student ORDER BY class')
    rows = cur.fetchall()
    conn.close()
    return jsonify([r['class'] for r in rows])

# ===================== API: 教师获取签到记录 =====================
@app.route('/api/teacher/records')
@login_required
def api_teacher_records():
    if session.get('role') != 'teacher':
        return jsonify({'records': [], 'stats': {}})
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    class_filter = request.args.get('class', '')

    conn = get_db()
    cur = conn.cursor()

    # 查询每个学生当日最新的一条签到记录
    if class_filter and class_filter != '全部':
        cur.execute('''
            SELECT s.id, s.name, s.class, r.is_signed, r.recognition_time
            FROM student s
            LEFT JOIN (
                SELECT student_id, is_signed, recognition_time
                FROM face_recognition_record
                WHERE record_date=? AND id IN (
                    SELECT MAX(id) FROM face_recognition_record
                    WHERE record_date=? GROUP BY student_id
                )
            ) r ON s.id = r.student_id
            WHERE s.class=?
            ORDER BY COALESCE(r.is_signed, 0) ASC, s.id ASC
        ''', (date_str, date_str, class_filter))
    else:
        cur.execute('''
            SELECT s.id, s.name, s.class, r.is_signed, r.recognition_time
            FROM student s
            LEFT JOIN (
                SELECT student_id, is_signed, recognition_time
                FROM face_recognition_record
                WHERE record_date=? AND id IN (
                    SELECT MAX(id) FROM face_recognition_record
                    WHERE record_date=? GROUP BY student_id
                )
            ) r ON s.id = r.student_id
            ORDER BY COALESCE(r.is_signed, 0) ASC, s.id ASC
        ''', (date_str, date_str))

    rows = cur.fetchall()
    conn.close()

    records = []
    signed = 0
    for r in rows:
        records.append({
            'id': r['id'],
            'name': r['name'],
            'class': r['class'],
            'status': '已签到' if r['is_signed'] else '未签到',
            'time': r['recognition_time'] or ''
        })
        if r['is_signed']:
            signed += 1

    total = len(records)
    return jsonify({
        'records': records,
        'stats': {
            'signed': signed,
            'total': total,
            'unsigned': total - signed,
            'rate': round(signed / total * 100, 1) if total > 0 else 0
        }
    })

# ===================== API: 教师获取图表数据 =====================
@app.route('/api/teacher/chart')
@login_required
def api_teacher_chart():
    if session.get('role') != 'teacher':
        return jsonify({})
    class_filter = request.args.get('class', '')
    today = date.today()
    conn = get_db()
    cur = conn.cursor()
    dates = []
    rates = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        if class_filter and class_filter != '全部':
            cur.execute('''
                SELECT COUNT(*), SUM(r.is_signed)
                FROM face_recognition_record r
                JOIN student s ON r.student_id = s.id
                WHERE r.record_date=? AND s.class=?
            ''', (d, class_filter))
        else:
            cur.execute('''
                SELECT COUNT(*), SUM(is_signed)
                FROM face_recognition_record WHERE record_date=?
            ''', (d,))
        total, signed = cur.fetchone()
        rate = round(signed / total * 100, 1) if total and total > 0 else 0
        dates.append(d[5:])
        rates.append(rate)
    conn.close()
    return jsonify({'dates': dates, 'rates': rates})

# ===================== API: 教师修改学生信息 =====================
@app.route('/api/teacher/edit-student', methods=['POST'])
@login_required
def api_edit_student():
    if session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '无权限'})
    data = request.get_json()
    old_id = data.get('old_id')
    new_id = data.get('id')
    name = data.get('name')
    cls = data.get('class')
    if not all([old_id, new_id, name, cls]):
        return jsonify({'success': False, 'message': '信息不完整'})
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute('UPDATE student SET id=?, name=?, class=? WHERE id=?',
                    (new_id, name, cls, old_id))
        conn.commit()
        conn.close()
        app_logger.info(f'教师 {session["user_name"]} 修改学生: {old_id} -> {new_id} {name} ({cls}班)')
        return jsonify({'success': True, 'message': '修改成功'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'message': '学号已存在'})

# ===================== API: 教师修改签到记录 =====================
@app.route('/api/teacher/edit-record', methods=['POST'])
@login_required
def api_edit_record():
    if session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '无权限'})
    data = request.get_json()
    student_id = data.get('student_id')
    date_str = data.get('date')
    is_signed = 1 if data.get('status') == '已签到' else 0
    rec_time = data.get('time') if is_signed else None
    if is_signed and not rec_time:
        return jsonify({'success': False, 'message': '签到时间不能为空'})
    conn = get_db()
    cur = conn.cursor()
    # 编辑该学生当日最新一条记录
    cur.execute(
        'UPDATE face_recognition_record SET is_signed=?, recognition_time=? '
        'WHERE id=(SELECT MAX(id) FROM face_recognition_record '
        'WHERE student_id=? AND record_date=?)',
        (is_signed, rec_time, student_id, date_str))
    conn.commit()
    conn.close()
    status_text = '已签到' if is_signed else '未签到'
    app_logger.info(
        f'教师 {session["user_name"]} 编辑签到: {student_id} {date_str} -> {status_text} {rec_time or ""}')
    return jsonify({'success': True, 'message': '签到记录已更新'})

# ===================== API: 获取当前用户信息 =====================
@app.route('/api/user-info')
@login_required
def api_user_info():
    return jsonify({
        'id': session.get('user_id'),
        'name': session.get('user_name'),
        'role': session.get('role'),
        'class': session.get('user_class', '')
    })

# ===================== 启动 =====================
if __name__ == '__main__':
    app_logger.info('=' * 50)
    app_logger.info('人脸识别签到系统 启动')
    app_logger.info(f'访问地址: http://localhost:5000')
    app_logger.info(f'日志目录: {LOG_DIR}')
    app_logger.info('=' * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
