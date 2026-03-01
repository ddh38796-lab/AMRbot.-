import sqlite3
import threading
import time
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self.connection = None
        self.cursor = None
        self.lock = threading.Lock()
        self.connect()
        self.create_all_tables()

    def connect(self):
        self.connection = sqlite3.connect(self.db_file, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def commit(self):
        if self.connection:
            self.connection.commit()

    def close(self):
        if self.connection:
            self.connection.close()

    def execute(self, query, params=()):
        with self.lock:
            try:
                self.cursor.execute(query, params)
                self.commit()
                return True
            except Exception as e:
                print(f"خطأ في تنفيذ الاستعلام: {e}")
                return False

    def fetch_one(self, query, params=()):
        with self.lock:
            try:
                self.cursor.execute(query, params)
                return self.cursor.fetchone()
            except Exception as e:
                print(f"خطأ في جلب البيانات: {e}")
                return None

    def fetch_all(self, query, params=()):
        with self.lock:
            try:
                self.cursor.execute(query, params)
                return self.cursor.fetchall()
            except Exception as e:
                print(f"خطأ في جلب البيانات: {e}")
                return []

    def create_all_tables(self):
        self.create_users_table()
        self.create_services_table()
        self.create_orders_table()
        self.create_payments_table()
        self.create_referrals_table()
        self.create_competitions_table()
        self.create_competition_participants_table()
        self.create_free_requests_table()
        print("✅ تم إنشاء جميع جداول قاعدة البيانات بنجاح")

    def create_users_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language TEXT DEFAULT 'ar',
            balance REAL DEFAULT 0,
            total_deposits REAL DEFAULT 0,
            total_spent REAL DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            joined_channel INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            FOREIGN KEY (referred_by) REFERENCES users(user_id)
        )
        """
        self.execute(query)

    def create_services_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS services (
            service_id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT,
            api_service_id TEXT,
            name TEXT,
            name_ar TEXT,
            category TEXT,
            price REAL,
            original_price REAL,
            min_quantity INTEGER,
            max_quantity INTEGER,
            description TEXT,
            api_type TEXT,
            speed TEXT,
            country TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP
        )
        """
        self.execute(query)

    def create_orders_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER,
            api_order_id TEXT,
            api_name TEXT,
            link TEXT,
            quantity INTEGER,
            price REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (service_id) REFERENCES services(service_id)
        )
        """
        self.execute(query)

    def create_payments_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'pending',
            processed_by INTEGER,
            notes TEXT,
            created_at TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (processed_by) REFERENCES users(user_id)
        )
        """
        self.execute(query)

    def create_referrals_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS referrals (
            referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            bonus_amount REAL DEFAULT 5,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referred_id) REFERENCES users(user_id)
        )
        """
        self.execute(query)

    def create_competitions_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS competitions (
            comp_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            name_ar TEXT,
            description TEXT,
            prize REAL,
            winners_count INTEGER DEFAULT 1,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP
        )
        """
        self.execute(query)

    def create_competition_participants_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS competition_participants (
            comp_id INTEGER,
            user_id INTEGER,
            joined_at TIMESTAMP,
            is_winner INTEGER DEFAULT 0,
            PRIMARY KEY (comp_id, user_id),
            FOREIGN KEY (comp_id) REFERENCES competitions(comp_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
        self.execute(query)

    def create_free_requests_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS free_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_type TEXT,
            quantity INTEGER,
            requested_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
        self.execute(query)

    def add_user(self, user_id, username, first_name, last_name=None, referred_by=None):
        with self.lock:
            existing = self.get_user(user_id)
            if existing:
                self.update_user_activity(user_id)
                return True
            referral_code = f"AMR{user_id}{int(time.time())}"
            query = """
            INSERT INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            now = datetime.now()
            result = self.execute(query, (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
            if result and referred_by:
                self.add_referral(referred_by, user_id)
            return result

    def get_user(self, user_id):
        query = "SELECT * FROM users WHERE user_id = ?"
        return self.fetch_one(query, (user_id,))

    def get_user_by_referral(self, referral_code):
        query = "SELECT * FROM users WHERE referral_code = ?"
        return self.fetch_one(query, (referral_code,))

    def update_user_activity(self, user_id):
        query = "UPDATE users SET last_active = ? WHERE user_id = ?"
        return self.execute(query, (datetime.now(), user_id))

    def update_user_language(self, user_id, language):
        query = "UPDATE users SET language = ? WHERE user_id = ?"
        return self.execute(query, (language, user_id))

    def update_channel_status(self, user_id, status=1):
        query = "UPDATE users SET joined_channel = ? WHERE user_id = ?"
        return self.execute(query, (status, user_id))

    def block_user(self, user_id):
        query = "UPDATE users SET is_blocked = 1 WHERE user_id = ?"
        return self.execute(query, (user_id,))

    def unblock_user(self, user_id):
        query = "UPDATE users SET is_blocked = 0 WHERE user_id = ?"
        return self.execute(query, (user_id,))

    def get_all_users(self):
        query = "SELECT user_id FROM users WHERE is_blocked = 0"
        return self.fetch_all(query)

    def get_total_users(self):
        query = "SELECT COUNT(*) as count FROM users"
        result = self.fetch_one(query)
        return result['count'] if result else 0

    def get_active_users_today(self):
        today = datetime.now().date()
        query = "SELECT COUNT(*) as count FROM users WHERE DATE(last_active) = ?"
        result = self.fetch_one(query, (today,))
        return result['count'] if result else 0

    def get_balance(self, user_id):
        query = "SELECT balance FROM users WHERE user_id = ?"
        result = self.fetch_one(query, (user_id,))
        return result['balance'] if result else 0

    def add_balance(self, user_id, amount, note=""):
        query = "UPDATE users SET balance = balance + ?, total_deposits = total_deposits + ? WHERE user_id = ?"
        return self.execute(query, (amount, amount, user_id))

    def deduct_balance(self, user_id, amount, note=""):
        with self.lock:
            balance = self.get_balance(user_id)
            if balance < amount:
                return False
            query = "UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ?"
            return self.execute(query, (amount, amount, user_id))

    def add_referral(self, referrer_id, referred_id):
        query = "SELECT * FROM referrals WHERE referred_id = ?"
        existing = self.fetch_one(query, (referred_id,))
        if existing:
            return False
        query = """
        INSERT INTO referrals (referrer_id, referred_id, created_at)
        VALUES (?, ?, ?)
        """
        return self.execute(query, (referrer_id, referred_id, datetime.now()))

    def get_referral_count(self, user_id):
        query = "SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ?"
        result = self.fetch_one(query, (user_id,))
        return result['count'] if result else 0

    def get_referral_earnings(self, user_id, bonus_amount=5):
        count = self.get_referral_count(user_id)
        return count * bonus_amount    # ==================== دوال الخدمات ====================
    
    def add_service(self, api_name, api_service_id, name, name_ar, category, price, original_price,
                    min_qty, max_qty, api_type, description="", speed="", country=""):
        """إضافة خدمة جديدة (تستخدم أثناء المزامنة)"""
        query = """
        INSERT INTO services 
        (api_name, api_service_id, name, name_ar, category, price, original_price,
         min_quantity, max_quantity, description, api_type, speed, country, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.execute(query, (
            api_name, api_service_id, name, name_ar, category, price, original_price,
            min_qty, max_qty, description, api_type, speed, country, datetime.now()
        ))
    
    def get_service(self, service_id):
        """جلب خدمة بالمعرف"""
        query = "SELECT * FROM services WHERE service_id = ? AND is_active = 1"
        return self.fetch_one(query, (service_id,))
    
    def get_services_by_api(self, api_name):
        """جلب جميع الخدمات لسيرفر معين"""
        query = "SELECT * FROM services WHERE api_name = ? AND is_active = 1 ORDER BY price ASC"
        return self.fetch_all(query, (api_name,))
    
    def get_services_by_category(self, api_name, category):
        """جلب خدمات سيرفر معين حسب التصنيف"""
        query = "SELECT * FROM services WHERE api_name = ? AND category = ? AND is_active = 1 ORDER BY price ASC"
        return self.fetch_all(query, (api_name, category))
    
    def get_all_apis_list(self):
        """جلب قائمة بجميع أسماء السيرفرات (للاستخدام في الأزرار)"""
        query = "SELECT DISTINCT api_name FROM services WHERE is_active = 1"
        return self.fetch_all(query)
    
    def get_categories_for_api(self, api_name):
        """جلب التصنيفات المتاحة لسيرفر معين"""
        query = "SELECT DISTINCT category FROM services WHERE api_name = ? AND is_active = 1"
        return self.fetch_all(query, (api_name,))
    
    def clear_old_services(self):
        """مسح جميع الخدمات القديمة (استعداداً للمزامنة الجديدة)"""
        query = "DELETE FROM services"
        return self.execute(query)
    
    def get_services_count(self, api_name):
        """عدد الخدمات لسيرفر معين"""
        query = "SELECT COUNT(*) as count FROM services WHERE api_name = ? AND is_active = 1"
        result = self.fetch_one(query, (api_name,))
        return result['count'] if result else 0
    
    # ==================== دوال الطلبات ====================
    
    def create_order(self, user_id, service_id, link, quantity, price, api_name=None, api_order_id=None):
        """إنشاء طلب جديد"""
        query = """
        INSERT INTO orders 
        (user_id, service_id, api_name, api_order_id, link, quantity, price, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        result = self.execute(query, (
            user_id, service_id, api_name, api_order_id, link, quantity, price, datetime.now()
        ))
        if result:
            # خصم الرصيد
            self.deduct_balance(user_id, price, f"طلب #{self.cursor.lastrowid}")
        return self.cursor.lastrowid if result else None
    
    def get_order(self, order_id):
        """جلب طلب بالمعرف"""
        query = """
        SELECT o.*, s.name_ar as service_name 
        FROM orders o
        LEFT JOIN services s ON o.service_id = s.service_id
        WHERE o.order_id = ?
        """
        return self.fetch_one(query, (order_id,))
    
    def get_user_orders(self, user_id, limit=10):
        """جلب طلبات مستخدم معين"""
        query = """
        SELECT o.*, s.name_ar as service_name 
        FROM orders o
        LEFT JOIN services s ON o.service_id = s.service_id
        WHERE o.user_id = ? 
        ORDER BY o.created_at DESC 
        LIMIT ?
        """
        return self.fetch_all(query, (user_id, limit))
    
    def update_order_status(self, order_id, status, api_order_id=None):
        """تحديث حالة الطلب"""
        if api_order_id:
            query = "UPDATE orders SET status = ?, api_order_id = ? WHERE order_id = ?"
            return self.execute(query, (status, api_order_id, order_id))
        else:
            query = "UPDATE orders SET status = ? WHERE order_id = ?"
            return self.execute(query, (status, order_id))
    
    def complete_order(self, order_id):
        """إنهاء طلب (اكتمل)"""
        query = "UPDATE orders SET status = 'completed', completed_at = ? WHERE order_id = ?"
        return self.execute(query, (datetime.now(), order_id))
    
    def get_pending_orders(self):
        """جلب الطلبات المعلقة التي لها رقم طلب API"""
        query = "SELECT * FROM orders WHERE status = 'pending' AND api_order_id IS NOT NULL"
        return self.fetch_all(query)
    
    def get_total_orders(self):
        """إجمالي عدد الطلبات"""
        query = "SELECT COUNT(*) as count FROM orders"
        result = self.fetch_one(query)
        return result['count'] if result else 0
    
    def get_total_earnings(self):
        """إجمالي الأرباح من الطلبات المكتملة"""
        query = "SELECT SUM(price) as total FROM orders WHERE status = 'completed'"
        result = self.fetch_one(query)
        return result['total'] if result and result['total'] else 0
    
    # ==================== دوال المدفوعات (الإيداع) ====================
    
    def add_payment(self, user_id, amount, screenshot_file_id):
        """إضافة طلب دفع جديد"""
        query = """
        INSERT INTO payments (user_id, amount, screenshot_file_id, created_at)
        VALUES (?, ?, ?, ?)
        """
        return self.execute(query, (user_id, amount, screenshot_file_id, datetime.now()))
    
    def get_payment(self, payment_id):
        """جلب طلب دفع بالمعرف"""
        query = "SELECT * FROM payments WHERE payment_id = ?"
        return self.fetch_one(query, (payment_id,))
    
    def get_pending_payments(self):
        """جلب جميع طلبات الدفع المعلقة مع بيانات المستخدم"""
        query = """
        SELECT p.*, u.username, u.first_name 
        FROM payments p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.status = 'pending'
        ORDER BY p.created_at ASC
        """
        return self.fetch_all(query)
    
    def approve_payment(self, payment_id, admin_id):
        """قبول طلب دفع وإضافة الرصيد"""
        # جلب معلومات الدفع
        payment = self.get_payment(payment_id)
        if not payment:
            return False
        
        # تحديث حالة الدفع
        query = "UPDATE payments SET status = 'approved', processed_by = ?, processed_at = ? WHERE payment_id = ?"
        result = self.execute(query, (admin_id, datetime.now(), payment_id))
        
        if result:
            # إضافة الرصيد للمستخدم
            self.add_balance(payment['user_id'], payment['amount'], f"إيداع #{payment_id}")
        
        return result
    
    def reject_payment(self, payment_id, admin_id, reason=""):
        """رفض طلب دفع"""
        query = "UPDATE payments SET status = 'rejected', processed_by = ?, processed_at = ?, notes = ? WHERE payment_id = ?"
        return self.execute(query, (admin_id, datetime.now(), reason, payment_id))
    
    # ==================== دوال المسابقات ====================
    
    def create_competition(self, name, name_ar, description, prize, winners_count, end_date):
        """إنشاء مسابقة جديدة"""
        query = """
        INSERT INTO competitions 
        (name, name_ar, description, prize, winners_count, end_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        return self.execute(query, (name, name_ar, description, prize, winners_count, end_date, datetime.now()))
    
    def get_active_competitions(self):
        """جلب المسابقات النشطة (التي لم ينته وقتها)"""
        now = datetime.now()
        query = """
        SELECT * FROM competitions 
        WHERE is_active = 1 AND end_date > ?
        ORDER BY end_date ASC
        """
        return self.fetch_all(query, (now,))
    
    def join_competition(self, comp_id, user_id):
        """انضمام مستخدم لمسابقة"""
        query = """
        INSERT OR IGNORE INTO competition_participants (comp_id, user_id, joined_at)
        VALUES (?, ?, ?)
        """
        return self.execute(query, (comp_id, user_id, datetime.now()))
    
    def get_competition_participants(self, comp_id):
        """جلب المشاركين في مسابقة"""
        query = """
        SELECT u.user_id, u.username, u.first_name, cp.joined_at
        FROM competition_participants cp
        JOIN users u ON cp.user_id = u.user_id
        WHERE cp.comp_id = ?
        ORDER BY cp.joined_at ASC
        """
        return self.fetch_all(query, (comp_id,))
    
    # ==================== دوال الخدمات المجانية اليومية ====================
    
    def can_request_free_service(self, user_id):
        """التحقق مما إذا كان المستخدم يمكنه طلب خدمة مجانية اليوم"""
        query = """
        SELECT requested_at FROM free_requests 
        WHERE user_id = ? 
        ORDER BY requested_at DESC LIMIT 1
        """
        last_request = self.fetch_one(query, (user_id,))
        
        if not last_request:
            return True, 0  # لم يطلب من قبل
        
        last_time = datetime.fromisoformat(last_request['requested_at'])
        hours_passed = (datetime.now() - last_time).total_seconds() / 3600
        
        if hours_passed >= 24:
            return True, 0
        else:
            remaining = 24 - hours_passed
            return False, round(remaining, 1)
    
    def add_free_request(self, user_id, service_type, quantity):
        """تسجيل طلب خدمة مجانية"""
        query = """
        INSERT INTO free_requests (user_id, service_type, quantity, requested_at)
        VALUES (?, ?, ?, ?)
        """
        return self.execute(query, (user_id, service_type, quantity, datetime.now()))
    
    # ==================== دوال الإحصائيات العامة ====================
    
    def get_statistics(self):
        """إحصائيات عامة للبوت"""
        stats = {}
        stats['total_users'] = self.get_total_users()
        stats['active_today'] = self.get_active_users_today()
        stats['total_orders'] = self.get_total_orders()
        stats['total_earnings'] = self.get_total_earnings()
        
        # عدد الخدمات النشطة
        query = "SELECT COUNT(*) as count FROM services WHERE is_active = 1"
        result = self.fetch_one(query)
        stats['total_services'] = result['count'] if result else 0
        
        # الطلبات المعلقة
        query = "SELECT COUNT(*) as count FROM orders WHERE status = 'pending'"
        result = self.fetch_one(query)
        stats['pending_orders'] = result['count'] if result else 0
        
        # المدفوعات المعلقة
        query = "SELECT COUNT(*) as count FROM payments WHERE status = 'pending'"
        result = self.fetch_one(query)
        stats['pending_payments'] = result['count'] if result else 0
        
        # إجمالي الودائع
        query = "SELECT SUM(total_deposits) as total FROM users"
        result = self.fetch_one(query)
        stats['total_deposits'] = result['total'] if result and result['total'] else 0
        
        return stats

# نهاية كلاس Database
