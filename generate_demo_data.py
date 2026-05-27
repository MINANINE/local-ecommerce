"""生成过去30天的模拟浏览与购买数据，写入 ecommerce.db。"""

import os
import random
import sqlite3
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "ecommerce.db")

DEMO_USERS = [
    ("test", "123", "test@example.com"),
    ("user2", "123", "user2@example.com"),
    ("user3", "123", "user3@example.com"),
]

ORDER_STATUSES = ["未发货", "已发货", "待收货", "已收货"]
FAKE_IPS = ["127.0.0.1", "192.168.1.10", "192.168.1.20", "10.0.0.5", "10.0.0.8"]


def ensure_tables(cursor):
    """确保所需表存在（与 app.py 结构一致）。"""
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users
           (id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            is_admin INTEGER DEFAULT 0)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS products
           (id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            stock INTEGER NOT NULL DEFAULT 0,
            category TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS orders
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
            FOREIGN KEY (product_id) REFERENCES products (id))"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS user_behavior
           (id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            behavior_type TEXT NOT NULL,
            product_id INTEGER,
            category TEXT,
            stay_duration INTEGER DEFAULT 0,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_behavior_user ON user_behavior(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_behavior_time ON user_behavior(created_at)"
    )


def random_datetime(days_ago_start, days_ago_end):
    """在 [days_ago_end, days_ago_start] 天前范围内生成随机时间。"""
    start = datetime.now() - timedelta(days=days_ago_start)
    end = datetime.now() - timedelta(days=days_ago_end)
    delta_seconds = int((end - start).total_seconds())
    if delta_seconds <= 0:
        return start
    return start + timedelta(seconds=random.randint(0, delta_seconds))


def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def ensure_users(cursor):
    inserted = 0
    for username, password, email in DEMO_USERS:
        cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password, email, is_admin) VALUES (?, ?, ?, 0)",
                (username, password, email),
            )
            inserted += 1
    return inserted


def main():
    if not os.path.exists(DB_FILE):
        print(f"[错误] 数据库不存在: {DB_FILE}")
        print("请先运行 python app.py 初始化数据库。")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    ensure_tables(c)
    conn.commit()

    users_inserted = ensure_users(c)
    conn.commit()

    c.execute(
        "SELECT id, username FROM users WHERE username IN (?, ?, ?)",
        tuple(u[0] for u in DEMO_USERS),
    )
    users = c.fetchall()
    if not users:
        print("[错误] 未找到演示用户，请检查 users 表。")
        conn.close()
        return

    c.execute("SELECT id, name, price, category FROM products")
    products = c.fetchall()
    if not products:
        print("[错误] products 表为空，请先运行 app.py 初始化商品数据。")
        conn.close()
        return

    browse_count = 0
    order_count = 0
    purchase_count = 0

    # 浏览记录：过去30天，每天每个用户浏览 5-10 个商品
    for day_offset in range(30, 0, -1):
        day_base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        day_base = day_base - timedelta(days=day_offset)

        for user_id, username in users:
            browse_num = random.randint(5, 10)
            sampled = random.sample(products, min(browse_num, len(products)))

            for product_id, name, price, category in sampled:
                created_at = day_base + timedelta(
                    hours=random.randint(8, 22),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59),
                )
                c.execute(
                    """INSERT INTO user_behavior
                       (user_id, username, behavior_type, product_id, category, ip_address, created_at)
                       VALUES (?, ?, 'browse', ?, ?, ?, ?)""",
                    (
                        user_id,
                        username,
                        product_id,
                        category,
                        random.choice(FAKE_IPS),
                        format_time(created_at),
                    ),
                )
                browse_count += 1

    # 购买记录：过去30天随机 30-50 笔订单
    order_num = random.randint(30, 50)
    for _ in range(order_num):
        user_id, username = random.choice(users)
        product_id, name, price, category = random.choice(products)
        quantity = random.randint(1, 3)
        total_price = price * quantity
        order_time = random_datetime(30, 0)
        status = random.choice(ORDER_STATUSES)
        time_str = format_time(order_time)

        c.execute(
            """INSERT INTO orders
               (user_id, product_id, product_name, product_price, quantity, total_price, status, order_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, product_id, name, price, quantity, total_price, status, time_str),
        )
        order_count += 1

        c.execute(
            """INSERT INTO user_behavior
               (user_id, username, behavior_type, product_id, category, created_at)
               VALUES (?, ?, 'purchase', ?, ?, ?)""",
            (user_id, username, product_id, category, time_str),
        )
        purchase_count += 1

    conn.commit()

    # 统计查询
    c.execute("SELECT COUNT(*) FROM user_behavior WHERE behavior_type = 'browse'")
    total_browse = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM user_behavior WHERE behavior_type = 'purchase'")
    total_purchase = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    c.execute(
        """SELECT MIN(created_at), MAX(created_at)
           FROM user_behavior
           WHERE behavior_type IN ('browse', 'purchase')"""
    )
    behavior_range = c.fetchone()
    c.execute("SELECT MIN(order_time), MAX(order_time) FROM orders")
    order_range = c.fetchone()

    conn.close()

    print("=" * 50)
    print("[完成] 模拟数据生成完成")
    print("=" * 50)
    print(f"数据库: {DB_FILE}")
    print(f"演示用户: {', '.join(u[0] for u in DEMO_USERS)}")
    print(f"本次新增用户: {users_inserted} 个")
    print(f"可用商品数: {len(products)} 个")
    print("-" * 50)
    print("本次生成:")
    print(f"  浏览记录 (browse):  {browse_count} 条")
    print(f"  订单记录 (orders):  {order_count} 条")
    print(f"  购买行为 (purchase): {purchase_count} 条")
    print("-" * 50)
    print("数据库累计:")
    print(f"  浏览记录总数: {total_browse} 条")
    print(f"  购买行为总数: {total_purchase} 条")
    print(f"  订单总数:     {total_orders} 条")
    if behavior_range[0]:
        print(f"  行为时间范围: {behavior_range[0]} ~ {behavior_range[1]}")
    if order_range[0]:
        print(f"  订单时间范围: {order_range[0]} ~ {order_range[1]}")
    print("=" * 50)


if __name__ == "__main__":
    main()
