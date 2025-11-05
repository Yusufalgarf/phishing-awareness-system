#!/usr/bin/env python3
"""
نظام التوعية بالتصيد - ملف التشغيل الجاهز
تشغيل: python run.py
"""

import os
import sys
import webbrowser
from threading import Timer
import subprocess

def main():
    print("🎯 نظام التوعية بالتصيد - الإصدار الجاهز")
    print("=" * 60)
    
    # التحقق من المتطلبات
    if check_requirements():
        # تشغيل الخادم
        start_server()

def check_requirements():
    """التحقق من تثبيت المتطلبات"""
    try:
        import flask
        import sqlite3
        print("✅ جميع المتطلبات مثبتة")
        return True
    except ImportError as e:
        print(f"❌ متطلب مفقود: {e}")
        print("📦 جاري تثبيت المتطلبات...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-sqlalchemy", "flask-cors"])
            print("✅ تم تثبيت المتطلبات بنجاح")
            return True
        except subprocess.CalledProcessError:
            print("❌ فشل في تثبيت المتطلبات")
            return False

def start_server():
    """تشغيل خادم التطبيق"""
    try:
        # استيراد وتشغيل التطبيق
        from backend.app import app
        
        print("🌐 جاري تشغيل الخادم...")
        print("📍 العنوان: http://localhost:5000")
        print("📊 لوحة التحكم: http://localhost:5000/dashboard")
        print("🎓 التدريب: http://localhost:5000/training")
        print("=" * 60)
        print("⏹️  لإيقاف الخادم: Ctrl+C")
        
        # فتح المتصفح تلقائياً بعد 3 ثوان
        def open_browser():
            webbrowser.open('http://localhost:5000')
        
        Timer(3, open_browser).start()
        
        # تشغيل التطبيق
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        
    except Exception as e:
        print(f"❌ خطأ في تشغيل الخادم: {e}")
        input("اضغط Enter للإغلاق...")

if __name__ == '__main__':
    main()