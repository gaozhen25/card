# -*- coding: utf-8 -*-
"""
抖音 / 小红书 外链卡片系统（独立版，本地直接运行）
技术栈: Python + Flask + SQLite（零外部依赖，无需 MySQL 服务）
核心能力: 卡片管理 / OG卡片生成 / 访问日志 / IP黑名单 / 过期与访问上限 / 后台登录
运行: python3 app.py  ->  http://127.0.0.1:8000
后台: http://127.0.0.1:8000/admin   默认账号 admin / 123456
"""
import os
import sqlite3
import time
import hashlib
from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 数据库路径：Render 部署时建议设置 DATABASE_PATH=/var/data/data.db 并挂载持久化磁盘
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'data.db'))
# 密钥：生产环境务必通过环境变量设置
SECRET_KEY = os.environ.get('SECRET_KEY', 'card_system_secret_ylb_change_me')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', '123456')  # 生产环境务必通过环境变量修改

app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.template_filter('fmt_time')
def fmt_time(ts):
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(ts)))
    except Exception:
        return ''

# ---------------- 数据库 ----------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS wailian_card (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL DEFAULT '',
        desc TEXT NOT NULL DEFAULT '',
        cover_img TEXT NOT NULL DEFAULT '',
        target_url TEXT NOT NULL DEFAULT '',
        max_visit INTEGER NOT NULL DEFAULT 0,
        expire_time INTEGER NOT NULL DEFAULT 0,
        status INTEGER NOT NULL DEFAULT 1,
        click_count INTEGER NOT NULL DEFAULT 0,
        enable_blackip INTEGER NOT NULL DEFAULT 0,
        create_time INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS wailian_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER NOT NULL DEFAULT 0,
        ip TEXT NOT NULL DEFAULT '',
        ua TEXT,
        is_spider INTEGER NOT NULL DEFAULT 0,
        create_time INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS wailian_blackip (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL UNIQUE,
        remark TEXT NOT NULL DEFAULT '',
        create_time INTEGER NOT NULL DEFAULT 0
    );
    """)
    db.commit()
    db.close()

# 模块加载时自动初始化数据库（确保 WSGI/gunicorn 启动时也能建表）
init_db()

# ---------------- 工具 ----------------
def is_spider_ua(ua):
    ua = (ua or '').lower()
    keywords = [
        'douyinspider', 'douyin', 'bytespider', 'tiktok',
        'xhs', 'xiaohongshu', 'jinabot',
        'twitterbot', 'facebookexternalhit', 'curl', 'python-requests', 'scrapy'
    ]
    for kw in keywords:
        if kw in ua:
            return True
    return False

def need_login(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get('admin'):
            return redirect(url_for('login'))
        return f(*a, **kw)
    return wrapper

# ---------------- 对外入口 ----------------
@app.route('/')
def index():
    cid = request.args.get('id', type=int)
    if not cid:
        return '参数缺失', 400
    db = get_db()
    row = db.execute("SELECT * FROM wailian_card WHERE id=?", (cid,)).fetchone()
    if not row or row['status'] != 1:
        return '卡片不存在或已关闭', 404
    now = int(time.time())
    if row['expire_time'] > 0 and now > row['expire_time']:
        return '链接已过期', 410
    if row['max_visit'] > 0 and row['click_count'] >= row['max_visit']:
        return '访问已达上限', 410

    ip = request.remote_addr or ''
    ua = request.headers.get('User-Agent', '')
    spider = 1 if is_spider_ua(ua) else 0

    if row['enable_blackip']:
        b = db.execute("SELECT id FROM wailian_blackip WHERE ip=?", (ip,)).fetchone()
        if b:
            return '访问被限制', 403

    db.execute("INSERT INTO wailian_log(card_id, ip, ua, is_spider, create_time) VALUES(?,?,?,?,?)",
               (cid, ip, ua, spider, now))
    db.commit()

    if spider:
        # 平台爬虫：返回 OG 元标签生成卡片预览
        return render_template('og.html', row=row)
    else:
        # 真实用户：计数 + 跳转目标
        db.execute("UPDATE wailian_card SET click_count=click_count+1 WHERE id=?", (cid,))
        db.commit()
        return redirect(row['target_url'])

# ---------------- 后台登录 ----------------
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    err = None
    if request.method == 'POST':
        u = (request.form.get('username') or '').strip()
        p = request.form.get('password') or ''
        if u == ADMIN_USER and hashlib.md5(p.encode()).hexdigest() == hashlib.md5(ADMIN_PASS.encode()).hexdigest():
            session['admin'] = True
            return redirect(url_for('admin_index'))
        err = '账号或密码错误'
    return render_template('login.html', err=err)

@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

# ---------------- 后台：卡片列表 ----------------
@app.route('/admin')
@need_login
def admin_index():
    db = get_db()
    page = max(1, request.args.get('page', 1, type=int))
    pagesize = 15
    offset = (page - 1) * pagesize
    total = db.execute("SELECT COUNT(*) c FROM wailian_card").fetchone()['c']
    list_ = db.execute("SELECT * FROM wailian_card ORDER BY id DESC LIMIT ? OFFSET ?",
                       (pagesize, offset)).fetchall()
    total_page = max(1, (total + pagesize - 1) // pagesize)
    return render_template('index.html', list_=list_, total=total, page=page,
                           total_page=total_page, site_url=request.host_url)

@app.route('/admin/del/<int:cid>')
@need_login
def admin_del(cid):
    db = get_db()
    db.execute("DELETE FROM wailian_card WHERE id=?", (cid,))
    db.execute("DELETE FROM wailian_log WHERE card_id=?", (cid,))
    db.commit()
    return redirect(url_for('admin_index'))

# ---------------- 后台：新增 / 编辑 ----------------
@app.route('/admin/edit', methods=['GET', 'POST'])
@app.route('/admin/edit/<int:cid>', methods=['GET', 'POST'])
@need_login
def admin_edit(cid=0):
    db = get_db()
    data = {'title': '', 'desc': '', 'cover_img': '', 'target_url': '',
            'max_visit': 0, 'expire_time': '', 'status': 1, 'enable_blackip': 0}
    if cid > 0:
        row = db.execute("SELECT * FROM wailian_card WHERE id=?", (cid,)).fetchone()
        if row:
            d = dict(row)
            d['expire_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(d['expire_time'])) if d['expire_time'] else ''
            data = d

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        desc = (request.form.get('desc') or '').strip()
        cover = (request.form.get('cover_img') or '').strip()
        target = (request.form.get('target_url') or '').strip()
        max_visit = request.form.get('max_visit', 0, type=int)
        exp_str = (request.form.get('expire_time') or '').strip()
        status = request.form.get('status', 1, type=int)
        enable_b = request.form.get('enable_blackip', 0, type=int)
        exp_ts = 0
        if exp_str:
            try:
                exp_ts = int(time.mktime(time.strptime(exp_str, '%Y-%m-%d %H:%M:%S')))
            except Exception:
                exp_ts = 0
        now = int(time.time())
        if cid > 0:
            db.execute("""UPDATE wailian_card SET title=?,desc=?,cover_img=?,target_url=?,
                          max_visit=?,expire_time=?,status=?,enable_blackip=? WHERE id=?""",
                       (title, desc, cover, target, max_visit, exp_ts, status, enable_b, cid))
        else:
            db.execute("""INSERT INTO wailian_card(title,desc,cover_img,target_url,max_visit,
                          expire_time,status,click_count,enable_blackip,create_time)
                          VALUES(?,?,?,?,?,?,?,0,?,?)""",
                       (title, desc, cover, target, max_visit, exp_ts, status, enable_b, now))
        db.commit()
        return redirect(url_for('admin_index'))
    return render_template('edit.html', data=data, cid=cid)

# ---------------- 后台：访问日志 ----------------
@app.route('/admin/log')
@need_login
def admin_log():
    db = get_db()
    card_id = request.args.get('card_id', 0, type=int)
    page = max(1, request.args.get('page', 1, type=int))
    pagesize = 20
    offset = (page - 1) * pagesize
    if card_id > 0:
        total = db.execute("SELECT COUNT(*) c FROM wailian_log WHERE card_id=?", (card_id,)).fetchone()['c']
        list_ = db.execute("SELECT * FROM wailian_log WHERE card_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                           (card_id, pagesize, offset)).fetchall()
    else:
        total = db.execute("SELECT COUNT(*) c FROM wailian_log").fetchone()['c']
        list_ = db.execute("SELECT * FROM wailian_log ORDER BY id DESC LIMIT ? OFFSET ?",
                           (pagesize, offset)).fetchall()
    total_page = max(1, (total + pagesize - 1) // pagesize)
    return render_template('log.html', list_=list_, total=total, page=page,
                           total_page=total_page, card_id=card_id)

# ---------------- 后台：IP 黑名单 ----------------
@app.route('/admin/blackip', methods=['GET', 'POST'])
@need_login
def admin_blackip():
    db = get_db()
    if request.method == 'POST':
        ip = (request.form.get('ip') or '').strip()
        remark = (request.form.get('remark') or '').strip()
        if ip:
            try:
                db.execute("INSERT OR IGNORE INTO wailian_blackip(ip,remark,create_time) VALUES(?,?,?)",
                           (ip, remark, int(time.time())))
                db.commit()
            except sqlite3.IntegrityError:
                pass
        return redirect(url_for('admin_blackip'))
    list_ = db.execute("SELECT * FROM wailian_blackip ORDER BY id DESC").fetchall()
    return render_template('blackip.html', list_=list_)

@app.route('/admin/blackip/del/<int:bid>')
@need_login
def admin_blackip_del(bid):
    db = get_db()
    db.execute("DELETE FROM wailian_blackip WHERE id=?", (bid,))
    db.commit()
    return redirect(url_for('admin_blackip'))

if __name__ == '__main__':
    # 确保数据库目录存在（Render 挂载持久化磁盘时需要）
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    init_db()
    port = int(os.environ.get('PORT', 8000))
    print("=" * 50)
    print("抖音/小红书外链卡片系统 已启动")
    print(f"监听端口: {port}")
    print(f"数据库: {DB_PATH}")
    print("后台地址: /admin  默认账号 admin / 123456")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
