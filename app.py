from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime

# 导入蓝图
from auth import auth_bp
from order import order_bp
from admin import admin_bp

# 初始化Flask应用
app = Flask(__name__)
app.secret_key = os.urandom(24)  # 更安全的随机密钥
DB_FILE = "ecommerce.db"

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(order_bp)
app.register_blueprint(admin_bp)

# 在 init_db() 函数中增加以下表结构
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 原有的商品表
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  price REAL NOT NULL,
                  description TEXT,
                  stock INTEGER NOT NULL DEFAULT 0,
                  category TEXT,
                  image_url TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  is_active INTEGER DEFAULT 1)''')
    
    # 新增：用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  full_name TEXT,
                  address TEXT,
                  phone TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  is_admin INTEGER DEFAULT 0)''')
    
    # 新增：订单表
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_number TEXT UNIQUE NOT NULL,
                  user_id INTEGER NOT NULL,
                  total_amount REAL NOT NULL,
                  status TEXT DEFAULT 'pending', -- pending, paid, shipped, delivered, cancelled
                  shipping_address TEXT,
                  payment_method TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # 新增：订单项表
    c.execute('''CREATE TABLE IF NOT EXISTS order_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_id INTEGER NOT NULL,
                  product_id INTEGER NOT NULL,
                  quantity INTEGER NOT NULL,
                  price REAL NOT NULL,
                  FOREIGN KEY (order_id) REFERENCES orders (id),
                  FOREIGN KEY (product_id) REFERENCES products (id))''')
    
    # 新增：购物车表（替代session存储）
    c.execute('''CREATE TABLE IF NOT EXISTS cart_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  product_id INTEGER NOT NULL,
                  quantity INTEGER NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  FOREIGN KEY (product_id) REFERENCES products (id))''')
    
    # 新增：用户浏览日志
    c.execute('''CREATE TABLE IF NOT EXISTS user_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  ip_address TEXT,
                  user_agent TEXT,
                  action TEXT, -- view_product, add_to_cart, purchase, etc.
                  product_id INTEGER,
                  details TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 插入测试数据
    # 1. 添加更多测试商品
    test_products = [
        ("小米14 手机", 4299.0, "骁龙8 Gen3，6.36英寸直屏", 50, "手机数码", "/static/images/xiaomi.jpg"),
        ("Apple AirPods Pro 2", 2499.0, "主动降噪，无线充电", 100, "耳机", "/static/images/airpods.jpg"),
        ("联想拯救者Y9000P", 9999.0, "i9处理器，RTX 4060显卡", 30, "电脑", "/static/images/lenovo.jpg"),
        ("华为MatePad Pro", 3499.0, "12.6英寸OLED全面屏", 40, "平板", "/static/images/huawei.jpg"),
        ("索尼PS5游戏机", 3899.0, "光驱版，支持4K游戏", 20, "游戏", "/static/images/ps5.jpg"),
        ("戴尔U2723QE显示器", 3999.0, "27英寸4K设计师显示器", 25, "显示器", "/static/images/dell.jpg"),
        ("罗技MX Master 3", 699.0, "无线蓝牙鼠标", 60, "外设", "/static/images/logitech.jpg"),
        ("三星980 PRO SSD 1TB", 899.0, "NVMe M.2固态硬盘", 80, "存储", "/static/images/samsung.jpg")
    ]
    
    for product in test_products:
        c.execute('''INSERT OR IGNORE INTO products 
                    (name, price, description, stock, category, image_url) 
                    VALUES (?, ?, ?, ?, ?, ?)''', product)
    
    # 2. 添加测试管理员用户 (密码: admin123)
    c.execute('''INSERT OR IGNORE INTO users 
                (username, email, password_hash, full_name, is_admin) 
                VALUES (?, ?, ?, ?, ?)''', 
                ('admin', 'admin@shop.com', 
                 'pbkdf2:sha256:260000$abcdefgh$1234567890abcdef',  # 实际使用时会加密
                 '系统管理员', 1))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 获取查询参数
    category = request.args.get('category', '')
    
    if category:
        c.execute("SELECT * FROM products WHERE category = ?", (category,))
    else:
        c.execute("SELECT * FROM products")
    
    products = c.fetchall()
    
    # 获取所有分类用于导航
    c.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL")
    categories = c.fetchall()
    
    conn.close()
    return render_template('index.html', products=products, categories=categories)
    
    # 排序
    if sort == 'price_asc':
        query += " ORDER BY price ASC"
    elif sort == 'price_desc':
        query += " ORDER BY price DESC"
    elif sort == 'popular':
        # 需要关联订单数据，这里简化为按销量排序（如果有销量字段）
        query += " ORDER BY (SELECT COUNT(*) FROM order_items WHERE product_id = products.id) DESC"
    else:  # newest
        query += " ORDER BY created_at DESC"
    
    c.execute(query, params)
    products = c.fetchall()
    
    # 获取分类
    c.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND is_active = 1")
    categories = c.fetchall()
    
    conn.close()
    
    # 记录用户浏览行为
    if 'user_id' in session:
        from auth import log_user_action
        log_user_action(session['user_id'], 'browse_products', 
                       request.remote_addr, request.user_agent.string,
                       None, f"分类: {category}, 搜索: {search}")
    
    return render_template('index.html', products=products, categories=categories)

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    cart_items = []
    total_price = 0.0

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for product_id, quantity in cart.items():
        c.execute("SELECT * FROM products WHERE id=?", (product_id,))
        product = c.fetchone()
        if product:
            item_total = product[2] * quantity
            total_price += item_total
            cart_items.append({
                'id': product[0],
                'name': product[1],
                'price': product[2],
                'quantity': quantity,
                'item_total': item_total
            })
    conn.close()

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    
    if not product:
        conn.close()
        return "商品不存在", 404
    
    # 记录用户浏览行为
    if 'user_id' in session:
        from auth import log_user_action
        log_user_action(session['user_id'], 'view_product', 
                       request.remote_addr, request.user_agent.string,
                       product_id, f"商品: {product[1]}")
    
    # 获取相关商品
    if product[5]:  # 如果有分类
        c.execute("SELECT * FROM products WHERE category = ? AND id != ? AND is_active = 1 LIMIT 4", 
                 (product[5], product_id))
    else:
        c.execute("SELECT * FROM products WHERE id != ? AND is_active = 1 ORDER BY RANDOM() LIMIT 4", 
                 (product_id,))
    
    related_products = c.fetchall()
    
    conn.close()
    
    return render_template('product_detail.html', product=product, related_products=related_products)

# 搜索功能
@app.route('/search')
def search():
    query = request.args.get('q', '')
    
    if not query:
        return redirect(url_for('index'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT * FROM products WHERE name LIKE ? OR description LIKE ? AND is_active = 1", 
             (f'%{query}%', f'%{query}%'))
    products = c.fetchall()
    
    conn.close()
    
    return render_template('search_results.html', products=products, query=query)

# 错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# 启动服务
if __name__ == '__main__':
    init_db()
    
    # 获取局域网IP
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"局域网访问: http://{local_ip}:5000")
    except:
        pass
    
    app.run(host='0.0.0.0', port=5000, debug=False)
