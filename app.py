from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime, timedelta
import webbrowser
from threading import Timer
import uuid
import socket
import requests

app = Flask(__name__)
app.config['DATABASE'] = 'phishing_system.db'


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE')
    return response


def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            department TEXT,
            user_type TEXT DEFAULT 'student',
            registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            phishing_type TEXT,
            difficulty_level TEXT DEFAULT 'medium',
            email_subject TEXT,
            email_content TEXT,
            target_audience TEXT DEFAULT 'all',
            status TEXT DEFAULT 'draft',
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            sent_date DATETIME,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS user_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            campaign_id INTEGER,
            interaction_type TEXT,
            interaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            response_time REAL,
            data_entered TEXT,
            ip_address TEXT,
            user_agent TEXT,
            risk_score INTEGER DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS external_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_code TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            campaign_id INTEGER,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            expiry_date DATETIME,
            is_active BOOLEAN DEFAULT 1,
            used_count INTEGER DEFAULT 0,
            max_uses INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')

    try:
        c.execute("INSERT OR IGNORE INTO users (email, name, department, user_type) VALUES (?, ?, ?, ?)",
                  ('admin@university.edu', 'مدير النظام', 'IT', 'admin'))
        c.execute("INSERT OR IGNORE INTO users (email, name, department) VALUES (?, ?, ?)",
                  ('student1@university.edu', 'طالب تجريبي', 'Engineering'))
        c.execute("INSERT OR IGNORE INTO users (email, name, department) VALUES (?, ?, ?)",
                  ('employee1@university.edu', 'موظف تجريبي', 'Administration'))

        campaigns_data = [
            ('حملة التوعية الأولى', 'تأكيد الحساب الجامعي', 'email', 'easy',
             'تنبيه عاجل: تأكيد حسابك الجامعي مطلوب',
             '''<div dir="rtl">
             <h3>عزيزي المستخدم،</h3>
             <p>نحتاج إلى تأكيد معلومات حسابك الجامعي للحفاظ على أمان النظام.</p>
             <p>يرجى تحديث بياناتك في أقرب وقت ممكن.</p>
             <p><a href="{tracking_url}">انقر هنا لتحديث معلوماتك</a></p>
             </div>'''),

            ('حملة التوعية الثانية', 'تحديث كلمة المرور', 'email', 'medium',
             'إشعار أمني: تحديث فوري لكلمة المرور',
             '''<div dir="rtl">
             <h3>تنبيه أمني مهم</h3>
             <p>لقد اكتشفنا نشاطاً غير عادي على حسابك.</p>
             <p>لحماية معلوماتك، نحتاج منك تحديث كلمة المرور فوراً.</p>
             <p><a href="{tracking_url}">انقر هنا لتغيير كلمة المرور</a></p>
             </div>''')
        ]

        for campaign in campaigns_data:
            c.execute('''
                INSERT OR IGNORE INTO campaigns 
                (name, description, phishing_type, difficulty_level, email_subject, email_content)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', campaign)

        conn.commit()
        print("✅ تم تهيئة قاعدة البيانات والبيانات التجريبية")
    except Exception as e:
        print(f"⚠️  ملاحظة: {e}")

    conn.close()


init_db()


def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def get_external_base_url():
    """الحصول على الرابط الأساسي للوصول الخارجي"""
    # إذا كان في production، استخدم النطاق الحقيقي
    if not request.host_url.startswith('http://localhost'):
        return request.host_url.rstrip('/')
    
    # في التطوير، حاول استخدام ngrok إذا كان شغال
    try:
        ngrok_tunnels = requests.get('http://localhost:4040/api/tunnels', timeout=2).json()
        for tunnel in ngrok_tunnels['tunnels']:
            if tunnel['proto'] == 'https':
                return tunnel['public_url']
    except:
        pass
    
    # إذا ما نجح ngrok، استخدم IP الجهاز
    try:
        # الحصول على IP المحلي
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return f"http://{local_ip}:5000"
    except:
        return "http://localhost:5000"


# ========== الصفحات الرئيسية ==========

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>نظام التوعية بالتصيد</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
            .header { background: #2c3e50; color: white; padding: 40px; text-align: center; }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .nav { background: #34495e; padding: 15px; text-align: center; }
            .nav a { color: white; text-decoration: none; padding: 10px 20px; margin: 0 10px; border-radius: 25px; transition: background 0.3s; display: inline-block; }
            .nav a:hover { background: #3498db; }
            .content { padding: 40px; }
            .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }
            .stat-card { background: #f8f9fa; padding: 25px; border-radius: 10px; text-align: center; border-left: 5px solid #3498db; }
            .stat-card h3 { font-size: 2.5em; color: #2c3e50; margin-bottom: 10px; }
            .features { display: grid; grid-template-columns: repeat(2, 1fr); gap: 25px; }
            .feature-card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); border-top: 4px solid #3498db; }
            .feature-card h3 { color: #2c3e50; margin-bottom: 15px; }
            .btn { display: inline-block; background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; margin: 10px 5px; transition: background 0.3s; }
            .btn:hover { background: #2980b9; }
            .footer { background: #ecf0f1; padding: 20px; text-align: center; color: #7f8c8d; margin-top: 40px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 نظام التوعية بالتصيد</h1>
                <p>حماية مجتمعنا الجامعي من التهديدات الإلكترونية</p>
            </div>

            <div class="nav">
                <a href="/">الرئيسية</a>
                <a href="/dashboard">لوحة التحكم</a>
                <a href="/training">التدريب</a>
            </div>

            <div class="content">
                <div class="stats">
                    <div class="stat-card"><h3 id="totalUsers">0</h3><p>المستخدمين</p></div>
                    <div class="stat-card"><h3 id="totalCampaigns">0</h3><p>الحملات</p></div>
                    <div class="stat-card"><h3 id="totalResponses">0</h3><p>التفاعلات</p></div>
                    <div class="stat-card"><h3 id="successRate">0%</h3><p>معدل النجاح</p></div>
                </div>

                <div class="features">
                    <div class="feature-card">
                        <h3>📧 محاكاة واقعية</h3>
                        <p>تجارب آمنة لمحاكاة هجمات التصيد الحقيقية</p>
                        <a href="/dashboard" class="btn">بدء المحاكاة</a>
                    </div>
                    <div class="feature-card">
                        <h3>📊 تحليل مفصل</h3>
                        <p>تتبع أداء المستخدمين وتحسين المهارات</p>
                        <a href="/dashboard" class="btn">عرض التقارير</a>
                    </div>
                    <div class="feature-card">
                        <h3>🎓 تدريب تفاعلي</h3>
                        <p>مواد تدريبية شاملة لتعزيز الوعي الأمني</p>
                        <a href="/training" class="btn">البدء بالتدريب</a>
                    </div>
                    <div class="feature-card">
                        <h3>🛡️ حماية مستدامة</h3>
                        <p>نظام متكامل لضمان استمرارية التوعية</p>
                        <a href="/training" class="btn">المزيد</a>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p>نظام التوعية بالتصيد - الجامعة © 2024</p>
            </div>
        </div>

        <script>
            fetch('/api/stats').then(r => r.json()).then(data => {
                document.getElementById('totalUsers').textContent = data.total_users;
                document.getElementById('totalCampaigns').textContent = data.total_campaigns;
                document.getElementById('totalResponses').textContent = data.total_responses;
                document.getElementById('successRate').textContent = data.success_rate + '%';
            });
        </script>
    </body>
    </html>
    '''


@app.route('/dashboard')
def dashboard():
    return '''
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة التحكم - نظام التوعية بالتصيد</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            body { background: #f5f6fa; min-height: 100vh; }
            .navbar { background: #2c3e50; color: white; padding: 1rem 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .nav-container { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; }
            .nav-logo h1 { font-size: 1.5rem; font-weight: bold; }
            .nav-menu { display: flex; list-style: none; gap: 2rem; }
            .nav-menu a { color: white; text-decoration: none; padding: 0.5rem 1rem; border-radius: 5px; transition: background 0.3s; }
            .nav-menu a:hover, .nav-menu a.active { background: #34495e; }
            .main-content { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
            .dashboard-section { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin-bottom: 2rem; }
            .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 2px solid #ecf0f1; }
            .section-header h3 { color: #2c3e50; font-size: 1.5rem; }
            .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem; }
            .stat-card { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); text-align: center; border-left: 5px solid #3498db; }
            .stat-number { font-size: 2.5rem; font-weight: bold; color: #2c3e50; margin-bottom: 0.5rem; }
            .btn { display: inline-block; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; font-size: 16px; cursor: pointer; transition: all 0.3s; text-align: center; }
            .btn-primary { background: #3498db; color: white; }
            .btn-primary:hover { background: #2980b9; }
            .btn-secondary { background: #95a5a6; color: white; }
            .btn-secondary:hover { background: #7f8c8d; }
            .form { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
            .form-group { margin-bottom: 1.5rem; }
            .form-group label { display: block; margin-bottom: 0.5rem; color: #2c3e50; font-weight: bold; }
            .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 6px; font-size: 16px; transition: border-color 0.3s; }
            .form-group input:focus, .form-group textarea:focus, .form-group select:focus { outline: none; border-color: #3498db; }
            .form-group textarea { resize: vertical; min-height: 100px; }
            .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
            .form-actions { display: flex; gap: 1rem; justify-content: flex-end; margin-top: 1.5rem; }
            .table-container { background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .data-table { width: 100%; border-collapse: collapse; }
            .data-table th, .data-table td { padding: 1rem; text-align: right; border-bottom: 1px solid #e0e0e0; }
            .data-table th { background: #f8f9fa; font-weight: bold; color: #2c3e50; }
            .data-table tr:hover { background: #f8f9fa; }
            .campaigns-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; }
            .campaign-card { background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); border-left: 4px solid #3498db; }
            .campaign-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
            .campaign-badge { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: bold; color: white; }
            .campaign-badge.easy { background: #27ae60; }
            .campaign-badge.medium { background: #f39c12; }
            .campaign-badge.hard { background: #e74c3c; }
            .campaign-meta { display: flex; gap: 1rem; margin: 1rem 0; font-size: 0.9rem; color: #7f8c8d; }
            .campaign-actions { display: flex; gap: 0.5rem; }
            .campaign-actions .btn { padding: 0.5rem 1rem; font-size: 0.9rem; }
            .tab-container { margin-bottom: 2rem; }
            .tab-buttons { display: flex; background: #f8f9fa; border-radius: 10px; padding: 0.5rem; margin-bottom: 1rem; }
            .tab-btn { padding: 0.75rem 1.5rem; border: none; background: none; cursor: pointer; border-radius: 8px; transition: all 0.3s; font-weight: 500; }
            .tab-btn.active { background: #3498db; color: white; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            .filter-bar { background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
            .filter-select { padding: 0.5rem; border: 1px solid #e0e0e0; border-radius: 5px; background: white; }
            .status-badge { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
            .status-badge.click { background: #e74c3c; color: white; }
            .status-badge.awareness { background: #27ae60; color: white; }
            .status-badge.report { background: #3498db; color: white; }
            .status-badge.ignore { background: #95a5a6; color: white; }
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <div class="nav-logo">
                    <h1>📊 لوحة التحكم</h1>
                </div>
                <ul class="nav-menu">
                    <li><a href="/">الرئيسية</a></li>
                    <li><a href="/dashboard" class="active">لوحة التحكم</a></li>
                    <li><a href="/training">التدريب</a></li>
                </ul>
            </div>
        </nav>

        <main class="main-content">
            <!-- الإحصائيات السريعة -->
            <section class="dashboard-section">
                <h2>نظرة عامة على النظام</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number" id="dashTotalUsers">0</div>
                        <div class="stat-label">المستخدمين</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="dashTotalCampaigns">0</div>
                        <div class="stat-label">الحملات</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="dashTotalResponses">0</div>
                        <div class="stat-label">التفاعلات</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="dashSuccessRate">0%</div>
                        <div class="stat-label">معدل النجاح</div>
                    </div>
                </div>
            </section>

            <!-- نظام التبويب الجديد -->
            <section class="dashboard-section">
                <div class="tab-container">
                    <div class="tab-buttons">
                        <button class="tab-btn active" onclick="openTab('usersTab')">👥 إدارة المستخدمين</button>
                        <button class="tab-btn" onclick="openTab('campaignsTab')">📧 إدارة الحملات</button>
                        <button class="tab-btn" onclick="openTab('accessTab')">🌐 الوصول الخارجي</button>
                        <button class="tab-btn" onclick="openTab('visitorsTab')">📊 متابعة الزوار</button>
                    </div>

                    <!-- تبويب متابعة الزوار الجديد -->
                    <div id="visitorsTab" class="tab-content active">
                        <div class="section-header">
                            <h3>📊 متابعة الزوار والتفاعلات</h3>
                            <div>
                                <select class="filter-select" id="campaignFilter" onchange="loadVisitors()">
                                    <option value="">جميع الحملات</option>
                                </select>
                                <select class="filter-select" id="typeFilter" onchange="loadVisitors()">
                                    <option value="">جميع الأنواع</option>
                                    <option value="click">نقر على الرابط</option>
                                    <option value="awareness_view">مشاهدة التوعية</option>
                                    <option value="report">الإبلاغ</option>
                                    <option value="ignore">تجاهل</option>
                                </select>
                            </div>
                        </div>

                        <div class="filter-bar">
                            <div>
                                <label>من:</label>
                                <input type="date" id="dateFrom" class="filter-select" onchange="loadVisitors()">
                            </div>
                            <div>
                                <label>إلى:</label>
                                <input type="date" id="dateTo" class="filter-select" onchange="loadVisitors()">
                            </div>
                            <button class="btn btn-secondary" onclick="exportVisitors()">📥 تصدير البيانات</button>
                        </div>

                        <div class="table-container">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>المستخدم</th>
                                        <th>البريد الإلكتروني</th>
                                        <th>الحملة</th>
                                        <th>نوع التفاعل</th>
                                        <th>وقت الاستجابة</th>
                                        <th>عنوان IP</th>
                                        <th>التاريخ</th>
                                    </tr>
                                </thead>
                                <tbody id="visitorsTableBody">
                                    <!-- سيتم ملؤها بالبيانات -->
                                </tbody>
                            </table>
                        </div>

                        <div style="margin-top: 1rem; text-align: center;">
                            <button class="btn btn-secondary" onclick="loadMoreVisitors()" id="loadMoreBtn">تحميل المزيد</button>
                        </div>
                    </div>

                    <!-- تبويب إدارة المستخدمين -->
                    <div id="usersTab" class="tab-content">
                        <div class="section-header">
                            <h3>👥 إدارة المستخدمين</h3>
                            <button class="btn btn-primary" onclick="showAddUserForm()">إضافة مستخدم</button>
                        </div>

                        <div class="section-content">
                            <div class="form-container" id="addUserForm" style="display: none;">
                                <form id="userForm" class="form">
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label for="userEmail">البريد الإلكتروني *</label>
                                            <input type="email" id="userEmail" required>
                                        </div>
                                        <div class="form-group">
                                            <label for="userName">الاسم</label>
                                            <input type="text" id="userName">
                                        </div>
                                    </div>
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label for="userDepartment">القسم/الكلية</label>
                                            <input type="text" id="userDepartment">
                                        </div>
                                        <div class="form-group">
                                            <label for="userType">نوع المستخدم</label>
                                            <select id="userType">
                                                <option value="student">طالب</option>
                                                <option value="employee">موظف</option>
                                                <option value="admin">مدير</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="form-actions">
                                        <button type="submit" class="btn btn-primary">إضافة المستخدم</button>
                                        <button type="button" class="btn btn-secondary" onclick="hideAddUserForm()">إلغاء</button>
                                    </div>
                                </form>
                            </div>

                            <div class="table-container">
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th>البريد الإلكتروني</th>
                                            <th>الاسم</th>
                                            <th>القسم</th>
                                            <th>النوع</th>
                                            <th>تاريخ التسجيل</th>
                                        </tr>
                                    </thead>
                                    <tbody id="usersTableBody">
                                        <!-- سيتم ملؤها بالبيانات -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- تبويب إدارة الحملات -->
                    <div id="campaignsTab" class="tab-content">
                        <div class="section-header">
                            <h3>📧 إدارة الحملات التدريبية</h3>
                            <button class="btn btn-primary" onclick="showAddCampaignForm()">إنشاء حملة</button>
                        </div>

                        <div class="section-content">
                            <div class="form-container" id="addCampaignForm" style="display: none;">
                                <form id="campaignForm" class="form">
                                    <div class="form-group">
                                        <label for="campaignName">اسم الحملة *</label>
                                        <input type="text" id="campaignName" required>
                                    </div>
                                    <div class="form-group">
                                        <label for="campaignDescription">وصف الحملة</label>
                                        <textarea id="campaignDescription" rows="3"></textarea>
                                    </div>
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label for="phishingType">نوع التصيد</label>
                                            <select id="phishingType">
                                                <option value="email">بريد إلكتروني</option>
                                                <option value="sms">رسالة نصية</option>
                                            </select>
                                        </div>
                                        <div class="form-group">
                                            <label for="difficultyLevel">مستوى الصعوبة</label>
                                            <select id="difficultyLevel">
                                                <option value="easy">سهل</option>
                                                <option value="medium">متوسط</option>
                                                <option value="hard">صعب</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="form-group">
                                        <label for="emailSubject">موضوع البريد الإلكتروني *</label>
                                        <input type="text" id="emailSubject" required>
                                    </div>
                                    <div class="form-group">
                                        <label for="emailContent">محتويات البريد الإلكتروني *</label>
                                        <textarea id="emailContent" rows="6" required></textarea>
                                        <small>استخدم {tracking_url} كعنصر نائب لرابط التتبع</small>
                                    </div>
                                    <div class="form-actions">
                                        <button type="submit" class="btn btn-primary">إنشاء الحملة</button>
                                        <button type="button" class="btn btn-secondary" onclick="hideAddCampaignForm()">إلغاء</button>
                                    </div>
                                </form>
                            </div>

                            <div class="campaigns-grid" id="campaignsGrid">
                                <!-- سيتم ملؤها بالبيانات -->
                            </div>
                        </div>
                    </div>

                    <!-- تبويب الوصول الخارجي -->
                    <div id="accessTab" class="tab-content">
                        <div class="section-header">
                            <h3>🌐 إدارة الوصول الخارجي</h3>
                            <button class="btn btn-primary" onclick="showCreateAccessForm()">إنشاء رابط وصول</button>
                        </div>

                        <div class="section-content">
                            <div class="form-container" id="createAccessForm" style="display: none;">
                                <form id="accessForm" class="form">
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label for="accessUser">المستخدم (اختياري)</label>
                                            <select id="accessUser">
                                                <option value="">اختيار مستخدم</option>
                                            </select>
                                        </div>
                                        <div class="form-group">
                                            <label for="accessCampaign">الحملة (اختياري)</label>
                                            <select id="accessCampaign">
                                                <option value="">اختيار حملة</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label for="validDays">مدة الصلاحية (أيام)</label>
                                            <input type="number" id="validDays" value="30" min="1" max="365">
                                        </div>
                                        <div class="form-group">
                                            <label for="maxUses">الحد الأقصى للاستخدام</label>
                                            <input type="number" id="maxUses" value="1" min="1" max="100">
                                        </div>
                                    </div>
                                    <div class="form-actions">
                                        <button type="submit" class="btn btn-primary">إنشاء الرابط</button>
                                        <button type="button" class="btn btn-secondary" onclick="hideCreateAccessForm()">إلغاء</button>
                                    </div>
                                </form>
                            </div>

                            <div id="accessResult" style="display: none;" class="form">
                                <h4>✅ تم إنشاء رابط الوصول</h4>
                                <div class="form-group">
                                    <label>رابط الوصول:</label>
                                    <input type="text" id="generatedLink" readonly style="background: #f8f9fa;">
                                    <button class="btn" onclick="copyLink()" style="margin-top: 10px;">نسخ الرابط</button>
                                </div>
                                <div class="form-group">
                                    <label>معلومات الرابط:</label>
                                    <div id="linkInfo" style="background: #f8f9fa; padding: 10px; border-radius: 5px;"></div>
                                </div>
                            </div>

                            <div class="table-container">
                                <h4>روابط الوصول النشطة</h4>
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th>رمز الوصول</th>
                                            <th>الحملة</th>
                                            <th>تاريخ الانتهاء</th>
                                            <th>عدد الاستخدامات</th>
                                            <th>الحالة</th>
                                        </tr>
                                    </thead>
                                    <tbody id="accessTableBody">
                                        <!-- سيتم ملؤها بالبيانات -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </main>

        <script>
            // متغيرات التبويب
            let currentTab = 'visitorsTab';
            let visitorsPage = 1;
            let hasMoreVisitors = true;

            // دوال إدارة التبويب
            function openTab(tabName) {
                // إخفاء جميع المحتويات
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // إلغاء تنشيط جميع الأزرار
                document.querySelectorAll('.tab-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // إظهار المحتوى المطلوب
                document.getElementById(tabName).classList.add('active');
                
                // تنشيط الزر المطلوب
                event.currentTarget.classList.add('active');
                
                currentTab = tabName;
                
                // تحميل البيانات عند التبديل
                if (tabName === 'visitorsTab') {
                    loadVisitors();
                    loadCampaignsFilter();
                } else if (tabName === 'usersTab') {
                    loadUsers();
                } else if (tabName === 'campaignsTab') {
                    loadCampaigns();
                } else if (tabName === 'accessTab') {
                    loadAccessLinks();
                }
            }

            // دوال إدارة النماذج
            function showAddUserForm() {
                document.getElementById('addUserForm').style.display = 'block';
            }

            function hideAddUserForm() {
                document.getElementById('addUserForm').style.display = 'none';
                document.getElementById('userForm').reset();
            }

            function showAddCampaignForm() {
                document.getElementById('addCampaignForm').style.display = 'block';
            }

            function hideAddCampaignForm() {
                document.getElementById('addCampaignForm').style.display = 'none';
                document.getElementById('campaignForm').reset();
            }

            // دوال إدارة الوصول الخارجي
            function showCreateAccessForm() {
                document.getElementById('createAccessForm').style.display = 'block';
                loadUsersAndCampaigns();
            }

            function hideCreateAccessForm() {
                document.getElementById('createAccessForm').style.display = 'none';
                document.getElementById('accessForm').reset();
                document.getElementById('accessResult').style.display = 'none';
            }

            // تحميل الإحصائيات
            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    const stats = await response.json();

                    document.getElementById('dashTotalUsers').textContent = stats.total_users;
                    document.getElementById('dashTotalCampaigns').textContent = stats.total_campaigns;
                    document.getElementById('dashTotalResponses').textContent = stats.total_responses;
                    document.getElementById('dashSuccessRate').textContent = stats.success_rate + '%';
                } catch (error) {
                    console.error('Error loading stats:', error);
                }
            }

            // تحميل المستخدمين
            async function loadUsers() {
                try {
                    const response = await fetch('/api/users');
                    const users = await response.json();

                    const usersTable = document.getElementById('usersTableBody');
                    usersTable.innerHTML = users.map(user => `
                        <tr>
                            <td>${user.email}</td>
                            <td>${user.name || '-'}</td>
                            <td>${user.department || '-'}</td>
                            <td>${user.user_type}</td>
                            <td>${new Date(user.registration_date).toLocaleDateString('ar-EG')}</td>
                        </tr>
                    `).join('');
                } catch (error) {
                    console.error('Error loading users:', error);
                }
            }

            // تحميل الحملات
            async function loadCampaigns() {
                try {
                    const response = await fetch('/api/campaigns');
                    const campaigns = await response.json();

                    const campaignsGrid = document.getElementById('campaignsGrid');
                    campaignsGrid.innerHTML = campaigns.map(campaign => `
                        <div class="campaign-card">
                            <div class="campaign-header">
                                <h4>${campaign.name}</h4>
                                <span class="campaign-badge ${campaign.difficulty_level}">${getDifficultyText(campaign.difficulty_level)}</span>
                            </div>
                            <p>${campaign.description || 'لا يوجد وصف'}</p>
                            <div class="campaign-meta">
                                <span>📧 ${campaign.phishing_type}</span>
                                <span>📋 ${campaign.email_subject}</span>
                            </div>
                            <div class="campaign-actions">
                                <button class="btn btn-primary" onclick="sendCampaign(${campaign.id})">إرسال الحملة</button>
                                <button class="btn btn-secondary" onclick="testCampaign(${campaign.id})">اختبار</button>
                            </div>
                        </div>
                    `).join('');
                } catch (error) {
                    console.error('Error loading campaigns:', error);
                }
            }

            // دوال المساعدة
            function getDifficultyText(level) {
                const levels = {
                    'easy': 'سهل',
                    'medium': 'متوسط',
                    'hard': 'صعب'
                };
                return levels[level] || level;
            }

            function getInteractionTypeText(type) {
                const types = {
                    'click': 'نقر على الرابط',
                    'awareness_view': 'مشاهدة التوعية',
                    'report': 'الإبلاغ',
                    'ignore': 'تجاهل',
                    'phishing_alert_view': 'مشاهدة التنبيه'
                };
                return types[type] || type;
            }

            function getStatusBadge(type) {
                const badges = {
                    'click': 'status-badge click',
                    'awareness_view': 'status-badge awareness',
                    'report': 'status-badge report',
                    'ignore': 'status-badge ignore',
                    'phishing_alert_view': 'status-badge awareness'
                };
                return badges[type] || 'status-badge ignore';
            }

            // إرسال حملة
            async function sendCampaign(campaignId) {
                if (!confirm('هل تريد إرسال هذه الحملة لجميع المستخدمين؟')) {
                    return;
                }

                try {
                    const response = await fetch(`/api/send-campaign/${campaignId}`, {
                        method: 'POST'
                    });

                    const result = await response.json();
                    alert(`✅ ${result.message}`);
                    loadStats();
                } catch (error) {
                    console.error('Error sending campaign:', error);
                    alert('❌ خطأ في إرسال الحملة');
                }
            }

            // اختبار حملة
            function testCampaign(campaignId) {
                window.open(`/simulate/${campaignId}?user=1`, '_blank');
            }

            // إضافة مستخدم
            document.getElementById('userForm').addEventListener('submit', async function(e) {
                e.preventDefault();

                const formData = {
                    email: document.getElementById('userEmail').value,
                    name: document.getElementById('userName').value,
                    department: document.getElementById('userDepartment').value,
                    user_type: document.getElementById('userType').value
                };

                try {
                    const response = await fetch('/api/users', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    });

                    const result = await response.json();

                    if (response.ok) {
                        alert('تم إضافة المستخدم بنجاح');
                        hideAddUserForm();
                        loadUsers();
                        loadStats();
                    } else {
                        alert('خطأ: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error adding user:', error);
                    alert('خطأ في إضافة المستخدم');
                }
            });

            // إضافة حملة
            document.getElementById('campaignForm').addEventListener('submit', async function(e) {
                e.preventDefault();

                const formData = {
                    name: document.getElementById('campaignName').value,
                    description: document.getElementById('campaignDescription').value,
                    phishing_type: document.getElementById('phishingType').value,
                    difficulty_level: document.getElementById('difficultyLevel').value,
                    email_subject: document.getElementById('emailSubject').value,
                    email_content: document.getElementById('emailContent').value
                };

                try {
                    const response = await fetch('/api/campaigns', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    });

                    const result = await response.json();

                    if (response.ok) {
                        alert('تم إنشاء الحملة بنجاح');
                        hideAddCampaignForm();
                        loadCampaigns();
                        loadStats();
                    } else {
                        alert('خطأ: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error adding campaign:', error);
                    alert('خطأ في إنشاء الحملة');
                }
            });

            // دوال الوصول الخارجي
            async function loadUsersAndCampaigns() {
                try {
                    const [usersResponse, campaignsResponse] = await Promise.all([
                        fetch('/api/users'),
                        fetch('/api/campaigns')
                    ]);

                    const users = await usersResponse.json();
                    const campaigns = await campaignsResponse.json();

                    const userSelect = document.getElementById('accessUser');
                    const campaignSelect = document.getElementById('accessCampaign');

                    userSelect.innerHTML = '<option value="">اختيار مستخدم</option>';
                    campaignSelect.innerHTML = '<option value="">اختيار حملة</option>';

                    users.forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.id;
                        option.textContent = `${user.name} (${user.email})`;
                        userSelect.appendChild(option);
                    });

                    campaigns.forEach(campaign => {
                        const option = document.createElement('option');
                        option.value = campaign.id;
                        option.textContent = campaign.name;
                        campaignSelect.appendChild(option);
                    });
                } catch (error) {
                    console.error('Error loading data:', error);
                }
            }

            // إنشاء رابط وصول
            document.getElementById('accessForm').addEventListener('submit', async function(e) {
                e.preventDefault();

                const formData = {
                    user_id: document.getElementById('accessUser').value || null,
                    campaign_id: document.getElementById('accessCampaign').value || null,
                    valid_days: parseInt(document.getElementById('validDays').value),
                    max_uses: parseInt(document.getElementById('maxUses').value)
                };

                try {
                    const response = await fetch('/api/external/access', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    });

                    const result = await response.json();

                    if (response.ok) {
                        document.getElementById('createAccessForm').style.display = 'none';
                        document.getElementById('accessResult').style.display = 'block';
                        document.getElementById('generatedLink').value = result.external_url;
                        document.getElementById('linkInfo').innerHTML = `
                            <strong>رمز الوصول:</strong> ${result.access_code}<br>
                            <strong>تاريخ الانتهاء:</strong> ${result.expiry_date}<br>
                            <strong>الرابط الأساسي:</strong> ${result.base_url}
                        `;
                        loadAccessLinks();
                    } else {
                        alert('خطأ: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error creating access:', error);
                    alert('خطأ في إنشاء رابط الوصول');
                }
            });

            function copyLink() {
                const linkInput = document.getElementById('generatedLink');
                linkInput.select();
                document.execCommand('copy');
                alert('تم نسخ الرابط إلى الحافظة');
            }

            async function loadAccessLinks() {
                try {
                    const response = await fetch('/api/external/access-list');
                    const accessLinks = await response.json();
                    
                    const accessTable = document.getElementById('accessTableBody');
                    accessTable.innerHTML = accessLinks.map(access => `
                        <tr>
                            <td>${access.access_code}</td>
                            <td>${access.campaign_name || 'جميع الحملات'}</td>
                            <td>${new Date(access.expiry_date).toLocaleDateString('ar-EG')}</td>
                            <td>${access.used_count}/${access.max_uses}</td>
                            <td>${access.is_active ? 'نشط' : 'غير نشط'}</td>
                        </tr>
                    `).join('');
                } catch (error) {
                    console.error('Error loading access links:', error);
                }
            }

            // دوال متابعة الزوار الجديدة
            async function loadCampaignsFilter() {
                try {
                    const response = await fetch('/api/campaigns');
                    const campaigns = await response.json();
                    
                    const campaignFilter = document.getElementById('campaignFilter');
                    campaignFilter.innerHTML = '<option value="">جميع الحملات</option>';
                    
                    campaigns.forEach(campaign => {
                        const option = document.createElement('option');
                        option.value = campaign.id;
                        option.textContent = campaign.name;
                        campaignFilter.appendChild(option);
                    });
                } catch (error) {
                    console.error('Error loading campaigns filter:', error);
                }
            }

            async function loadVisitors(resetPage = true) {
                if (resetPage) {
                    visitorsPage = 1;
                    hasMoreVisitors = true;
                }

                try {
                    const campaignId = document.getElementById('campaignFilter').value;
                    const interactionType = document.getElementById('typeFilter').value;
                    const dateFrom = document.getElementById('dateFrom').value;
                    const dateTo = document.getElementById('dateTo').value;

                    let url = `/api/user-responses?page=${visitorsPage}`;
                    if (campaignId) url += `&campaign_id=${campaignId}`;
                    if (interactionType) url += `&interaction_type=${interactionType}`;
                    if (dateFrom) url += `&date_from=${dateFrom}`;
                    if (dateTo) url += `&date_to=${dateTo}`;

                    const response = await fetch(url);
                    const visitors = await response.json();

                    const visitorsTable = document.getElementById('visitorsTableBody');
                    
                    if (resetPage) {
                        visitorsTable.innerHTML = '';
                    }

                    if (visitors.length === 0) {
                        if (visitorsPage === 1) {
                            visitorsTable.innerHTML = '<tr><td colspan="7" style="text-align: center;">لا توجد بيانات</td></tr>';
                        }
                        hasMoreVisitors = false;
                        document.getElementById('loadMoreBtn').style.display = 'none';
                    } else {
                        visitorsTable.innerHTML += visitors.map(visitor => `
                            <tr>
                                <td>${visitor.name || visitor.email || 'زائر خارجي'}</td>
                                <td>${visitor.email || '-'}</td>
                                <td>${visitor.campaign_name || 'تدريب عام'}</td>
                                <td><span class="${getStatusBadge(visitor.interaction_type)}">${getInteractionTypeText(visitor.interaction_type)}</span></td>
                                <td>${visitor.response_time ? visitor.response_time + ' ثانية' : '-'}</td>
                                <td>${visitor.ip_address || '-'}</td>
                                <td>${new Date(visitor.interaction_date).toLocaleString('ar-EG')}</td>
                            </tr>
                        `).join('');

                        document.getElementById('loadMoreBtn').style.display = 'block';
                    }
                } catch (error) {
                    console.error('Error loading visitors:', error);
                }
            }

            async function loadMoreVisitors() {
                visitorsPage++;
                await loadVisitors(false);
            }

            function exportVisitors() {
                const campaignId = document.getElementById('campaignFilter').value;
                const interactionType = document.getElementById('typeFilter').value;
                const dateFrom = document.getElementById('dateFrom').value;
                const dateTo = document.getElementById('dateTo').value;

                let url = `/api/export-visitors`;
                let params = [];
                if (campaignId) params.push(`campaign_id=${campaignId}`);
                if (interactionType) params.push(`interaction_type=${interactionType}`);
                if (dateFrom) params.push(`date_from=${dateFrom}`);
                if (dateTo) params.push(`date_to=${dateTo}`);

                if (params.length > 0) {
                    url += '?' + params.join('&');
                }

                window.open(url, '_blank');
            }

            // التحميل الأولي
            loadStats();
            loadUsers();
            loadCampaigns();
            loadAccessLinks();
            loadVisitors();
            loadCampaignsFilter();
        </script>
    </body>
    </html>
    '''
