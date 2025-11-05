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

            <!-- إدارة المستخدمين -->
            <section class="dashboard-section">
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
            </section>

            <!-- إدارة الحملات -->
            <section class="dashboard-section">
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
            </section>

            <!-- قسم الوصول الخارجي الجديد -->
            <section class="dashboard-section">
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
            </section>
        </main>

        <script>
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

            // التحميل الأولي
            loadStats();
            loadUsers();
            loadCampaigns();
            loadAccessLinks();
        </script>
    </body>
    </html>
    '''

@app.route('/training')
def training():
    return '''
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>مركز التدريب - نظام التوعية بالتصيد</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            body { background: #f5f6fa; min-height: 100vh; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 40px; padding: 20px; background: #2c3e50; color: white; border-radius: 10px; }
            .nav { background: #34495e; padding: 15px; border-radius: 5px; margin-bottom: 30px; text-align: center; }
            .nav a { color: white; text-decoration: none; padding: 10px 20px; margin: 0 10px; display: inline-block; }
            .training-card { background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #3498db; cursor: pointer; transition: transform 0.3s; }
            .training-card:hover { transform: translateY(-5px); }
            .btn { background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px; border: none; cursor: pointer; }
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
            .modal-content { background: white; margin: 5% auto; padding: 30px; border-radius: 10px; width: 80%; max-width: 800px; max-height: 80vh; overflow-y: auto; }
            .close { float: left; font-size: 28px; font-weight: bold; cursor: pointer; }
            .quiz-question { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }
            .quiz-option { margin: 10px 0; padding: 10px; background: white; border: 1px solid #ddd; border-radius: 5px; cursor: pointer; }
            .quiz-option:hover { background: #e3f2fd; }
            .correct { background: #d4edda !important; border-color: #c3e6cb !important; }
            .wrong { background: #f8d7da !important; border-color: #f5c6cb !important; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 مركز التدريب</h1>
                <p>طور مهاراتك في التعرف على هجمات التصيد</p>
            </div>
            
            <div class="nav">
                <a href="/">الرئيسية</a>
              
                <a href="/training" style="background: #2c3e50; border-radius: 5px;">التدريب</a>
            </div>

            <!-- المواد التدريبية -->
            <div class="training-card" onclick="openTraining(1)">
                <h3>📚 المادة 1: مقدمة في هجمات التصيد</h3>
                <p>تعرف على أساسيات هجمات التصيد وأنواعها وأهدافها</p>
                <button class="btn">بدء التعلم</button>
            </div>
            
            <div class="training-card" onclick="openTraining(2)">
                <h3>🔍 المادة 2: كيفية التعرف على رسائل التصيد</h3>
                <p>تعلم العلامات الدالة على رسائل التصيد المشبوهة</p>
                <button class="btn">بدء التعلم</button>
            </div>
            
            <div class="training-card" onclick="openTraining(3)">
                <h3>🛡️ المادة 3: أساليب الوقاية من التصيد</h3>
                <p>استراتيجيات فعالة لحماية نفسك من هجمات التصيد</p>
                <button class="btn">بدء التعلم</button>
            </div>

            <!-- اختبار تفاعلي -->
            <div class="training-card" onclick="startQuiz()">
                <h3>🧪 اختبار التوعية التفاعلي</h3>
                <p>اختبر معرفتك بالتصيد من خلال اختبار عملي</p>
                <button class="btn">بدء الاختبار</button>
            </div>
        </div>

        <!-- نافذة المحتوى التدريبي -->
        <div id="trainingModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeTraining()">&times;</span>
                <div id="trainingContent"></div>
            </div>
        </div>

        <!-- نافذة الاختبار -->
        <div id="quizModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeQuiz()">&times;</span>
                <div id="quizContent"></div>
            </div>
        </div>

        <script>
            // المحتوى التدريبي
            const trainingMaterials = {
                1: {
                    title: "📚 مقدمة في هجمات التصيد",
                    content: `
                        <h2>ما هو التصيد (Phishing)؟</h2>
                        <p>التصيد هو نوع من الهجمات الإلكترونية حيث يحاول المهاجمون خداعك لإعطائهم معلوماتك الشخصية الحساسة.</p>
                        
                        <h3>🎯 أهداف هجمات التصيد:</h3>
                        <ul>
                            <li>كلمات المرور</li>
                            <li>أرقام البطاقات الائتمانية</li>
                            <li>المعلومات البنكية</li>
                            <li>بيانات الحسابات المهمة</li>
                            <li>المعلومات الشخصية</li>
                        </ul>

                        <h3>📧 أنواع التصيد الشائعة:</h3>
                        <ul>
                            <li><strong>تصيد البريد الإلكتروني:</strong> رسائل بريدية مزورة</li>
                            <li><strong>تصيد الرسائل النصية:</strong> رسائل SMS احتيالية</li>
                            <li><strong>تصيد وسائل التواصل:</strong> رسائل عبر منصات التواصل</li>
                            <li><strong>التصيد المستهدف:</strong> هجمات موجهة لأفراد محددين</li>
                        </ul>

                        <div style="text-align: center; margin-top: 30px;">
                            <button class="btn" onclick="closeTraining()">تمت الدراسة</button>
                        </div>
                    `
                },
                2: {
                    title: "🔍 كيفية التعرف على رسائل التصيد",
                    content: `
                        <h2>علامات التحذير من رسائل التصيد</h2>
                        
                        <h3>📨 علامات في البريد الإلكتروني:</h3>
                        <ul>
                            <li>⏰ <strong>التعجيل والتهديد:</strong> "يجب عليك التصرف الآن!"</li>
                            <li>📧 <strong>عنوان المرسل مشبوه:</strong> مثل support@university-security.com</li>
                            <li>🔗 <strong>روابط مختصرة أو غريبة:</strong> bit.ly أو روابط غير مألوفة</li>
                            <li>✍️ <strong>أخطاء إملائية ونحوية:</strong> علامة على عدم الاحترافية</li>
                            <li>🎁 <strong>عروض مغرية:</strong> "ربح جائزة قيمة!"</li>
                        </ul>

                        <h3>🌐 علامات في صفحات الويب:</h3>
                        <ul>
                            <li>🔒 <strong>غياب قفل الأمان (HTTPS)</strong></li>
                            <li>🌍 <strong>عنوان URL غير صحيح:</strong> مثل faceb00k.com</li>
                            <li>🎨 <strong>تصميم غير احترافي:</strong> ألوان وتصميم غريب</li>
                            <li>📝 <strong>نماذج طلب بيانات حساسة:</strong> طلب كلمات مرور أو معلومات بنكية</li>
                        </ul>

                        <h3>💡 مثال عملي:</h3>
                        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border: 1px solid #ffeaa7;">
                            <p><strong>بريد مشبوه:</strong> "عزيزي العميل، حسابك معرض للإغلاق. انقر هنا لتأكيد بياناتك."</p>
                            <p><strong>لماذا هو مشبوه؟</strong> التهديد، طلب بيانات، رابط غير موثوق</p>
                        </div>

                        <div style="text-align: center; margin-top: 30px;">
                            <button class="btn" onclick="closeTraining()">تمت الدراسة</button>
                        </div>
                    `
                },
                3: {
                    title: "🛡️ أساليب الوقاية من التصيد",
                    content: `
                        <h2>كيف تحمي نفسك من هجمات التصيد</h2>
                        
                        <h3>✅ إجراءات وقائية أساسية:</h3>
                        <ul>
                            <li>🔍 <strong>افحص عنوان البريد المرسل:</strong> تأكد من أنه رسمي</li>
                            <li>🖱️ <strong>لا تنقر على الروابط مباشرة:</strong> اكتب العنوان بنفسك</li>
                            <li>🔒 <strong>استخدم المصادقة الثنائية:</strong> حماية إضافية لحساباتك</li>
                            <li>📞 <strong>اتصل بالمصدر للتأكد:</strong> لا تثق بالبريد فقط</li>
                            <li>🔄 <strong>حدث برامجك باستمرار:</strong> تصحيحات أمنية مهمة</li>
                        </ul>

                        <h3>🚨 ماذا تفعل إذا شككت في بريد؟</h3>
                        <ol>
                            <li>❌ لا ترد على البريد</li>
                            <li>🔗 لا تنقر على أي روابط</li>
                            <li>📎 لا تفتح أي مرفقات</li>
                            <li>📞 اتصل بالدعم الفني للتأكد</li>
                            <li>🗑️ احذف البريد المشبوه</li>
                        </ol>

                        <h3>🛠️ أدوات مساعدة:</h3>
                        <ul>
                            <li>مرشحات البريد العشوائي</li>
                            <li>برامج مكافحة الفيروسات</li>
                            <li>متصفحات ذات حماية من التصيد</li>
                            <li>إدارة كلمات المرور</li>
                        </ul>

                        <div style="text-align: center; margin-top: 30px;">
                            <button class="btn" onclick="closeTraining()">تمت الدراسة</button>
                        </div>
                    `
                }
            };

            // الأسئلة التفاعلية
            const quizQuestions = [
                {
                    question: "أي من هذه يعتبر علامة على بريد تصيد؟",
                    options: [
                        "أخطاء إملائية ونحوية",
                        "التعجيل والتهديد في الطلب",
                        "عنوان مرسل مشبوه",
                        "جميع ما سبق"
                    ],
                    correct: 3
                },
                {
                    question: "ماذا يجب أن تفعل إذا تلقيت بريداً يطلب تحديث كلمة المرور؟",
                    options: [
                        "النقر على الرابط وتحديث كلمة المرور فوراً",
                        "الاتصال بالدعم الفني للتأكد أولاً",
                        "إعادة إرسال البريد لأصدقائك",
                        "تجاهل البريد تماماً"
                    ],
                    correct: 1
                },
                {
                    question: "أي من هذه العناوين يبدو مشبوهاً؟",
                    options: [
                        "support@university.edu",
                        "security@university-official.com",
                        "admin@it-department.org",
                        "help@university-security-update.com"
                    ],
                    correct: 3
                }
            ];

            let currentQuestion = 0;
            let score = 0;

            function openTraining(materialId) {
                const material = trainingMaterials[materialId];
                document.getElementById('trainingContent').innerHTML = `
                    <h2>${material.title}</h2>
                    ${material.content}
                `;
                document.getElementById('trainingModal').style.display = 'block';
            }

            function closeTraining() {
                document.getElementById('trainingModal').style.display = 'none';
            }

            function startQuiz() {
                currentQuestion = 0;
                score = 0;
                showQuestion();
                document.getElementById('quizModal').style.display = 'block';
            }

            function closeQuiz() {
                document.getElementById('quizModal').style.display = 'none';
            }

            function showQuestion() {
                if (currentQuestion >= quizQuestions.length) {
                    showResults();
                    return;
                }

                const question = quizQuestions[currentQuestion];
                let optionsHtml = '';
                
                question.options.forEach((option, index) => {
                    optionsHtml += `
                        <div class="quiz-option" onclick="selectAnswer(${index})">
                            ${option}
                        </div>
                    `;
                });

                document.getElementById('quizContent').innerHTML = `
                    <h2>🧪 اختبار التوعية بالتصيد</h2>
                    <div class="quiz-question">
                        <h3>سؤال ${currentQuestion + 1} من ${quizQuestions.length}:</h3>
                        <p>${question.question}</p>
                        ${optionsHtml}
                    </div>
                    <div style="text-align: center; margin-top: 20px;">
                        <button class="btn" onclick="nextQuestion()" style="display: none;" id="nextBtn">التالي</button>
                    </div>
                `;
            }

            function selectAnswer(selectedIndex) {
                const question = quizQuestions[currentQuestion];
                const options = document.querySelectorAll('.quiz-option');
                
                options.forEach((option, index) => {
                    if (index === question.correct) {
                        option.classList.add('correct');
                    } else if (index === selectedIndex && index !== question.correct) {
                        option.classList.add('wrong');
                    }
                    option.style.pointerEvents = 'none';
                });

                if (selectedIndex === question.correct) {
                    score++;
                }

                document.getElementById('nextBtn').style.display = 'inline-block';
            }

            function nextQuestion() {
                currentQuestion++;
                showQuestion();
            }

            function showResults() {
                const percentage = Math.round((score / quizQuestions.length) * 100);
                let message = '';
                let emoji = '🎉';

                if (percentage >= 80) {
                    message = 'ممتاز! أنت على دراية جيدة بمخاطر التصيد.';
                    emoji = '🏆';
                } else if (percentage >= 60) {
                    message = 'جيد جداً! لديك معرفة أساسية جيدة.';
                    emoji = '✅';
                } else {
                    message = 'احرص على دراسة المواد التدريبية لتحسين معرفتك.';
                    emoji = '📚';
                }

                document.getElementById('quizContent').innerHTML = `
                    <h2>${emoji} نتائج الاختبار</h2>
                    <div style="text-align: center; padding: 30px;">
                        <h3>درجتك: ${score} من ${quizQuestions.length}</h3>
                        <h3>النسبة: ${percentage}%</h3>
                        <p>${message}</p>
                        <button class="btn" onclick="closeQuiz()" style="margin: 10px;">إغلاق</button>
                        <button class="btn" onclick="startQuiz()" style="margin: 10px;">إعادة الاختبار</button>
                    </div>
                `;
            }

            // إغلاق النوافذ عند النقر خارج المحتوى
            window.onclick = function(event) {
                const trainingModal = document.getElementById('trainingModal');
                const quizModal = document.getElementById('quizModal');
                
                if (event.target === trainingModal) {
                    closeTraining();
                }
                if (event.target === quizModal) {
                    closeQuiz();
                }
            }
        </script>
    </body>
    </html>
    '''

@app.route('/simulate/<int:campaign_id>')
def simulate(campaign_id):
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>تسجيل الدخول - نظام الجامعة</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            
            .login-container {{
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 450px;
            }}
            
            .university-header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            
            .university-logo {{
                font-size: 2.5em;
                margin-bottom: 10px;
                color: #2c3e50;
            }}
            
            .university-header h1 {{
                color: #2c3e50;
                margin-bottom: 5px;
                font-size: 1.8em;
            }}
            
            .university-header p {{
                color: #7f8c8d;
                font-size: 1.1em;
            }}
            
            .login-form {{
                margin-top: 30px;
            }}
            
            .form-group {{
                margin-bottom: 20px;
            }}
            
            .form-group label {{
                display: block;
                margin-bottom: 8px;
                color: #2c3e50;
                font-weight: 600;
            }}
            
            .form-group input {{
                width: 100%;
                padding: 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }}
            
            .form-group input:focus {{
                outline: none;
                border-color: #3498db;
            }}
            
            .login-btn {{
                background: #3498db;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
                width: 100%;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }}
            
            .login-btn:hover {{
                background: #2980b9;
            }}
            
            .form-footer {{
                text-align: center;
                margin-top: 20px;
                color: #7f8c8d;
            }}
            
            .form-footer a {{
                color: #3498db;
                text-decoration: none;
            }}
            
            .security-notice {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                text-align: center;
                border-left: 4px solid #3498db;
            }}
            
            .training-alert {{
                display: none;
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                color: #856404;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
                text-align: center;
                animation: fadeIn 0.5s;
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; }}
                to {{ opacity: 1; }}
            }}
            
            .alert-btn {{
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 10px;
                font-size: 16px;
            }}
            
            .alert-btn:hover {{
                background: #219a52;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="university-header">
                <div class="university-logo">🎓</div>
                <h1>جامعة التكنولوجيا</h1>
                <p>نظام إدارة المعلومات الموحد</p>
            </div>
            
            <div class="security-notice">
                <strong>🔒 تنبيه أمني:</strong> يرجى تسجيل الدخول باستخدام بياناتك الجامعية
            </div>
            
            <form class="login-form" id="loginForm">
                <div class="form-group">
                    <label for="username">اسم المستخدم:</label>
                    <input type="text" id="username" placeholder="أدخل اسم المستخدم الجامعي" required>
                </div>
                
                <div class="form-group">
                    <label for="password">كلمة المرور:</label>
                    <input type="password" id="password" placeholder="أدخل كلمة المرور" required>
                </div>
                
                <button type="submit" class="login-btn">تسجيل الدخول</button>
            </form>
            
            <div class="form-footer">
                <a href="#">نسيت كلمة المرور؟</a> | 
                <a href="#">مساعدة</a>
            </div>
            
            <div class="training-alert" id="trainingAlert">
                <h3>🎯 تدريب على التوعية الأمنية</h3>
                <p>لقد قمت للتو بالتفاعل مع صفحة محاكاة لهجوم التصيد!</p>
                <p>في الواقع، كان هذا يمكن أن يكون هجوماً حقيقياً لسرقة معلوماتك.</p>
                <button class="alert-btn" onclick="redirectToAwareness()">تعلم كيفية الحماية</button>
            </div>
        </div>

        <script>
            const urlParams = new URLSearchParams(window.location.search);
            const campaignId = {campaign_id};
            const userId = urlParams.get('user') || '1';
            
            document.getElementById('loginForm').addEventListener('submit', function(e) {{
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                // تسجيل محاولة إدخال البيانات
                recordInteraction('data_entry', username, password);
                
                // إظهار رسالة التدريب بعد 2 ثانية
                setTimeout(() => {{
                    document.getElementById('trainingAlert').style.display = 'block';
                }}, 2000);
            }});
            
            function recordInteraction(type, username = '', password = '') {{
                const data = {{
                    user_id: userId,
                    campaign_id: campaignId,
                    interaction_type: type,
                    data_entered: username || password ? `username: ${{username}}, password: ${{password}}` : null,
                    response_time: Math.floor(Math.random() * 10) + 1
                }};
                
                fetch('/api/record-interaction', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify(data)
                }}).catch(error => console.error('Error recording interaction:', error));
            }}
            
            function redirectToAwareness() {{
                window.location.href = `/awareness/${{campaignId}}?user=${{userId}}&type=data_entry`;
            }}
            
            // تسجيل النقر عند تحميل الصفحة
            window.addEventListener('load', function() {{
                recordInteraction('page_view');
            }});
        </script>
    </body>
    </html>
    '''

@app.route('/awareness/<int:campaign_id>')
def awareness(campaign_id):
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>توعية - هجمات التصيد</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .awareness-container {{
                max-width: 900px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 25px 50px rgba(0,0,0,0.1);
            }}
            
            .awareness-header {{
                background: linear-gradient(135deg, #e74c3c, #c0392b);
                color: white;
                padding: 40px;
                text-align: center;
            }}
            
            .awareness-header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            
            .awareness-header p {{
                font-size: 1.2em;
                opacity: 0.9;
            }}
            
            .awareness-content {{
                padding: 40px;
            }}
            
            .alert-section {{
                background: #fff3cd;
                border: 2px solid #ffeaa7;
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 30px;
            }}
            
            .alert-section h2 {{
                color: #856404;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .analysis-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                margin: 40px 0;
            }}
            
            .analysis-card {{
                background: #f8f9fa;
                padding: 25px;
                border-radius: 10px;
                border-left: 4px solid;
            }}
            
            .analysis-card.bad {{
                border-left-color: #e74c3c;
                background: #fdedec;
            }}
            
            .analysis-card.good {{
                border-left-color: #27ae60;
                background: #f0f9f4;
            }}
            
            .analysis-card h4 {{
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .analysis-card ul {{
                list-style: none;
                padding: 0;
            }}
            
            .analysis-card li {{
                padding: 8px 0;
                border-bottom: 1px solid rgba(0,0,0,0.1);
            }}
            
            .stats-card {{
                background: #ecf0f1;
                padding: 25px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            
            .action-buttons {{
                display: flex;
                gap: 15px;
                justify-content: center;
                margin-top: 30px;
                flex-wrap: wrap;
            }}
            
            .btn {{
                display: inline-block;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                text-decoration: none;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                text-align: center;
            }}
            
            .btn-primary {{
                background: #3498db;
                color: white;
            }}
            
            .btn-primary:hover {{
                background: #2980b9;
            }}
            
            .btn-success {{
                background: #27ae60;
                color: white;
            }}
            
            .btn-success:hover {{
                background: #219a52;
            }}
            
            .btn-secondary {{
                background: #95a5a6;
                color: white;
            }}
            
            .btn-secondary:hover {{
                background: #7f8c8d;
            }}
            
            @media (max-width: 768px) {{
                .analysis-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .action-buttons {{
                    flex-direction: column;
                }}
                
                .btn {{
                    width: 100%;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="awareness-container">
            <div class="awareness-header">
                <h1>🎯 تدريب على التوعية بالتصيد</h1>
                <p>لقد تفاعلت مع محاكاة هجوم تصيد</p>
            </div>
            
            <div class="awareness-content">
                <div class="alert-section">
                    <h2>⚠️ تنبيه أمني مهم!</h2>
                    <p>لقد قمت للتو بالتفاعل مع صفحة محاكاة لهجوم التصيد. في الواقع، كان هذا يمكن أن يكون هجوماً حقيقياً!</p>
                </div>
                
                <h2>ماذا حدث؟</h2>
                <p>لقد تلقيت بريداً إلكترونياً يحاول خداعك لإدخال معلوماتك الشخصية في صفحة مزورة.</p>
                
                <div class="analysis-grid">
                    <div class="analysis-card bad">
                        <h4>❌ ما فعلته:</h4>
                        <ul>
                            <li>نقرت على رابط في بريد مشبوه</li>
                            <li>أدخلت بيانات في نموذج غير موثوق</li>
                            <li>لم تتأكد من صحة المصدر</li>
                            <li>شاركت معلومات حساسة محتملة</li>
                        </ul>
                    </div>
                    
                    <div class="analysis-card good">
                        <h4>✅ ما يجب فعله:</h4>
                        <ul>
                            <li>تحقق من عنوان البريد المرسل</li>
                            <li>افحص رابط URL قبل النقر</li>
                            <li>لا تدخل بيانات في صفحات غير موثوقة</li>
                            <li>اتصل بالدعم الفني للتأكد</li>
                            <li>استخدم المصادقة الثنائية</li>
                        </ul>
                    </div>
                </div>
                
                <div class="stats-card">
                    <h3>📊 إحصائيات أدائك:</h3>
                    <p>✅ لقد تعلمت كيفية التعرف على التصيد</p>
                    <p>🎯 هذه تجربة تعليمية قيمة لتحسين مهاراتك</p>
                    <p>🛡️ استمر في التدريب لتصبح أكثر أماناً</p>
                </div>
                
                <h3>🎓 واصل التعلم:</h3>
                <p>لتحسين مهاراتك في التعرف على الهجمات الإلكترونية:</p>
                
                <div class="action-buttons">
                    <a href="/training" class="btn btn-success">الذهاب إلى التدريب الكامل</a>
                   
                </div>
            </div>
        </div>

        <script>
            // الحصول على معاملات الرابط
            const urlParams = new URLSearchParams(window.location.search);
            const interactionType = urlParams.get('type') || 'click';
            
            // تسجيل تفاعل المشاهدة
            fetch('/api/record-interaction', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify({{
                    campaign_id: parseInt(window.location.pathname.split('/').pop()),
                    interaction_type: 'awareness_view',
                    user_id: urlParams.get('user') || '1'
                }})
            }}).catch(error => console.error('Error recording interaction:', error));
        </script>
    </body>
    </html>
    '''

# ========== واجهات الوصول الخارجي ==========

@app.route('/external/login/<access_code>')
def external_login(access_code):
    """واجهة تسجيل الدخول للمستخدمين الخارجيين"""
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>نظام التوعية بالتصيد - الدخول الخارجي</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            
            .login-container {{
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 500px;
                text-align: center;
            }}
            
            .logo {{
                font-size: 3em;
                margin-bottom: 20px;
                color: #2c3e50;
            }}
            
            h1 {{
                color: #2c3e50;
                margin-bottom: 10px;
            }}
            
            .subtitle {{
                color: #7f8c8d;
                margin-bottom: 30px;
            }}
            
            .access-info {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                border-left: 4px solid #3498db;
            }}
            
            .btn {{
                display: inline-block;
                background: #3498db;
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                border: none;
                transition: background 0.3s;
                margin: 10px 5px;
                width: 200px;
            }}
            
            .btn:hover {{
                background: #2980b9;
            }}
            
            .btn-success {{
                background: #27ae60;
            }}
            
            .btn-success:hover {{
                background: #219a52;
            }}
            
            .error-message {{
                background: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border: 1px solid #f5c6cb;
            }}
            
            .loading {{
                display: none;
                margin: 20px 0;
            }}
            
            .spinner {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 2s linear infinite;
                margin: 0 auto;
            }}
            
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">🎯</div>
            <h1>نظام التوعية بالتصيد</h1>
            <p class="subtitle">الدخول عبر الرابط الخارجي</p>
            
            <div class="access-info">
                <h3>رمز الوصول: <strong>{access_code}</strong></h3>
                <p>انقر على الزر أدناه للدخول إلى نظام التوعية</p>
            </div>
            
            <div id="errorMessage" class="error-message" style="display: none;"></div>
            
            <div id="loading" class="loading">
                <div class="spinner"></div>
                <p>جاري التحقق من صلاحية الرابط...</p>
            </div>
            
            <div id="successContent" style="display: none;">
                <div class="access-info" style="border-left-color: #27ae60;">
                    <h3>✅ الرابط صالح</h3>
                    <p id="accessDetails"></p>
                </div>
                <button class="btn btn-success" onclick="enterSystem()">الدخول إلى النظام</button>
            </div>
            
            <button class="btn" onclick="validateAccess()" id="validateBtn">التحقق من الرابط</button>
        </div>

        <script>
            const accessCode = '{access_code}';
            
            function validateAccess() {{
                document.getElementById('validateBtn').style.display = 'none';
                document.getElementById('loading').style.display = 'block';
                document.getElementById('errorMessage').style.display = 'none';
                
                fetch(`/api/external/validate/${{accessCode}}`)
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('loading').style.display = 'none';
                        
                        if (data.valid) {{
                            document.getElementById('successContent').style.display = 'block';
                            document.getElementById('accessDetails').innerHTML = `
                                <strong>الحملة:</strong> ${{data.access.campaign_name || 'تدريب عام'}}<br>
                                <strong>عدد الاستخدامات المتبقية:</strong> ${{data.access.max_uses - data.access.used_count}}
                            `;
                        }} else {{
                            document.getElementById('errorMessage').style.display = 'block';
                            document.getElementById('errorMessage').innerHTML = `
                                <strong>❌ خطأ:</strong> ${{data.error}}
                            `;
                            document.getElementById('validateBtn').style.display = 'inline-block';
                        }}
                    }})
                    .catch(error => {{
                        document.getElementById('loading').style.display = 'none';
                        document.getElementById('errorMessage').style.display = 'block';
                        document.getElementById('errorMessage').innerHTML = `
                            <strong>❌ خطأ في الاتصال:</strong> يرجى المحاولة مرة أخرى
                        `;
                        document.getElementById('validateBtn').style.display = 'inline-block';
                    }});
            }}
            
            function enterSystem() {{
                // تسجيل الاستخدام أولاً
                fetch(`/api/external/record-use/${{accessCode}}`, {{ method: 'POST' }})
                    .then(() => {{
                        // التوجه إلى النظام الرئيسي
                        window.location.href = `/external/dashboard/${{accessCode}}`;
                    }});
            }}
            
            // التحقق التلقائي عند تحميل الصفحة
            window.addEventListener('load', validateAccess);
        </script>
    </body>
    </html>
    '''

@app.route('/external/dashboard/<access_code>')
def external_dashboard(access_code):
    """لوحة التحكم للمستخدمين الخارجيين"""
    # التحقق من صلاحية الرمز أولاً
    conn = get_db_connection()
    access = conn.execute('''
        SELECT ea.*, c.name as campaign_name, c.id as campaign_id 
        FROM external_access ea
        LEFT JOIN campaigns c ON ea.campaign_id = c.id
        WHERE ea.access_code = ? AND ea.is_active = 1
    ''', (access_code,)).fetchone()
    
    if not access:
        conn.close()
        return '''
        <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
            <h1>❌ رابط الوصول غير صالح</h1>
            <p>الرابط الذي استخدمته غير صالح أو منتهي الصلاحية.</p>
            <p>يرجى التواصل مع المسؤول للحصول على رابط جديد.</p>
        </div>
        '''
    
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>نظام التوعية - لوحة التحكم</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            body {{
                background: #f5f6fa;
                min-height: 100vh;
            }}
            
            .navbar {{
                background: #2c3e50;
                color: white;
                padding: 1rem 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            
            .nav-container {{
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0 20px;
            }}
            
            .nav-logo h1 {{
                font-size: 1.5rem;
                font-weight: bold;
            }}
            
            .nav-info {{
                background: #34495e;
                padding: 0.5rem 1rem;
                border-radius: 5px;
                font-size: 0.9rem;
            }}
            
            .main-content {{
                max-width: 1200px;
                margin: 30px auto;
                padding: 0 20px;
            }}
            
            .welcome-section {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 3rem 2rem;
                border-radius: 15px;
                margin-bottom: 2rem;
                text-align: center;
            }}
            
            .features-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 2rem;
                margin: 2rem 0;
            }}
            
            .feature-card {{
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                text-align: center;
                border-top: 4px solid #3498db;
                cursor: pointer;
                transition: transform 0.3s;
            }}
            
            .feature-card:hover {{
                transform: translateY(-5px);
            }}
            
            .feature-icon {{
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
            
            .btn {{
                display: inline-block;
                background: #3498db;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                border: none;
                transition: background 0.3s;
                margin: 5px;
            }}
            
            .btn:hover {{
                background: #2980b9;
            }}
            
            .btn-success {{
                background: #27ae60;
            }}
            
            .btn-success:hover {{
                background: #219a52;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 1.5rem;
                margin: 2rem 0;
            }}
            
            .stat-card {{
                background: white;
                padding: 1.5rem;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                text-align: center;
            }}
            
            .stat-number {{
                font-size: 2.5rem;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 0.5rem;
            }}
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <div class="nav-logo">
                    <h1>🎯 نظام التوعية بالتصيد</h1>
                </div>
                <div class="nav-info">
                    الوصول الخارجي | رمز: {access_code}
                </div>
            </div>
        </nav>

        <main class="main-content">
            <section class="welcome-section">
                <h2>مرحباً بك في نظام التوعية بالتصيد</h2>
                <p>هذا النظام مصمم لتدريبك على التعرف على هجمات التصيد الإلكتروني وحماية معلوماتك</p>
            </section>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="totalCampaigns">0</div>
                    <div class="stat-label">الحملات المتاحة</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="totalTraining">3</div>
                    <div class="stat-label">مواد تدريبية</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="successRate">0%</div>
                    <div class="stat-label">معدل النجاح</div>
                </div>
            </div>

            <h2>الأنشطة المتاحة</h2>
            <div class="features-grid">
                <div class="feature-card" onclick="startTraining()">
                    <div class="feature-icon">🎓</div>
                    <h3>المواد التدريبية</h3>
                    <p>تعلم أساسيات التعرف على هجمات التصيد والوقاية منها</p>
                    <button class="btn">بدء التدريب</button>
                </div>
                
                <div class="feature-card" onclick="startSimulation()">
                    <div class="feature-icon">📧</div>
                    <h3>محاكاة التصيد</h3>
                    <p>اختبر مهاراتك في بيئة محاكاة آمنة</p>
                    <button class="btn">بدء المحاكاة</button>
                </div>
                
                <div class="feature-card" onclick="takeQuiz()">
                    <div class="feature-icon">🧪</div>
                    <h3>اختبار المعرفة</h3>
                    <p>اختبر معلوماتك من خلال اختبار تفاعلي</p>
                    <button class="btn">بدء الاختبار</button>
                </div>
            </div>
        </main>

        <script>
            const accessCode = '{access_code}';
            const campaignId = {access['campaign_id'] if access['campaign_id'] else 'null'};
            
            function startTraining() {{
                window.location.href = `/training?external=${{accessCode}}`;
            }}
            
            function startSimulation() {{
                if (campaignId && campaignId !== 'null') {{
                    window.location.href = `/simulate/${{campaignId}}?external=${{accessCode}}`;
                }} else {{
                    // إذا لم تكن هناك حملة محددة، انتقل إلى قائمة الحملات
                    window.location.href = `/training?external=${{accessCode}}`;
                }}
            }}
            
            function takeQuiz() {{
                window.location.href = `/training?external=${{accessCode}}#quiz`;
            }}
            
            // تحميل الإحصائيات
            fetch('/api/stats')
                .then(response => response.json())
                .then(stats => {{
                    document.getElementById('totalCampaigns').textContent = stats.total_campaigns;
                    document.getElementById('successRate').textContent = stats.success_rate + '%';
                }});
        </script>
    </body>
    </html>
    '''

# ========== واجهات API ==========

@app.route('/api/stats')
def api_stats():
    """إحصائيات النظام"""
    conn = get_db_connection()
    
    total_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0]
    total_campaigns = conn.execute('SELECT COUNT(*) FROM campaigns WHERE is_active = 1').fetchone()[0]
    total_responses = conn.execute('SELECT COUNT(*) FROM user_responses').fetchone()[0]
    
    # حساب نسبة النجاح بشكل أفضل
    successful_responses = conn.execute('''
        SELECT COUNT(*) FROM user_responses 
        WHERE interaction_type IN ('awareness_view', 'report', 'ignore')
    ''').fetchone()[0]
    
    # إذا كان هناك تفاعلات، احسب النسبة
    if total_responses > 0:
        success_rate = (successful_responses / total_responses) * 100
    else:
        success_rate = 0
    
    conn.close()
    
    return jsonify({
        'total_users': total_users,
        'total_campaigns': total_campaigns,
        'total_responses': total_responses,
        'success_rate': round(success_rate, 1)
    })

@app.route('/api/users', methods=['GET', 'POST'])
def api_users():
    """إدارة المستخدمين"""
    conn = get_db_connection()

    if request.method == 'GET':
        users = conn.execute('SELECT * FROM users WHERE is_active = 1').fetchall()
        result = [dict(user) for user in users]
        conn.close()
        return jsonify(result)

    elif request.method == 'POST':
        data = request.get_json()
        try:
            conn.execute(
                'INSERT INTO users (email, name, department, user_type) VALUES (?, ?, ?, ?)',
                (data['email'], data.get('name', ''), data.get('department', 'عام'), data.get('user_type', 'student'))
            )
            conn.commit()
            conn.close()
            return jsonify({'message': 'تم إضافة المستخدم بنجاح'})
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 400

@app.route('/api/campaigns', methods=['GET', 'POST'])
def api_campaigns():
    """إدارة الحملات"""
    conn = get_db_connection()

    if request.method == 'GET':
        campaigns = conn.execute('SELECT * FROM campaigns WHERE is_active = 1').fetchall()
        result = [dict(campaign) for campaign in campaigns]
        conn.close()
        return jsonify(result)

    elif request.method == 'POST':
        data = request.get_json()
        try:
            conn.execute(
                'INSERT INTO campaigns (name, description, phishing_type, difficulty_level, email_subject, email_content) VALUES (?, ?, ?, ?, ?, ?)',
                (data['name'], data.get('description', ''), data['phishing_type'], data.get('difficulty_level', 'medium'), data['email_subject'], data['email_content'])
            )
            conn.commit()
            conn.close()
            return jsonify({'message': 'تم إنشاء الحملة بنجاح'})
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 400

@app.route('/api/send-campaign/<int:campaign_id>', methods=['POST'])
def send_campaign(campaign_id):
    """إرسال حملة"""
    conn = get_db_connection()

    # جلب بيانات الحملة
    campaign = conn.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        return jsonify({'error': 'الحملة غير موجودة'}), 404

    # جلب المستخدمين
    users = conn.execute('SELECT * FROM users WHERE is_active = 1').fetchall()

    sent_count = 0
    for user in users:
        # محاكاة إرسال البريد
        tracking_url = f"http://localhost:5000/simulate/{campaign_id}?user={user['id']}"
        print(f"📧 محاكاة إرسال بريد إلى: {user['email']}")
        print(f"📋 الموضوع: {campaign['email_subject']}")
        print(f"🔗 الرابط: {tracking_url}")
        print("---")
        sent_count += 1

    # تحديث حالة الحملة
    conn.execute('UPDATE campaigns SET status = "active", sent_date = CURRENT_TIMESTAMP WHERE id = ?', (campaign_id,))
    conn.commit()
    conn.close()

    return jsonify({
        'message': f'تم إرسال الحملة إلى {sent_count} مستخدم',
        'sent': sent_count,
        'total': len(users)
    })

@app.route('/api/record-interaction', methods=['POST'])
def record_interaction():
    """تسجيل تفاعل المستخدم"""
    data = request.get_json()
    conn = get_db_connection()

    try:
        conn.execute(
            'INSERT INTO user_responses (user_id, campaign_id, interaction_type, data_entered, response_time, ip_address) VALUES (?, ?, ?, ?, ?, ?)',
            (data.get('user_id', 1), data['campaign_id'], data['interaction_type'], data.get('data_entered'), data.get('response_time'), request.remote_addr)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'تم تسجيل التفاعل'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-responses')
def get_user_responses():
    """الحصول على تفاعلات المستخدمين"""
    conn = get_db_connection()
    responses = conn.execute('''
        SELECT ur.*, u.email, c.name as campaign_name 
        FROM user_responses ur 
        JOIN users u ON ur.user_id = u.id 
        JOIN campaigns c ON ur.campaign_id = c.id 
        ORDER BY ur.interaction_date DESC 
        LIMIT 50
    ''').fetchall()

    result = [dict(response) for response in responses]
    conn.close()
    return jsonify(result)

# ========== واجهات API للوصول الخارجي ==========

@app.route('/api/external/access', methods=['POST'])
def create_external_access():
    """إنشاء رمز وصول خارجي"""
    data = request.get_json()
    conn = get_db_connection()
    
    try:
        # إنشاء رمز فريد
        access_code = str(uuid.uuid4())[:8].upper()
        
        # حساب تاريخ الانتهاء
        expiry_date = datetime.now() + timedelta(days=data.get('valid_days', 30))
        
        conn.execute(
            'INSERT INTO external_access (access_code, user_id, campaign_id, expiry_date, max_uses) VALUES (?, ?, ?, ?, ?)',
            (access_code, data.get('user_id'), data.get('campaign_id'), expiry_date, data.get('max_uses', 1))
        )
        conn.commit()
        
        # إنشاء الرابط الخارجي باستخدام الدالة الجديدة
        base_url = get_external_base_url()
        external_url = f"{base_url}/external/login/{access_code}"
        
        conn.close()
        return jsonify({
            'message': 'تم إنشاء رابط الوصول الخارجي',
            'access_code': access_code,
            'external_url': external_url,
            'expiry_date': expiry_date.strftime('%Y-%m-%d %H:%M:%S'),
            'base_url': base_url
        })
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400

@app.route('/api/external/validate/<access_code>')
def validate_external_access(access_code):
    """التحقق من صلاحية رمز الوصول"""
    conn = get_db_connection()
    
    access = conn.execute('''
        SELECT ea.*, u.name as user_name, c.name as campaign_name 
        FROM external_access ea
        LEFT JOIN users u ON ea.user_id = u.id
        LEFT JOIN campaigns c ON ea.campaign_id = c.id
        WHERE ea.access_code = ? AND ea.is_active = 1
    ''', (access_code,)).fetchone()
    
    if not access:
        conn.close()
        return jsonify({'valid': False, 'error': 'رمز الوصول غير صحيح أو منتهي'})
    
    # التحقق من التاريخ
    if access['expiry_date'] and datetime.now() > datetime.fromisoformat(access['expiry_date']):
        conn.close()
        return jsonify({'valid': False, 'error': 'رمز الوصول منتهي الصلاحية'})
    
    # التحقق من عدد الاستخدامات
    if access['max_uses'] and access['used_count'] >= access['max_uses']:
        conn.close()
        return jsonify({'valid': False, 'error': 'تم استخدام رمز الوصول لأقصى عدد مسموح'})
    
    conn.close()
    return jsonify({
        'valid': True,
        'access': dict(access)
    })

@app.route('/api/external/record-use/<access_code>', methods=['POST'])
def record_external_use(access_code):
    """تسجيل استخدام رمز الوصول"""
    conn = get_db_connection()
    
    try:
        conn.execute(
            'UPDATE external_access SET used_count = used_count + 1 WHERE access_code = ?',
            (access_code,)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'تم تسجيل الاستخدام'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/external/access-list')
def get_external_access_list():
    """الحصول على قائمة روابط الوصول"""
    conn = get_db_connection()
    access_list = conn.execute('''
        SELECT ea.*, c.name as campaign_name 
        FROM external_access ea
        LEFT JOIN campaigns c ON ea.campaign_id = c.id
        ORDER BY ea.created_date DESC
    ''').fetchall()

    result = [dict(access) for access in access_list]
    conn.close()
    return jsonify(result)

if __name__ == '__main__':
    # الحصول على الـ IP المحلي لعرضه للمستخدم
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "localhost"
    
    print("🎯 نظام التوعية بالتصيد - الإصدار الكامل مع الوصول الخارجي")
    print("📍 يعمل على: http://localhost:5000")
    print("📍 للوصول من أجهزة أخرى: http://{}:5000".format(local_ip))
    print("📊 لوحة التحكم: http://localhost:5000/dashboard")
    print("🎓 التدريب: http://localhost:5000/training")
    print("🌐 للوصول الخارجي: استخدم ngrok أو الرابط أعلاه")
    print("=" * 50)
    print("💡 لاستخدام ngrok: نزل ngrok وشغل 'ngrok http 5000'")
    print("💡 ثم استخدم الرابط الذي يظهر في ngrok")

    # فتح المتصفح تلقائياً
    def open_browser():
        webbrowser.open('http://localhost:5000')

    Timer(2, open_browser).start()

    # تشغيل الخادم على جميع الواجهات للوصول الخارجي
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)