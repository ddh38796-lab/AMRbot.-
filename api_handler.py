# ==================== Amr Digital Empire - ملف معالج API ====================
# الإمبراطور: @AmrDigital
# تاريخ الإنشاء: 1 مارس 2026
# الإصدار: 1.0

import requests
import json
import time
from datetime import datetime
from config import APIS, PRICE_STEPS, FREE_SERVICE_LIMITS, MINIMUM_PRICE

class SMMAPI:
    """
    كلاس متكامل للربط مع السيرفرات (حالياً موقعان)
    يحتوي على دوال لجلب الخدمات، تقديم الطلبات، التحقق من الحالة،
    والمزامنة المتقدمة مع قاعدة البيانات.
    """
    
    def __init__(self):
        """
        تهيئة المعالج مع إعدادات السيرفرات من config.py
        """
        self.apis = APIS
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AmrDigital-Bot/1.0',
            'Accept': 'application/json'
        })
        
        # إحصائيات لكل سيرفر
        self.api_stats = {}
        for api_name in self.apis:
            self.api_stats[api_name] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'last_sync': None,
                'services_count': 0
            }
        
        # كاش للخدمات (لتقليل الطلبات)
        self.services_cache = []
        self.cache_timestamp = None
    
    # -------------------------------------------------------------------
    # دوال الاتصال الأساسية
    # -------------------------------------------------------------------
    
    def make_request(self, api_name, action, additional_params=None):
        """
        إجراء طلب إلى API معين مع معالجة الأخطاء.
        :param api_name: اسم السيرفر (مفتاح في قاموس apis)
        :param action: الإجراء المطلوب (services, add, status, balance)
        :param additional_params: معاملات إضافية (للطلبات)
        :return: بيانات الاستجابة بصيغة JSON أو None في حالة الفشل
        """
        api_config = self.apis.get(api_name)
        if not api_config:
            print(f"❌ سيرفر {api_name} غير موجود")
            return None
        
        self.api_stats[api_name]['total_requests'] += 1
        
        try:
            # تجهيز البيانات حسب نوع السيرفر (مدفوع أو مجاني)
            if api_config['type'] == 'paid':
                payload = {
                    'key': api_config['key'],
                    'action': action
                }
            else:
                payload = {
                    'api_key': api_config['key'],
                    'action': action
                }
            
            # دمج المعاملات الإضافية إن وجدت
            if additional_params:
                payload.update(additional_params)
            
            # تنفيذ الطلب (باستخدام POST كما هو مطلوب)
            response = self.session.post(
                api_config['url'],
                data=payload,
                timeout=30
            )
            
            # التحقق من حالة الاستجابة
            if response.status_code == 200:
                try:
                    result = response.json()
                    self.api_stats[api_name]['successful_requests'] += 1
                    return result
                except json.JSONDecodeError:
                    self.api_stats[api_name]['failed_requests'] += 1
                    print(f"⚠️ خطأ في فك ترميز JSON من {api_name}")
                    return None
            else:
                self.api_stats[api_name]['failed_requests'] += 1
                print(f"⚠️ خطأ HTTP {response.status_code} من {api_name}")
                return None
                
        except requests.exceptions.ConnectionError:
            self.api_stats[api_name]['failed_requests'] += 1
            print(f"⚠️ خطأ في الاتصال بالسيرفر {api_name}")
            return None
        except requests.exceptions.Timeout:
            self.api_stats[api_name]['failed_requests'] += 1
            print(f"⚠️ انتهت مهلة الاتصال بـ {api_name}")
            return None
        except Exception as e:
            self.api_stats[api_name]['failed_requests'] += 1
            print(f"⚠️ خطأ غير متوقع مع {api_name}: {e}")
            return None
    
    # -------------------------------------------------------------------
    # دوال جلب الخدمات من سيرفر واحد
    # -------------------------------------------------------------------
    
    def fetch_services_from_api(self, api_name):
        """
        جلب جميع الخدمات من سيرفر محدد.
        :param api_name: اسم السيرفر
        :return: قائمة بالخدمات بعد معالجتها
        """
        api_config = self.apis.get(api_name)
        if not api_config:
            return []
        
        print(f"📡 جاري الاتصال بـ {api_config['name']}...")
        
        # طلب الخدمات
        services_data = self.make_request(api_name, 'services')
        
        if not services_data:
            print(f"❌ فشل جلب الخدمات من {api_config['name']}")
            return []
        
        # التأكد من أن البيانات هي قائمة
        if not isinstance(services_data, list):
            print(f"⚠️ البيانات الواردة من {api_name} ليست قائمة")
            # محاولة تحويل إذا كان قاموساً يحتوي على خدمات
            if isinstance(services_data, dict):
                if 'data' in services_data:
                    services_data = services_data['data']
                elif 'services' in services_data:
                    services_data = services_data['services']
                else:
                    return []
            else:
                return []
        
        processed_services = []
        
        for service in services_data:
            try:
                # التأكد من أن الخدمة هي قاموس
                if not isinstance(service, dict):
                    continue
                
                service_id = service.get('service') or service.get('id')
                if not service_id:
                    continue
                
                name = service.get('name', 'خدمة بدون اسم')
                original_price = float(service.get('price', 0))
                original_price = float(service.get('rate', original_price))  # بعض المواقع تستخدم rate
                
                # للخدمات المجانية، نريد فقط التي سعرها 0 إذا كان السيرفر مجاني
                if api_config['type'] == 'free' and original_price > 0:
                    continue
                
                # حساب السعر النهائي باستخدام نظام الشرائح الذكي
                final_price = self.calculate_final_price(original_price)
                
                # تصنيف الخدمة
                category = self.detect_category(name)
                
                # اسم عربي تقريبي
                name_ar = self.translate_service_name(name, category)
                
                # الحد الأدنى والأقصى
                min_qty = int(service.get('min', 1))
                max_qty = int(service.get('max', 10000))
                
                # سرعة الخدمة (تقديرية)
                speed = self.detect_speed(service)
                
                processed_services.append({
                    'api_name': api_name,
                    'api_service_id': str(service_id),
                    'name': name,
                    'name_ar': name_ar,
                    'category': category,
                    'price': final_price,
                    'original_price': original_price,
                    'min': min_qty,
                    'max': max_qty,
                    'api_type': api_config['type'],
                    'speed': speed,
                    'country': api_config.get('country', 'عالمي'),
                    'api_provider': api_config['name']
                })
                
            except Exception as e:
                print(f"⚠️ خطأ في معالجة خدمة من {api_name}: {e}")
                continue
        
        # تحديث الإحصائيات
        self.api_stats[api_name]['services_count'] = len(processed_services)
        self.api_stats[api_name]['last_sync'] = datetime.now()
        
        print(f"✅ تم جلب {len(processed_services)} خدمة من {api_config['name']}")
        return processed_services
    
    # -------------------------------------------------------------------
    # نظام الأسعار الذكي (الشرائح)
    # -------------------------------------------------------------------
    
    def calculate_final_price(self, original_price):
        """
        تطبيق نظام الشرائح على السعر الأصلي.
        :param original_price: سعر الخدمة من السيرفر
        :return: السعر النهائي للمستخدم
        """
        for limit, price in PRICE_STEPS:
            if original_price <= limit:
                return max(price, MINIMUM_PRICE)
        
        # إذا كان السعر أكبر من آخر شريحة، نضيف زيادة تدريجية
        last_limit = PRICE_STEPS[-1][0]
        last_price = PRICE_STEPS[-1][1]
        extra_steps = (original_price - last_limit) // 5
        return last_price + (extra_steps + 1) * 5
    
    # -------------------------------------------------------------------
    # دوال مساعدة للتصنيف والترجمة
    # -------------------------------------------------------------------
    
    def detect_category(self, service_name):
        """
        تحديد تصنيف الخدمة بناءً على اسمها.
        """
        name_lower = service_name.lower()
        
        if any(k in name_lower for k in ['instagram', 'ig']):
            return 'instagram'
        elif any(k in name_lower for k in ['youtube', 'yt']):
            return 'youtube'
        elif any(k in name_lower for k in ['facebook', 'fb']):
            return 'facebook'
        elif any(k in name_lower for k in ['twitter']):
            return 'twitter'
        elif any(k in name_lower for k in ['tiktok']):
            return 'tiktok'
        elif any(k in name_lower for k in ['telegram', 'tg']):
            return 'telegram'
        elif any(k in name_lower for k in ['spotify']):
            return 'spotify'
        elif any(k in name_lower for k in ['soundcloud']):
            return 'soundcloud'
        else:
            return 'other'
    
    def translate_service_name(self, english_name, category):
        """
        ترجمة تقريبية لاسم الخدمة إلى العربية.
        """
        translations = {
            'followers': 'متابعين',
            'follower': 'متابع',
            'likes': 'إعجابات',
            'like': 'إعجاب',
            'views': 'مشاهدات',
            'view': 'مشاهدة',
            'comments': 'تعليقات',
            'comment': 'تعليق',
            'shares': 'مشاركات',
            'share': 'مشاركة',
            'subscribers': 'مشتركين',
            'subscriber': 'مشترك',
            'retweets': 'إعادة تغريد',
            'retweet': 'إعادة تغريد',
            'favorites': 'مفضلة',
            'favorite': 'مفضلة',
            'votes': 'أصوات',
            'vote': 'صوت',
            'members': 'أعضاء',
            'member': 'عضو',
            'joins': 'انضمام',
            'join': 'انضمام',
            'streams': 'استماع',
            'stream': 'استماع',
            'plays': 'تشغيل',
            'play': 'تشغيل',
        }
        
        translated = english_name
        for eng, arb in translations.items():
            if eng in english_name.lower():
                translated = translated.replace(eng, arb)
        
        return translated.strip()
    
    def detect_speed(self, service_data):
        """
        تقدير سرعة الخدمة بناءً على بيانات السيرفر.
        """
        service_str = json.dumps(service_data).lower()
        
        if 'instant' in service_str or 'fast' in service_str:
            return '⚡ سريع'
        elif 'slow' in service_str:
            return '🐢 بطيء'
        else:
            return '⏱️ عادي'
    
    # -------------------------------------------------------------------
    # دوال جلب الخدمات من جميع السيرفرات
    # -------------------------------------------------------------------
    
    def fetch_all_services(self):
        """
        جلب الخدمات من جميع السيرفرات (حالياً موقعان).
        """
        print("\n" + "="*60)
        print("🚀 بدء مزامنة الخدمات من جميع السيرفرات")
        print("="*60)
        
        all_services = []
        successful_apis = 0
        failed_apis = 0
        
        for idx, (api_name, api_config) in enumerate(self.apis.items(), 1):
            print(f"\n📡 [{idx}/{len(self.apis)}] {api_config['name']}")
            print("-"*40)
            
            services = self.fetch_services_from_api(api_name)
            
            if services:
                all_services.extend(services)
                successful_apis += 1
            else:
                failed_apis += 1
            
            # تأخير بسيط بين الطلبات
            time.sleep(2)
        
        print("\n" + "="*60)
        print(f"✅ اكتملت المزامنة!")
        print(f"   • إجمالي الخدمات: {len(all_services)}")
        print(f"   • سيرفرات ناجحة: {successful_apis}")
        print(f"   • سيرفرات فاشلة: {failed_apis}")
        print("="*60)
        
        # تخزين في الكاش
        self.services_cache = all_services
        self.cache_timestamp = datetime.now()
        
        return all_services    # -------------------------------------------------------------------
    # دوال تقديم الطلبات (orders)
    # -------------------------------------------------------------------
    
    def place_order(self, api_name, service_id, link, quantity):
        """
        تقديم طلب جديد إلى سيرفر محدد.
        :param api_name: اسم السيرفر
        :param service_id: معرف الخدمة في ذلك السيرفر
        :param link: الرابط المطلوب
        :param quantity: الكمية المطلوبة
        :return: رقم الطلب من السيرفر أو None في حالة الفشل
        """
        api_config = self.apis.get(api_name)
        if not api_config:
            print(f"❌ سيرفر {api_name} غير موجود")
            return None
        
        print(f"📦 تقديم طلب إلى {api_config['name']}:")
        print(f"   • service_id: {service_id}")
        print(f"   • link: {link}")
        print(f"   • quantity: {quantity}")
        
        params = {
            'service': service_id,
            'link': link,
            'quantity': quantity
        }
        
        result = self.make_request(api_name, 'add', params)
        
        if result:
            order_id = result.get('order') or result.get('id') or str(result)
            print(f"✅ تم تقديم الطلب بنجاح، رقم الطلب: {order_id}")
            return str(order_id)
        else:
            print(f"❌ فشل تقديم الطلب إلى {api_config['name']}")
            return None
    
    def check_order_status(self, api_name, order_id):
        """
        التحقق من حالة طلب في سيرفر محدد.
        :param api_name: اسم السيرفر
        :param order_id: رقم الطلب
        :return: قاموس بمعلومات الحالة أو None
        """
        params = {'order': order_id}
        result = self.make_request(api_name, 'status', params)
        
        if result:
            return {
                'status': result.get('status', 'unknown'),
                'start_count': result.get('start_count', 0),
                'remains': result.get('remains', 0)
            }
        return None
    
    def get_balance(self, api_name):
        """
        جلب رصيد سيرفر معين.
        :param api_name: اسم السيرفر
        :return: الرصيد (float) أو None
        """
        result = self.make_request(api_name, 'balance')
        
        if result:
            balance = result.get('balance') or result.get('funds') or 0
            return float(balance)
        return None
    
    # -------------------------------------------------------------------
    # الذكاء الاصطناعي لاختيار أفضل موقع للخدمة
    # -------------------------------------------------------------------
    
    def smart_service_selector(self, service_type, quantity, platform, db_handler):
        """
        الذكاء الاصطناعي يختار أفضل موقع للخدمة بناءً على السعر والجودة.
        """
        best_service = None
        best_price = float('inf')
        
        for api_name in self.apis:
            services = db_handler.get_services_by_category(api_name, platform)
            for service in services:
                if service_type.lower() in service['name'].lower() or service_type.lower() in service['name_ar'].lower():
                    if service['min_quantity'] <= quantity <= service['max_quantity']:
                        total_price = service['price'] * quantity
                        if total_price < best_price:
                            best_price = total_price
                            best_service = service
        return best_service
    
    # -------------------------------------------------------------------
    # دوال الخدمة المجانية اليومية
    # -------------------------------------------------------------------
    
    def get_cheapest_free_service(self, db_handler):
        """
        جلب أرخص خدمة مجانية من السيرفرات المتاحة.
        """
        # نأخذ أول سيرفر متاح (يمكن تخصيصها لسيرفر معين)
        for api_name in self.apis:
            services = db_handler.get_services_by_api(api_name)
            if services:
                services.sort(key=lambda x: x['price'])
                return services[:5]  # أرخص 5 خدمات
        return None
    
    def check_free_service_limit(self, service_name, quantity):
        """
        التحقق من أن الكمية لا تتجاوز الحد المسموح للخدمة المجانية.
        """
        name_lower = service_name.lower()
        if 'like' in name_lower:
            max_q = FREE_SERVICE_LIMITS.get('like', 10)
            return quantity <= max_q, min(quantity, max_q)
        elif 'view' in name_lower:
            max_q = FREE_SERVICE_LIMITS.get('view', 100)
            return quantity <= max_q, min(quantity, max_q)
        else:
            max_q = FREE_SERVICE_LIMITS.get('default', 10)
            return quantity <= max_q, min(quantity, max_q)
    
    # -------------------------------------------------------------------
    # دوال نظام التحويلات (عند نفاد الرصيد)
    # -------------------------------------------------------------------
    
    def process_payment_redirect(self, user_id, service_price, api_name, db_handler):
        """
        معالجة حالة نفاد الرصيد: إرجاع رقم الموقع للتحويل.
        """
        api_config = self.apis.get(api_name)
        if not api_config:
            return None
        
        site_phone = api_config.get('phone')
        if not site_phone:
            return None
        
        return {
            'phone': site_phone,
            'amount': service_price,
            'api_name': api_name,
            'message': f"⚠️ حول المبلغ {service_price} جنيه على الرقم {site_phone} وأرسل صورة الإيصال"
        }
    
    # -------------------------------------------------------------------
    # دوال المزامنة المتقدمة مع قاعدة البيانات
    # -------------------------------------------------------------------
    
    def sync_services_advanced(self, db_handler):
        """
        مزامنة متقدمة: جلب الخدمات من جميع السيرفرات وتخزينها في قاعدة البيانات.
        """
        print("\n" + "="*60)
        print("🔄 بدء المزامنة المتقدمة مع قاعدة البيانات")
        print("="*60)
        
        db_handler.clear_old_services()
        all_services = self.fetch_all_services()
        
        if not all_services:
            return {'success': False, 'message': 'لم يتم جلب أي خدمات', 'total': 0}
        
        saved_count = 0
        categories_count = {}
        
        for service in all_services:
            try:
                db_handler.add_service(
                    service['api_name'],
                    service['api_service_id'],
                    service['name'],
                    service['name_ar'],
                    service['category'],
                    service['price'],
                    service['original_price'],
                    service['min'],
                    service['max'],
                    service['api_type'],
                    '',
                    service['speed'],
                    service['country']
                )
                saved_count += 1
                cat = service['category']
                categories_count[cat] = categories_count.get(cat, 0) + 1
            except Exception as e:
                print(f"⚠️ خطأ في حفظ الخدمة: {e}")
                continue
        
        self.services_cache = all_services
        self.cache_timestamp = datetime.now()
        
        print("\n" + "="*60)
        print(f"✅ اكتملت المزامنة المتقدمة!")
        print(f"   • تم حفظ {saved_count} خدمة في قاعدة البيانات")
        print(f"   • عدد التصنيفات: {len(categories_count)}")
        print("="*60)
        
        return {
            'success': True,
            'total': saved_count,
            'categories': categories_count,
            'api_stats': self.api_stats,
            'timestamp': datetime.now()
        }
    
    # -------------------------------------------------------------------
    # دوال الحصول على معلومات وإحصائيات
    # -------------------------------------------------------------------
    
    def get_api_stats(self):
        """
        جلب إحصائيات جميع السيرفرات.
        """
        stats_list = []
        for api_name, api_config in self.apis.items():
            stat = self.api_stats.get(api_name, {})
            stats_list.append({
                'name': api_config['name'],
                'type': api_config['type'],
                'services': stat.get('services_count', 0),
                'success_rate': self.calculate_success_rate(api_name),
                'last_sync': stat.get('last_sync'),
                'total_requests': stat.get('total_requests', 0),
                'successful_requests': stat.get('successful_requests', 0),
                'failed_requests': stat.get('failed_requests', 0)
            })
        return stats_list
    
    def calculate_success_rate(self, api_name):
        """
        حساب نسبة نجاح طلبات سيرفر معين.
        """
        stat = self.api_stats.get(api_name, {})
        total = stat.get('total_requests', 0)
        if total == 0:
            return 0
        successful = stat.get('successful_requests', 0)
        return round((successful / total) * 100, 2)
    
    def get_cache_info(self):
        """
        الحصول على معلومات عن الكاش.
        """
        if not self.services_cache:
            return "📭 لا توجد بيانات مخزنة في الكاش"
        
        count = len(self.services_cache)
        if self.cache_timestamp:
            time_diff = datetime.now() - self.cache_timestamp
            minutes = int(time_diff.total_seconds() / 60)
            return f"📦 {count} خدمة مخزنة - آخر تحديث منذ {minutes} دقيقة"
        return f"📦 {count} خدمة مخزنة"
    
    def clear_cache(self):
        """مسح الكاش."""
        self.services_cache = []
        self.cache_timestamp = None
        print("🧹 تم مسح الكاش بنجاح")

# نهاية كلاس SMMAPI
