from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
DB_FILE = "ecommerce.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def admin_required(f):
    """管理员权限装饰器"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('需要管理员权限', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def dashboard():
    conn = get_db_connection()
    
    # 基础统计
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    stats = {
        'total_users': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'total_products': conn.execute('SELECT COUNT(*) FROM products').fetchone()[0],
        'total_orders': conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
        'today_orders': conn.execute('SELECT COUNT(*) FROM orders WHERE DATE(created_at) = ?', (today,)).fetchone()[0],
        'weekly_sales': conn.execute('SELECT SUM(total_amount) FROM orders WHERE DATE(created_at) >= ?', (week_ago,)).fetchone()[0] or 0,
        'pending_orders': conn.execute('SELECT COUNT(*) FROM orders WHERE status = ?', ('pending',)).fetchone()[0]
    }
    
    # 最近订单
    recent_orders = conn.execute('''
        SELECT o.*, u.username 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        ORDER BY o.created_at DESC 
        LIMIT 10
    ''').fetchall()
    
    # 销售趋势（最近7天）
    sales_trend = conn.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as order_count, SUM(total_amount) as total_sales
        FROM orders 
        WHERE DATE(created_at) >= ? 
        GROUP BY DATE(created_at) 
        ORDER BY date
    ''', (week_ago,)).fetchall()
    
    # 热门商品
    popular_products = conn.execute('''
        SELECT p.name, SUM(oi.quantity) as total_sold, p.stock
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.id
        ORDER BY total_sold DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_orders=recent_orders,
                         sales_trend=sales_trend,
                         popular_products=popular_products)

@admin_bp.route('/products')
@admin_required
def manage_products():
    conn = get_db_connection()
    
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    query += ' ORDER BY created_at DESC'
    
    products = conn.execute(query, params).fetchall()
    categories = conn.execute('SELECT DISTINCT category FROM products WHERE category IS NOT NULL').fetchall()
    
    conn.close()
    
    return render_template('admin/products.html', products=products, categories=categories)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        category = request.form.get('category', '')
        image_url = request.form.get('image_url', '')
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO products (name, price, description, stock, category, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, price, description, stock, category, image_url))
        conn.commit()
        conn.close()
        
        flash('商品添加成功', 'success')
        return redirect(url_for('admin.manage_products'))
    
    return render_template('admin/add_product.html')

@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        category = request.form.get('category', '')
        image_url = request.form.get('image_url', '')
        is_active = 1 if request.form.get('is_active') else 0
        
        conn.execute('''
            UPDATE products 
            SET name = ?, price = ?, description = ?, stock = ?, 
                category = ?, image_url = ?, is_active = ?
            WHERE id = ?
        ''', (name, price, description, stock, category, image_url, is_active, product_id))
        conn.commit()
        conn.close()
        
        flash('商品更新成功', 'success')
        return redirect(url_for('admin.manage_products'))
    
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    
    if not product:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin.manage_products'))
    
    return render_template('admin/edit_product.html', product=product)

@admin_bp.route('/products/delete/<int:product_id>')
@admin_required
def delete_product(product_id):
    conn = get_db_connection()
    
    # 检查是否有订单关联
    order_count = conn.execute('SELECT COUNT(*) FROM order_items WHERE product_id = ?', (product_id,)).fetchone()[0]
    
    if order_count > 0:
        # 如果有订单，只标记为下架
        conn.execute('UPDATE products SET is_active = 0 WHERE id = ?', (product_id,))
        flash('商品已下架（有订单关联）', 'warning')
    else:
        # 没有订单，可以删除
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        flash('商品删除成功', 'success')
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/orders')
@admin_required
def manage_orders():
    conn = get_db_connection()
    
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = '''
        SELECT o.*, u.username, u.email 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        WHERE 1=1
    '''
    params = []
    
    if status_filter:
        query += ' AND o.status = ?'
        params.append(status_filter)
    
    if search:
        query += ' AND (o.order_number LIKE ? OR u.username LIKE ? OR u.email LIKE ?)'
        search_term = f'%{search}%'
        params.extend([search_term, search_term, search_term])
    
    query += ' ORDER BY o.created_at DESC'
    
    orders = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('admin/orders.html', orders=orders)

@admin_bp.route('/orders/update_status/<int:order_id>', methods=['POST'])
@admin_required
def update_order_status(order_id):
    new_status = request.form['status']
    
    conn = get_db_connection()
    
    # 获取当前状态
    current_order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not current_order:
        flash('订单不存在', 'danger')
        return redirect(url_for('admin.manage_orders'))
    
    # 更新状态
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    
    # 记录状态变更
    from auth import log_user_action
    log_user_action(current_order['user_id'], 'order_status_change', 
                   request.remote_addr, request.user_agent.string,
                   None, f"订单 {current_order['order_number']}: {current_order['status']} -> {new_status}")
    
    conn.commit()
    conn.close()
    
    flash('订单状态已更新', 'success')
    return redirect(url_for('admin.manage_orders'))

@admin_bp.route('/users')
@admin_required
def manage_users():
    conn = get_db_connection()
    
    search = request.args.get('search', '')
    
    query = 'SELECT * FROM users WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (username LIKE ? OR email LIKE ? OR full_name LIKE ?)'
        search_term = f'%{search}%'
        params.extend([search_term, search_term, search_term])
    
    query += ' ORDER BY created_at DESC'
    
    users = conn.execute(query, params).fetchall()
    
    # 获取用户统计数据
    for user in users:
        order_stats = conn.execute('''
            SELECT COUNT(*) as order_count, SUM(total_amount) as total_spent
            FROM orders 
            WHERE user_id = ?
        ''', (user['id'],)).fetchone()
        
        user['order_count'] = order_stats['order_count'] or 0
        user['total_spent'] = order_stats['total_spent'] or 0
    
    conn.close()
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/analytics')
@admin_required
def analytics():
    conn = get_db_connection()
    
    # 时间范围
    time_range = request.args.get('range', 'week')  # day, week, month, year
    
    if time_range == 'day':
        start_date = datetime.now() - timedelta(days=1)
    elif time_range == 'week':
        start_date = datetime.now() - timedelta(days=7)
    elif time_range == 'month':
        start_date = datetime.now() - timedelta(days=30)
    else:  # year
        start_date = datetime.now() - timedelta(days=365)
    
    # 销售数据
    sales_data = conn.execute('''
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as order_count,
            SUM(total_amount) as total_sales,
            AVG(total_amount) as avg_order_value
        FROM orders 
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (start_date,)).fetchall()
    
    # 用户增长
    user_growth = conn.execute('''
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as new_users
        FROM users 
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (start_date,)).fetchall()
    
    # 热门分类
    top_categories = conn.execute('''
        SELECT 
            p.category,
            COUNT(DISTINCT o.id) as order_count,
            SUM(oi.quantity) as total_quantity,
            SUM(oi.quantity * oi.price) as total_sales
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.created_at >= ? AND p.category IS NOT NULL
        GROUP BY p.category
        ORDER BY total_sales DESC
        LIMIT 10
    ''', (start_date,)).fetchall()
    
    # 用户行为统计
    user_actions = conn.execute('''
        SELECT 
            action,
            COUNT(*) as action_count,
            COUNT(DISTINCT user_id) as unique_users
        FROM user_logs 
        WHERE created_at >= ?
        GROUP BY action
        ORDER BY action_count DESC
    ''', (start_date,)).fetchall()
    
    conn.close()
    
    return render_template('admin/analytics.html',
                         sales_data=sales_data,
                         user_growth=user_growth,
                         top_categories=top_categories,
                         user_actions=user_actions,
                         time_range=time_range)

@admin_bp.route('/logs')
@admin_required
def view_logs():
    conn = get_db_connection()
    
    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    
    # 获取日志
    logs = conn.execute('''
        SELECT l.*, u.username 
        FROM user_logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset)).fetchall()
    
    # 获取总数
    total = conn.execute('SELECT COUNT(*) FROM user_logs').fetchone()[0]
    total_pages = (total + per_page - 1) // per_page
    
    conn.close()
    
    return render_template('admin/logs.html', logs=logs, page=page, total_pages=total_pages)
