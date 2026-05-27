from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import time
import json
import random
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "simple_key_123"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "ecommerce.db")


def set_flash(msg, msg_type='success'):
    """在 session 中设置一次性提示消息。"""
    session['_flash'] = {'msg': msg, 'type': msg_type}


@app.context_processor
def inject_flash():
    """将 flash 消息注入所有模板，读取后立即清除。"""
    flash_msg = session.pop('_flash', None)
    return {'flash': flash_msg}

def require_role(*roles):
    """检查当前登录用户是否拥有指定角色之一。"""
    if 'user_id' not in session:
        return False
    return session.get('role') in roles


# 初始化数据库（仅在新库时插入测试数据，CREATE TABLE IF NOT EXISTS 不覆盖已有数据）
def init_db():
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 创建商品表
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  price REAL NOT NULL,
                  description TEXT,
                  stock INTEGER NOT NULL DEFAULT 0,
                  category TEXT)''')
    
    # 创建用户表，role 字段区分角色: customer=普通用户, sales=销售人员, admin=管理者
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  email TEXT,
                  is_admin INTEGER DEFAULT 0,
                  role TEXT DEFAULT 'customer')''')
    
    # 创建订单表
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  product_id INTEGER NOT NULL,
                  product_name TEXT NOT NULL,
                  product_price REAL NOT NULL,
                  quantity INTEGER NOT NULL,
                  total_price REAL NOT NULL,
                  status TEXT DEFAULT '未发货',
                  order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  FOREIGN KEY (product_id) REFERENCES products (id))''')
    
    # 创建用户行为表
    c.execute('''CREATE TABLE IF NOT EXISTS user_behavior
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  behavior_type TEXT NOT NULL,
                  product_id INTEGER,
                  category TEXT,
                  stay_duration INTEGER DEFAULT 0,
                  ip_address TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_behavior_user ON user_behavior(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_behavior_time ON user_behavior(created_at)')
    
    # 插入测试数据
    products = [
        ("小米14 手机", 4299.0, "骁龙8 Gen3，6.36英寸直屏", 50, "手机"),
        ("AirPods Pro 2", 2499.0, "主动降噪，无线充电", 100, "耳机"),
        ("联想拯救者", 9999.0, "i9处理器，RTX 4060显卡", 30, "电脑"),
        ("华为平板", 3499.0, "12.6英寸OLED全面屏", 40, "平板"),
        ("索尼PS5", 3899.0, "光驱版，支持4K游戏", 20, "游戏"),
        ("戴尔显示器", 3999.0, "27英寸4K设计师显示器", 25, "显示器"),
        ("iPhone 15", 5999.0, "A16芯片，4800万像素双摄", 80, "手机"),
        ("三星Galaxy S24", 6999.0, "骁龙8 Gen3，AI影像增强", 65, "手机"),
        ("一加12", 4299.0, "2K东方屏，哈苏影像系统", 120, "手机"),
        ("荣耀Magic6", 4699.0, "青海湖电池，鹰眼相机", 90, "手机"),
        ("vivo X100", 3999.0, "天玑9300，蔡司镜头", 110, "手机"),
        ("OPPO Find X7", 4499.0, "双潜望长焦，哈苏影像", 75, "手机"),
        ("红米K70", 2999.0, "骁龙8 Gen2，2K直屏", 200, "手机"),
        ("华为Mate 60", 6499.0, "卫星通话，昆仑玻璃", 50, "手机"),
        ("魅族21", 3699.0, "骁龙8 Gen3，白色面板", 60, "手机"),
        ("iQOO 12", 3999.0, "自研电竞芯片Q1", 85, "手机"),
        ("MacBook Pro 14", 14999.0, "M3 Pro芯片，XDR显示屏", 40, "电脑"),
        ("华为MateBook X Pro", 8999.0, "3.1K触控全面屏", 55, "电脑"),
        ("戴尔XPS 13", 9999.0, "13.4英寸InfinityEdge屏", 35, "电脑"),
        ("华硕天选4", 7499.0, "RTX 4060，144Hz电竞屏", 70, "电脑"),
        ("惠普暗影精灵9", 8299.0, "i7-13700HX，240Hz高刷", 45, "电脑"),
        ("小米笔记本Pro 14", 5999.0, "2.8K OLED触控屏", 90, "电脑"),
        ("ROG幻16", 11999.0, "星云原画屏，i9处理器", 25, "电脑"),
        ("机械革命蛟龙16", 6999.0, "RTX 4060，2.5K屏幕", 80, "电脑"),
        ("雷蛇灵刃14", 15999.0, "迷你LED屏，轻薄游戏本", 15, "电脑"),
        ("微软Surface Laptop 5", 9988.0, "触控PixelSense显示屏", 30, "电脑"),
        ("iPad Air 5", 4799.0, "M1芯片，全面屏设计", 150, "平板"),
        ("小米平板6 Pro", 2799.0, "骁龙8+，2.8K高刷屏", 180, "平板"),
        ("三星Tab S9", 6999.0, "Dynamic AMOLED 2X屏", 95, "平板"),
        ("荣耀V8 Pro", 2499.0, "144Hz高刷，天玑8100", 130, "平板"),
        ("联想拯救者Y700", 2399.0, "8.8英寸电竞屏，骁龙8+", 110, "平板"),
        ("vivo Pad 2", 2999.0, "12.1英寸大屏，天玑9000", 120, "平板"),
        ("OPPO Pad 2", 3299.0, "7:5比例屏幕，9510mAh电池", 100, "平板"),
        ("华为MatePad Pro 13.2", 5199.0, "OLED屏，星闪技术", 70, "平板"),
        ("苹果iPad 10", 3599.0, "A14芯片，全面屏升级", 200, "平板"),
        ("微软Surface Pro 9", 8488.0, "Intel处理器，可拆卸键盘", 40, "平板"),
        ("索尼WF-1000XM4", 1699.0, "真无线降噪，LDAC编码", 180, "耳机"),
        ("Bose QC35 II", 1999.0, "经典降噪，20小时续航", 140, "耳机"),
        ("三星Galaxy Buds2 Pro", 1299.0, "24bit高保真，智能降噪", 160, "耳机"),
        ("JBL TUNE 510BT", 399.0, "轻量设计，40小时续航", 300, "耳机"),
        ("漫步者NeoBuds Pro2", 899.0, "数字分频，Hi-Res认证", 220, "耳机"),
        ("Beats Studio Pro", 2899.0, "空间音频，主动降噪", 90, "耳机"),
        ("森海塞尔MOMENTUM 4", 2999.0, "60小时续航，自适应降噪", 75, "耳机"),
        ("华为FreeBuds Pro 3", 1499.0, "麒麟A2芯片，无损音质", 150, "耳机"),
        ("Jabra Elite 7 Pro", 1399.0, "骨传导麦克风，防水设计", 120, "耳机"),
        ("铁三角ATH-M50x", 1299.0, "监听耳机，专业级音质", 100, "耳机"),
        ("任天堂Switch Lite", 1499.0, "便携掌机，多种配色", 250, "游戏"),
        ("Xbox Series X", 3899.0, "4K游戏，快速唤醒", 60, "游戏"),
        ("Valve Steam Deck", 3999.0, "掌上PC游戏机", 80, "游戏"),
        ("罗技G502 X", 699.0, "LIGHTFORCE混动微动", 150, "游戏"),
        ("雷蛇黑寡妇V4", 1299.0, "机械键盘，RGB灯效", 110, "游戏"),
        ("索尼DualSense Edge", 1599.0, "可定制化精英手柄", 95, "游戏"),
        ("微软Xbox精英手柄2代", 1399.0, "可更换组件，无线连接", 70, "游戏"),
        ("北通宙斯2", 899.0, "光轴机械按键，模块化设计", 130, "游戏"),
        ("赛睿寒冰新星7", 1599.0, "无线游戏耳机，ClearCast麦克风", 85, "游戏"),
        ("罗技G Pro X Superlight", 999.0, "超轻量设计，HERO 25K传感器", 200, "游戏"),
        ("LG 27GP850", 2999.0, "27英寸Nano IPS，180Hz", 120, "显示器"),
        ("AOC Q27G3S", 1699.0, "2K 170Hz，1ms响应", 180, "显示器"),
        ("明基PD2705U", 4299.0, "4K设计师显示器，Type-C 90W", 65, "显示器"),
        ("飞利浦279M1RV", 5499.0, "4K 144Hz Nano IPS", 45, "显示器"),
        ("华硕PG32UQ", 7999.0, "32英寸4K 144Hz HDR", 30, "显示器"),
        ("戴尔U2723QX", 3699.0, "4K USB-C显示器，IPS Black", 90, "显示器"),
        ("三星Odyssey G7", 3999.0, "1000R曲面，240Hz", 75, "显示器"),
        ("优派VX2781", 2299.0, "2K 180Hz Fast IPS", 110, "显示器"),
        ("小米Redmi 27英寸", 1499.0, "4K IPS，Type-C 65W", 200, "显示器"),
        ("宏碁XV272U V3", 1999.0, "2K 180Hz，HDR400", 130, "显示器")
    ]
    
    for product in products:
        c.execute("INSERT OR IGNORE INTO products (name, price, description, stock, category) VALUES (?, ?, ?, ?, ?)", product)
    
    # 插入测试用户
    c.execute("INSERT OR IGNORE INTO users (username, password, email, is_admin, role) VALUES ('test', '123', 'test@example.com', 0, 'customer')")
    c.execute("INSERT OR IGNORE INTO users (username, password, email, is_admin, role) VALUES ('sales', 'sales123', 'sales@example.com', 0, 'sales')")
    c.execute("INSERT OR IGNORE INTO users (username, password, email, is_admin, role) VALUES ('admin', 'admin123', 'admin@example.com', 1, 'admin')")
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成，共添加 {} 个商品".format(len(products)))


def get_item_cf_recommendations(user_id, limit=6):
    """基于物品的协同过滤：按用户偏好类别推荐高销量商品，无行为则推荐热销商品。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''SELECT DISTINCT category FROM user_behavior
                 WHERE user_id = ? AND behavior_type IN ('browse', 'purchase')
                   AND category IS NOT NULL AND category != '' ''',
              (user_id,))
    categories = [row[0] for row in c.fetchall()]

    c.execute('SELECT DISTINCT product_id FROM orders WHERE user_id = ?', (user_id,))
    purchased_ids = [row[0] for row in c.fetchall()]

    def query_hot_products(category_filter=None):
        params = []
        where_clauses = []
        if category_filter:
            placeholders = ','.join('?' * len(category_filter))
            where_clauses.append(f'p.category IN ({placeholders})')
            params.extend(category_filter)
        if purchased_ids:
            placeholders = ','.join('?' * len(purchased_ids))
            where_clauses.append(f'p.id NOT IN ({placeholders})')
            params.extend(purchased_ids)
        where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
        params.append(limit)
        c.execute(f'''SELECT p.id, p.name, p.price, p.description, p.stock, p.category,
                             COALESCE(SUM(o.quantity), 0) as sales
                      FROM products p
                      LEFT JOIN orders o ON p.id = o.product_id
                      {where_sql}
                      GROUP BY p.id
                      ORDER BY sales DESC, p.id
                      LIMIT ?''', params)
        return c.fetchall()

    if categories:
        results = query_hot_products(categories)
        if results:
            conn.close()
            return results

    results = query_hot_products()
    conn.close()
    return results


PAGE_SIZE = 30


def paginate_query(c, select_sql, count_sql, params, page, per_page=PAGE_SIZE):
    page = max(1, page or 1)
    c.execute(count_sql, params)
    total = c.fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    c.execute(select_sql + " LIMIT ? OFFSET ?", params + (per_page, offset))
    return c.fetchall(), page, total_pages, total


def detect_sales_anomalies():
    """检测销售异常：今天销量与过去7天日均销量对比，标记暴增或暴跌。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')

    c.execute('''SELECT p.name,
                        COALESCE(SUM(CASE WHEN DATE(o.order_time) = ? THEN o.quantity ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN DATE(o.order_time) >= DATE(?, '-7 days')
                                          AND DATE(o.order_time) < ? THEN o.quantity ELSE 0 END), 0)
                 FROM products p
                 LEFT JOIN orders o ON p.id = o.product_id
                 GROUP BY p.id, p.name''', (today, today, today))
    rows = c.fetchall()
    conn.close()

    anomalies = []
    for name, today_sales, past_7_total in rows:
        past_7_avg = past_7_total / 7.0

        if past_7_avg == 0:
            if today_sales > 0:
                anomalies.append((name, today_sales, past_7_avg, '暴增'))
        elif today_sales > past_7_avg * 2:
            anomalies.append((name, today_sales, past_7_avg, '暴增'))
        elif today_sales < past_7_avg * 0.5:
            anomalies.append((name, today_sales, past_7_avg, '暴跌'))

    return anomalies


@app.route('/api/recommend')
@app.route('/recommend')
def recommend():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    
    recs = get_item_cf_recommendations(session['user_id'])
    return jsonify([{
        'id': r[0],
        'name': r[1],
        'price': r[2],
        'description': r[3],
        'stock': r[4],
        'category': r[5],
        'sales': r[6],
    } for r in recs])


@app.route('/test_recommend')
def test_recommend():
    if not require_role('admin', 'sales'):
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    username = session.get('username')
    recommendations = []
    error = None
    
    try:
        recommendations = get_item_cf_recommendations(user_id)
    except Exception as e:
        error = str(e)
    
    return render_template('test_recommend.html',
                           user_id=user_id,
                           username=username,
                           recommendations=recommendations,
                           error=error)


# 首页 - 需要登录
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    products, page, total_pages, total_count = paginate_query(
        c,
        "SELECT * FROM products",
        "SELECT COUNT(*) FROM products",
        (),
        page,
    )
    conn.close()
    
    recommendations = get_item_cf_recommendations(session['user_id'])
    return render_template('index.html', products=products, username=session.get('username'),
                           recommendations=recommendations, page=page, total_pages=total_pages,
                           total_count=total_count, list_type='index')

# 搜索功能
@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    keyword = request.args.get('keyword', '')
    page = request.args.get('page', 1, type=int)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if keyword:
        params = ('%' + keyword + '%', '%' + keyword + '%')
        products, page, total_pages, total_count = paginate_query(
            c,
            "SELECT * FROM products WHERE name LIKE ? OR description LIKE ?",
            "SELECT COUNT(*) FROM products WHERE name LIKE ? OR description LIKE ?",
            params,
            page,
        )
    else:
        products, page, total_pages, total_count = paginate_query(
            c,
            "SELECT * FROM products",
            "SELECT COUNT(*) FROM products",
            (),
            page,
        )
    
    conn.close()
    
    recommendations = get_item_cf_recommendations(session['user_id'])
    return render_template('index.html', products=products, search_keyword=keyword,
                           username=session.get('username'), recommendations=recommendations,
                           page=page, total_pages=total_pages, total_count=total_count,
                           list_type='search')

# 分类筛选
@app.route('/category/<cat>')
def category(cat):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    products, page, total_pages, total_count = paginate_query(
        c,
        "SELECT * FROM products WHERE category = ?",
        "SELECT COUNT(*) FROM products WHERE category = ?",
        (cat,),
        page,
    )
    conn.close()
    
    recommendations = get_item_cf_recommendations(session['user_id'])
    return render_template('index.html', products=products, current_category=cat,
                           username=session.get('username'), recommendations=recommendations,
                           page=page, total_pages=total_pages, total_count=total_count,
                           list_type='category')

# 商品详情页
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    
    if not product:
        conn.close()
        return "商品不存在", 404
    
    c.execute('''INSERT INTO user_behavior (user_id, username, behavior_type, product_id, category, ip_address, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (session.get('user_id'), session.get('username'), 'browse', product_id, product[5],
               request.remote_addr, time.strftime('%Y-%m-%d %H:%M:%S')))
    
    c.execute("SELECT COUNT(*) FROM products WHERE id != ?", (product_id,))
    other_count = c.fetchone()[0]
    
    if other_count >= 2:
        c.execute("SELECT id, name, price FROM products WHERE id != ? ORDER BY RANDOM() LIMIT 2",
                  (product_id,))
        also_bought = c.fetchall()
    else:
        also_bought = []
    
    conn.commit()
    conn.close()
    
    return render_template('product_detail.html', product=product, username=session.get('username'),
                           also_bought=also_bought)

# 登录页面 - 支持管理者(admin)、销售人员(sales)、普通用户三种角色
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    success = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form.get('user_type', 'user')

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()

        if user:
            role = user[5] if len(user) > 5 and user[5] else 'customer'

            if user_type == 'admin' and role not in ('admin', 'sales'):
                error = "该账号无后台管理权限"
            elif user_type == 'user' and role in ('admin', 'sales'):
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = role
                return redirect(url_for('index'))
            else:
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = role

                c.execute('''INSERT INTO user_behavior (user_id, username, behavior_type, ip_address, created_at)
                             VALUES (?, ?, ?, ?, ?)''',
                          (user[0], user[1], 'login', request.remote_addr,
                           time.strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                conn.close()

                if user_type == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('index'))
        else:
            error = "用户名或密码错误"

        conn.close()

    success = request.args.get('success')
    return render_template('login.html', error=error, success=success)

# 注册页面
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # 检查用户名是否已存在
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        if c.fetchone():
            error = "用户名已存在"
        else:
            # 创建新用户（默认为普通用户）
            c.execute("INSERT INTO users (username, password, email, is_admin, role) VALUES (?, ?, ?, 0, 'customer')", (username, password, email))
            conn.commit()
            # 注册成功，重定向到登录页并传递成功消息
            return redirect(url_for('login', success='注册成功！请登录'))
        
        conn.close()
    
    return render_template('register.html', error=error)

# 登出
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 加入购物车
@app.route('/add')
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    product_id = request.args.get('product_id')
    if product_id:
        if 'cart' not in session:
            session['cart'] = {}

        cart = session['cart']
        cart[str(product_id)] = cart.get(str(product_id), 0) + 1
        session['cart'] = cart
        set_flash('已成功添加至购物车', 'success')

    return redirect(request.referrer or url_for('index'))

# 查看购物车
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cart_items = []
    total = 0
    
    if 'cart' in session:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        for product_id, quantity in session['cart'].items():
            c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            product = c.fetchone()
            if product:
                item_total = product[2] * quantity
                total += item_total
                cart_items.append({
                    'id': product[0],
                    'name': product[1],
                    'price': product[2],
                    'quantity': quantity,
                    'total': item_total
                })
        
        conn.close()
    
    return render_template('cart.html', cart_items=cart_items, total=total)

# 付款页面
@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('cart'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 获取用户信息
    c.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = c.fetchone()
    
    # 获取购物车商品信息
    cart_items = []
    total = 0
    
    for product_id, quantity in session['cart'].items():
        c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = c.fetchone()
        if product:
            item_total = product[2] * quantity
            total += item_total
            cart_items.append({
                'id': product[0],
                'name': product[1],
                'price': product[2],
                'description': product[3],
                'quantity': quantity,
                'total': item_total
            })
    
    conn.close()
    
    return render_template('checkout.html', user=user, cart_items=cart_items, total=total)

# 处理付款
@app.route('/process_payment', methods=['POST'])
def process_payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    payment_status = request.form.get('status')
    
    if payment_status == 'success':
        # 创建订单
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # 先检查库存是否足够
        insufficient_stock = False
        for product_id, quantity in session['cart'].items():
            c.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
            stock = c.fetchone()[0]
            if stock < quantity:
                insufficient_stock = True
                break
        
        if insufficient_stock:
            conn.close()
            set_flash('库存不足，请调整购物车数量', 'error')
            return redirect(url_for('cart'))
        
        # 库存足够，创建订单
        for product_id, quantity in session['cart'].items():
            c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            product = c.fetchone()
            
            if product:
                # 插入订单记录
                c.execute('''INSERT INTO orders (user_id, product_id, product_name, product_price, quantity, total_price, status)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (session['user_id'], product_id, product[1], product[2], quantity, product[2] * quantity, '未发货'))
                
                # 减少库存
                c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
                
                # 记录购买行为
                c.execute('''INSERT INTO user_behavior (user_id, behavior_type, product_id, category, created_at)
                             VALUES (?, ?, ?, ?, ?)''',
                          (session['user_id'], 'purchase', product_id, product[5],
                           time.strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        # 清空购物车
        session.pop('cart', None)

        set_flash('付款成功！订单已生成', 'success')
        return redirect(url_for('orders'))
    else:
        set_flash('付款失败，请重试', 'error')
        return redirect(url_for('cart'))

# 用户订单页面
@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 获取用户的所有订单
    c.execute('''SELECT * FROM orders 
                WHERE user_id = ? 
                ORDER BY order_time DESC''', (session['user_id'],))
    user_orders = c.fetchall()
    
    conn.close()
    
    return render_template('orders.html', orders=user_orders)

# 清空购物车
@app.route('/clear')
def clear_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    session.pop('cart', None)
    return redirect(url_for('cart'))

# ================= 管理员功能 =================

# 管理员仪表板
@app.route('/admin')
def admin_dashboard():
    if not require_role('admin', 'sales'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    
    return render_template('admin/dashboard.html', products=products, username=session.get('username'))

# 管理员查看所有订单
@app.route('/admin/orders')
def admin_orders():
    if not require_role('admin', 'sales'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 获取所有订单，关联用户信息
    c.execute('''SELECT orders.*, users.username 
                FROM orders 
                JOIN users ON orders.user_id = users.id 
                ORDER BY orders.order_time DESC''')
    all_orders = c.fetchall()
    
    conn.close()
    
    return render_template('admin/orders.html', orders=all_orders)

# 销售管理（仅管理者 admin 可访问）
@app.route('/admin/sales_management', methods=['GET', 'POST'])
def sales_management():
    if not require_role('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            new_username = request.form.get('username', '').strip()
            new_password = request.form.get('password', '').strip()
            if new_username and new_password:
                c.execute("SELECT id FROM users WHERE username = ?", (new_username,))
                if c.fetchone():
                    set_flash('用户名已存在', 'error')
                else:
                    c.execute("INSERT INTO users (username, password, email, is_admin, role) VALUES (?, ?, ?, 0, 'sales')",
                              (new_username, new_password, new_username + '@example.com'))
                    conn.commit()
                    set_flash(f'销售人员 {new_username} 创建成功', 'success')
            else:
                set_flash('用户名和密码不能为空', 'error')
            conn.close()
            return redirect(url_for('sales_management'))
        elif action == 'delete':
            user_id = request.form.get('user_id')
            c.execute("DELETE FROM users WHERE id = ? AND role = 'sales'", (user_id,))
            if c.rowcount:
                conn.commit()
                set_flash('销售人员已删除', 'success')
            else:
                set_flash('删除失败', 'error')
            conn.close()
            return redirect(url_for('sales_management'))
        elif action == 'reset_password':
            user_id = request.form.get('user_id')
            new_pwd = request.form.get('new_password', '123456').strip()
            c.execute("UPDATE users SET password = ? WHERE id = ? AND role = 'sales'", (new_pwd, user_id))
            if c.rowcount:
                conn.commit()
                set_flash(f'密码重置成功', 'success')
            else:
                set_flash('重置失败', 'error')
            conn.close()
            return redirect(url_for('sales_management'))

    c.execute("SELECT id, username, email FROM users WHERE role = 'sales' ORDER BY id")
    sales_users = c.fetchall()

    # 统计每个销售的订单量和销售额
    c.execute("""SELECT o.user_id, COUNT(o.id), COALESCE(SUM(o.total_price), 0)
                 FROM orders o JOIN users u ON o.user_id = u.id
                 WHERE u.role = 'sales' GROUP BY o.user_id""")
    sales_stats = {row[0]: (row[1], row[2]) for row in c.fetchall()}

    conn.close()

    return render_template('admin/sales_management.html',
                           sales_users=sales_users,
                           sales_stats=sales_stats)

# 用户浏览/购买日志查看
@app.route('/admin/user-behavior')
def admin_user_behavior():
    if not require_role('admin', 'sales'):
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    filter_user = request.args.get('user', '')
    filter_type = request.args.get('type', '')
    per_page = 50

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    where_clauses = ["behavior_type IN ('browse', 'purchase')"]
    params = []

    if filter_user:
        where_clauses.append("username LIKE ?")
        params.append('%' + filter_user + '%')
    if filter_type:
        where_clauses.append("behavior_type = ?")
        params.append(filter_type)

    where_sql = ' AND '.join(where_clauses)

    c.execute(f"SELECT COUNT(*) FROM user_behavior WHERE {where_sql}", params)
    total = c.fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    c.execute(f'''SELECT ub.id, ub.username, ub.behavior_type, ub.product_id,
                         p.name, ub.category, ub.ip_address, ub.created_at
                  FROM user_behavior ub
                  LEFT JOIN products p ON ub.product_id = p.id
                  WHERE {where_sql}
                  ORDER BY ub.created_at DESC
                  LIMIT ? OFFSET ?''', params + [per_page, offset])
    behaviors = c.fetchall()

    c.execute(f'''SELECT behavior_type, COUNT(*) FROM user_behavior
                  WHERE {where_sql} GROUP BY behavior_type''', params)
    type_counts = dict(c.fetchall())

    conn.close()

    return render_template('admin/user_behavior.html',
                           behaviors=behaviors,
                           page=page, total_pages=total_pages, total=total,
                           filter_user=filter_user, filter_type=filter_type,
                           browse_count=type_counts.get('browse', 0),
                           purchase_count=type_counts.get('purchase', 0))

# 数据分析看板（仅管理者 admin 可访问）
@app.route('/admin/analytics')
def admin_analytics():
    if not require_role('admin'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''SELECT DATE(order_time) as day, SUM(total_price) as sales
                 FROM orders
                 WHERE DATE(order_time) >= DATE('now', '-6 days')
                 GROUP BY DATE(order_time)
                 ORDER BY day''')
    sales_by_day = {row[0]: row[1] for row in c.fetchall()}
    
    daily_sales = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        daily_sales.append((day, sales_by_day.get(day, 0) or 0))
    
    weekly_sales = []
    for i in range(3, -1, -1):
        week_start = datetime.now() - timedelta(days=datetime.now().weekday() + 7 * i)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        c.execute('''SELECT COALESCE(SUM(total_price), 0) FROM orders
                     WHERE order_time >= ? AND order_time < ?''',
                  (week_start.strftime('%Y-%m-%d %H:%M:%S'),
                   week_end.strftime('%Y-%m-%d %H:%M:%S')))
        sales = c.fetchone()[0]
        weekly_sales.append((4 - i, sales))
    
    c.execute('''SELECT product_name, SUM(quantity) as total_qty, SUM(total_price) as total_sales
                 FROM orders
                 GROUP BY product_id
                 ORDER BY total_qty DESC
                 LIMIT 10''')
    top_products = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*), COALESCE(SUM(total_price), 0), COALESCE(SUM(quantity), 0) FROM orders")
    stats = c.fetchone()
    total_orders = stats[0]
    total_sales = stats[1]
    total_products = stats[2]
    
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    avg_products_per_user = total_products / total_users if total_users > 0 else 0
    
    c.execute('''SELECT u.id, u.username, COALESCE(SUM(o.total_price), 0) as total_spent
                 FROM users u
                 LEFT JOIN orders o ON u.id = o.user_id
                 GROUP BY u.id
                 ORDER BY total_spent DESC''')
    users_spending = c.fetchall()
    
    c.execute('''SELECT o.user_id, p.category, SUM(o.quantity) as qty
                 FROM orders o
                 JOIN products p ON o.product_id = p.id
                 GROUP BY o.user_id, p.category''')
    category_prefs = {}
    for user_id, category, qty in c.fetchall():
        if user_id not in category_prefs or qty > category_prefs[user_id][1]:
            category_prefs[user_id] = (category, qty)
    
    user_profiles = []
    for user_id, username, total_spent in users_spending:
        preferred_category = category_prefs[user_id][0] if user_id in category_prefs else '无'
        user_profiles.append((username, total_spent, preferred_category))
    
    conn.close()
    
    sales_anomalies = detect_sales_anomalies()
    
    return render_template('admin/analytics.html',
                           username=session.get('username'),
                           daily_sales_json=json.dumps(daily_sales),
                           weekly_sales_json=json.dumps(weekly_sales),
                           top_products=top_products,
                           total_users=total_users,
                           total_orders=total_orders,
                           total_sales=total_sales,
                           avg_order_value=avg_order_value,
                           avg_products_per_user=avg_products_per_user,
                           user_profiles=user_profiles,
                           sales_anomalies=sales_anomalies)

# 管理员更新订单状态
@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if not require_role('admin', 'sales'):
        return redirect(url_for('login'))
    
    new_status = request.form.get('status')
    
    if new_status in ['未发货', '已发货', '待收货', '已收货']:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        conn.close()
    
    return redirect(url_for('admin_orders'))

# 添加商品页面
@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if not require_role('admin', 'sales'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        category = request.form['category']
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO products (name, price, description, stock, category) VALUES (?, ?, ?, ?, ?)",
                 (name, price, description, stock, category))
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_product.html')

# 编辑商品页面
@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not require_role('admin', 'sales'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        category = request.form['category']
        
        c.execute("UPDATE products SET name=?, price=?, description=?, stock=?, category=? WHERE id=?",
                 (name, price, description, stock, category, product_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_dashboard'))
    
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()
    
    if not product:
        return "商品不存在"
    
    return render_template('admin/edit_product.html', product=product)

# 删除商品
@app.route('/admin/delete_product/<int:product_id>')
def delete_product(product_id):
    if not require_role('admin', 'sales'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

# 管理员退出
@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('login'))

def migrate_db():
    """升级旧数据库到角色系统：添加 role 列，修正用户角色。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 为旧表添加 role 列（不存在则添加）
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if 'role' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'customer'")
        print("[迁移] 已添加 role 列")
        # 将原有 is_admin=1 的用户设为 sales 角色
        c.execute("UPDATE users SET role = 'sales' WHERE is_admin = 1")
        # 将 test 用户设为 customer
        c.execute("UPDATE users SET role = 'customer' WHERE username = 'test' AND role IS NULL")
        conn.commit()

    # 确保 admin 管理员账号存在
    c.execute("SELECT id FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT OR IGNORE INTO users (username, password, email, is_admin, role) VALUES ('admin', 'admin123', 'admin@example.com', 1, 'admin')")
        conn.commit()
        print("[迁移] 已创建 admin 管理者账号")
    else:
        c.execute("UPDATE users SET role = 'admin', is_admin = 1 WHERE username = 'admin'")
        conn.commit()

    # 确保 sales 销售账号角色正确
    c.execute("SELECT id, role FROM users WHERE username = 'sales'")
    sales_user = c.fetchone()
    if sales_user:
        c.execute("UPDATE users SET role = 'sales', is_admin = 0 WHERE username = 'sales'")
        if sales_user[1] != 'sales':
            print("[迁移] 已将 sales 角色修正为销售人员")
        conn.commit()

    conn.close()


if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        init_db()
    else:
        print("[信息] 数据库已存在，直接使用")
        migrate_db()
    
    print("=" * 50)
    print("🚀 电商网站已启动")
    print("👉 访问: http://127.0.0.1:5000")
    print("👉 普通用户: test / 123")
    print("👉 销售人员: sales / sales123")
    print("👉 管理者: admin / admin123")
    print("👉 商品总数: 66个商品")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)