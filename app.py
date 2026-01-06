from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "simple_key_123"
DB_FILE = "ecommerce.db"

# 初始化数据库
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
    
    # 创建用户表，增加is_admin字段
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  email TEXT,
                  is_admin INTEGER DEFAULT 0)''')  # 0=普通用户, 1=管理员
    
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
    
    # 插入测试商品 - 完整列表
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
    
    # 插入测试用户（test是普通用户）
    c.execute("INSERT OR IGNORE INTO users (username, password, email, is_admin) VALUES ('test', '123', 'test@example.com', 0)")
    
    # 插入管理员用户（admin是管理员）
    c.execute("INSERT OR IGNORE INTO users (username, password, email, is_admin) VALUES ('admin', 'admin123', 'admin@example.com', 1)")
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成，共添加 {} 个商品".format(len(products)))

# 首页 - 需要登录
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    
    return render_template('index.html', products=products, username=session.get('username'))

# 搜索功能
@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    keyword = request.args.get('keyword', '')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if keyword:
        c.execute("SELECT * FROM products WHERE name LIKE ? OR description LIKE ?", 
                 ('%' + keyword + '%', '%' + keyword + '%'))
    else:
        c.execute("SELECT * FROM products")
    
    products = c.fetchall()
    conn.close()
    
    return render_template('index.html', products=products, search_keyword=keyword, username=session.get('username'))

# 分类筛选
@app.route('/category/<cat>')
def category(cat):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE category = ?", (cat,))
    products = c.fetchall()
    conn.close()
    
    return render_template('index.html', products=products, current_category=cat, username=session.get('username'))

# 登录页面 - 同时处理用户和管理员登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    success = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form.get('user_type', 'user')  # user 或 admin
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            # 检查用户类型
            is_admin = user[4]  # 第5列是is_admin字段
            
            if user_type == 'admin' and is_admin == 0:
                error = "该账号不是管理员"
            elif user_type == 'user' and is_admin == 1:
                # 管理员也可以用普通用户身份登录
                pass
            else:
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['is_admin'] = is_admin
                
                if user_type == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('index'))
        else:
            error = "用户名或密码错误"
    
    # 检查是否有来自注册页的成功消息
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
            c.execute("INSERT INTO users (username, password, email, is_admin) VALUES (?, ?, ?, 0)", (username, password, email))
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
            return "库存不足，请调整购物车数量", 400
        
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
        
        conn.commit()
        conn.close()
        
        # 清空购物车
        session.pop('cart', None)
        
        return redirect(url_for('orders'))
    else:
        # 付款失败，返回购物车
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
    if 'user_id' not in session or session.get('is_admin') != 1:
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
    if 'user_id' not in session or session.get('is_admin') != 1:
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

# 管理员更新订单状态
@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session or session.get('is_admin') != 1:
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
    if 'user_id' not in session or session.get('is_admin') != 1:
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
    if 'user_id' not in session or session.get('is_admin') != 1:
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
    if 'user_id' not in session or session.get('is_admin') != 1:
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

if __name__ == '__main__':
    # 删除旧数据库重新开始
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()
    
    print("=" * 50)
    print("🚀 电商网站已启动")
    print("👉 访问: http://127.0.0.1:5000")
    print("👉 普通用户: test / 123")
    print("👉 管理员: admin / admin123")
    print("👉 商品总数: 66个商品")
    print("👉 新功能: 搜索商品、付款流程、订单管理")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
