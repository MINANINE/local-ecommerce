from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re

auth_bp = Blueprint('auth', __name__)
DB_FILE = "ecommerce.db"

# 邮箱验证正则
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form.get('full_name', '')
        
        # 验证输入
        errors = []
        
        if len(username) < 3:
            errors.append('用户名至少3个字符')
        
        if not re.match(EMAIL_REGEX, email):
            errors.append('邮箱格式不正确')
        
        if len(password) < 6:
            errors.append('密码至少6个字符')
        
        if password != confirm_password:
            errors.append('两次输入的密码不一致')
        
        # 检查用户名和邮箱是否已存在
        conn = get_db_connection()
        existing_user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?', 
            (username, email)
        ).fetchone()
        
        if existing_user:
            if existing_user['username'] == username:
                errors.append('用户名已存在')
            if existing_user['email'] == email:
                errors.append('邮箱已注册')
        
        if errors:
            conn.close()
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')
        
        # 创建用户
        password_hash = generate_password_hash(password)
        conn.execute(
            'INSERT INTO users (username, email, password_hash, full_name) VALUES (?, ?, ?, ?)',
            (username, email, password_hash, full_name)
        )
        conn.commit()
        
        # 获取用户ID并存入session
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        
        conn.close()
        
        flash('注册成功！欢迎 ' + username, 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember', False)
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?', 
            (username, username)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            
            if remember:
                session.permanent = True
            
            flash('登录成功！', 'success')
            
            # 记录登录日志
            log_user_action(user['id'], 'login', request.remote_addr, request.user_agent.string)
            
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        # 记录登出日志
        log_user_action(session['user_id'], 'logout', request.remote_addr, request.user_agent.string)
        
        session.clear()
        flash('已成功登出', 'success')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # 获取用户订单
    orders = conn.execute('''
        SELECT o.*, COUNT(oi.id) as item_count 
        FROM orders o 
        LEFT JOIN order_items oi ON o.id = oi.order_id 
        WHERE o.user_id = ? 
        GROUP BY o.id 
        ORDER BY o.created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('profile.html', user=user, orders=orders)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        
        # 检查邮箱是否被其他用户使用
        existing = conn.execute(
            'SELECT id FROM users WHERE email = ? AND id != ?', 
            (email, session['user_id'])
        ).fetchone()
        
        if existing:
            flash('该邮箱已被其他用户使用', 'danger')
            return render_template('edit_profile.html', user=conn.execute(
                'SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone())
        
        conn.execute('''
            UPDATE users 
            SET full_name = ?, email = ?, phone = ?, address = ? 
            WHERE id = ?
        ''', (full_name, email, phone, address, session['user_id']))
        conn.commit()
        
        flash('个人信息更新成功', 'success')
        return redirect(url_for('auth.profile'))
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('edit_profile.html', user=user)

def log_user_action(user_id, action, ip_address, user_agent, product_id=None, details=None):
    """记录用户行为日志"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO user_logs (user_id, ip_address, user_agent, action, product_id, details)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, ip_address, user_agent, action, product_id, details))
    conn.commit()
    conn.close()
