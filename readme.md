# 本地电商网站项目 - 维护文档

## 项目基本信息
-项目名称: 本地电商网站
-创建日期: 2025年12月29日
-首次运行: 3个月（至2026年3月29日）
-维护日期: 2026年3月29日-2026年5月27日
-再次运行: 6个月（至2026年11月27日）
- 项目位置: `C:\Users\29414\Desktop\local_ecommerce\`
- 负责人: 孙常朔 202330452891 网络工程
## 快速启动指南

### 安装依赖
```bash
cd C:\Users\29414\Desktop\local_ecommerce
pip install -r requirements.txt
```

### 启动本地服务
```bash
python app.py
```

### 生成演示数据（可选）
```bash
python generate_demo_data.py
```

### 访问地址
-本地访问: http://127.0.0.1:5000
-公网访问: 
---
## 账号体系

项目采用三角色权限模型，通过 `users` 表的 `role` 字段区分：

| 账号     | 密码   | 角色              | 权限说明 |
|---       |---    |---                |---      |
| `test`   | `123` | customer（普通用户）| 浏览商品、搜索、购物车、下单 |
| `sales`  | `sales123` | sales（销售人员）| 商品管理、订单管理、用户行为日志 |
| `admin`  | `admin123` | admin（管理者） | 全部权限：商品/订单/行为日志 + 数据分析看板 + 销售人员管理 |

## 功能清单

### 用户端
- 用户注册/登录
- 商品浏览、搜索、分类筛选（分页，每页30条）
- 商品详情页（浏览记录 + "看了该商品的人也买了"推荐）
- 基于物品的协同过滤推荐算法
- 购物车（添加/清空/数量调整）
- 付款流程（库存扣减 + 订单生成）
- 订单历史查看
- 操作成功/失败 Toast 弹窗提示

### 销售后台
- 商品管理：新增、编辑、删除商品
- 订单管理：查看所有订单、更新订单状态（未发货→已发货→待收货→已收货）
- 用户行为日志：按用户名/行为类型筛选，分页查看

### 管理后台
- 数据分析看板：近7天日销售额、近4周周销售额、热销商品排行TOP10、用户消费画像、销售异常检测（暴增/暴跌）
- 销售人员管理（`/admin/sales_management`）：新增/删除销售人员、重置密码

---

## 数据库结构（SQLite）

数据库文件：`ecommerce.db`

### users（用户表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| username | TEXT UNIQUE | 用户名 |
| password | TEXT | 密码（明文，生产环境需加密） |
| email | TEXT | 邮箱 |
| is_admin | INTEGER | 保留字段（0/1） |
| role | TEXT | 角色：customer / sales / admin |

### products（商品表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 商品名称 |
| price | REAL | 价格 |
| description | TEXT | 描述 |
| stock | INTEGER | 库存数量 |
| category | TEXT | 分类 |

### orders（订单表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER FK | 用户ID |
| product_id | INTEGER FK | 商品ID |
| product_name | TEXT | 商品快照名 |
| product_price | REAL | 商品快照价格 |
| quantity | INTEGER | 数量 |
| total_price | REAL | 总价 |
| status | TEXT | 状态：未发货/已发货/待收货/已收货 |
| order_time | TIMESTAMP | 下单时间 |

### user_behavior（用户行为表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER | 用户ID |
| username | TEXT | 用户名 |
| behavior_type | TEXT | 行为类型：browse / purchase / login |
| product_id | INTEGER | 商品ID |
| category | TEXT | 商品分类 |
| stay_duration | INTEGER | 停留时长（秒） |
| ip_address | TEXT | IP地址 |
| created_at | TIMESTAMP | 行为时间 |

---

## 项目文件结构

```
local_ecommerce/
├── app.py                      # Flask 主应用（路由、业务逻辑）
├── generate_demo_data.py       # 模拟数据生成脚本
├── ecommerce.db                # SQLite 数据库（自动生成）
├── requirements.txt            # Python 依赖
├── readme.md                   # 项目文档
├── static/
│   └── style.css               # 全局样式
└── templates/
    ├── _toast.html             # Toast 弹窗组件
    ├── index.html              # 首页（商品列表/搜索/分类）
    ├── product_detail.html     # 商品详情页
    ├── login.html              # 登录页
    ├── register.html           # 注册页
    ├── cart.html               # 购物车
    ├── checkout.html           # 付款确认页
    ├── orders.html             # 用户订单页
    ├── test_recommend.html     # 推荐算法测试页
    └── admin/
        ├── dashboard.html      # 后台仪表板（商品管理）
        ├── orders.html         # 后台订单管理
        ├── analytics.html      # 数据分析看板
        ├── add_product.html    # 新增商品
        ├── edit_product.html   # 编辑商品
        ├── user_behavior.html  # 用户行为日志
        └── sales_management.html # 销售人员管理
```

---

## 技术栈

- 后端: Python 3 + Flask 2.x
- 数据库: SQLite 3
- 前端: Jinja2 模板 + 原生 HTML/CSS/JS
- 

---

## 最近更新

- 三角色权限体系（admin / sales / customer）
- 管理者可管理销售人员账号
- 数据分析看板：销售趋势、异常检测、用户画像
- 物品协同过滤推荐算法
- Toast 弹窗提示（购物车/付款反馈）
- 用户浏览/购买行为日志
