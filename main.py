# ==================== Amr Digital Empire - الملف الرئيسي للبوت ====================
# الإمبراطور: @AmrDigital
# تاريخ الإنشاء: 1 مارس 2026
# الإصدار: 1.0

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import threading
from datetime import datetime, timedelta

# استيراد الكلاسات من الملفات الأخرى
from config import *
from database import Database
from api_handler import SMMAPI

# ==================== تهيئة البوت والكلاسات ====================

print("🚀 جاري تهيئة البوت...")

bot = telebot.TeleBot(BOT_TOKEN)
db = Database(DB_FILE)
api_handler = SMMAPI()

# متغيرات عامة لتخزين حالات المستخدمين والبيانات المؤقتة
user_states = {}      # قاموس لتخزين حالة كل مستخدم (في أي مرحلة هو)
temp_data = {}        # قاموس لتخزين البيانات المؤقتة أثناء الطلبات
user_language = {}    # قاموس مؤقت للغة (الأساس في قاعدة البيانات)

# ==================== دوال التحقق المساعدة ====================

def check_channel(user_id):
    """
    التحقق من أن المستخدم مشترك في القناة الإجبارية.
    """
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"خطأ في التحقق من القناة للمستخدم {user_id}: {e}")
        return False

def is_admin(user_id):
    """
    التحقق مما إذا كان المستخدم هو الأدمن.
    """
    return user_id == ADMIN_ID

def get_user_language(user_id):
    """
    الحصول على لغة المستخدم (من قاعدة البيانات أو من الذاكرة المؤقتة).
    """
    if user_id in user_language:
        return user_language[user_id]
    
    user = db.get_user(user_id)
    if user and user['language']:
        lang = user['language']
    else:
        lang = 'ar'  # اللغة الافتراضية
    
    user_language[user_id] = lang
    return lang

def set_user_language(user_id, lang):
    """
    تعيين لغة المستخدم وحفظها في قاعدة البيانات.
    """
    if lang in ['ar', 'en']:
        user_language[user_id] = lang
        db.update_user_language(user_id, lang)
        return True
    return False

def translate(user_id, text_ar, text_en):
    """
    ترجمة نص بناءً على لغة المستخدم.
    """
    lang = get_user_language(user_id)
    return text_ar if lang == 'ar' else text_en

# ==================== لوحات المفاتيح (Keyboards) ====================

def main_menu_keyboard(user_id):
    """
    القائمة الرئيسية الكبيرة (Inline Buttons) حسب طلبك.
    """
    lang = get_user_language(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    
    if lang == 'ar':
        markup.add(
            InlineKeyboardButton("🎁 الخدمات المجانية", callback_data="free_service"),
            InlineKeyboardButton("🛍️ الخدمات", callback_data="services_main")
        )
        markup.add(
            InlineKeyboardButton("🏆 المسابقات", callback_data="competitions"),
            InlineKeyboardButton("⏰ مواعيد التحديثات", callback_data="updates")
        )
        markup.add(
            InlineKeyboardButton("💰 محفظتي", callback_data="wallet"),
            InlineKeyboardButton("📦 طلباتي", callback_data="my_orders")
        )
        markup.add(
            InlineKeyboardButton("👥 الإحالة", callback_data="referral"),
            InlineKeyboardButton("📤 إيداع", callback_data="deposit")
        )
        markup.add(
            InlineKeyboardButton("📞 الدعم الفني", callback_data="support"),
            InlineKeyboardButton("🌐 اللغة", callback_data="change_lang")
        )
        markup.add(
            InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")
        )
    else:
        markup.add(
            InlineKeyboardButton("🎁 Free Service", callback_data="free_service"),
            InlineKeyboardButton("🛍️ Services", callback_data="services_main")
        )
        markup.add(
            InlineKeyboardButton("🏆 Competitions", callback_data="competitions"),
            InlineKeyboardButton("⏰ Updates", callback_data="updates")
        )
        markup.add(
            InlineKeyboardButton("💰 Wallet", callback_data="wallet"),
            InlineKeyboardButton("📦 My Orders", callback_data="my_orders")
        )
        markup.add(
            InlineKeyboardButton("👥 Referral", callback_data="referral"),
            InlineKeyboardButton("📤 Deposit", callback_data="deposit")
        )
        markup.add(
            InlineKeyboardButton("📞 Support", callback_data="support"),
            InlineKeyboardButton("🌐 Language", callback_data="change_lang")
        )
        markup.add(
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        )
    
    return markup

def services_main_keyboard(user_id):
    """
    قائمة السيرفرات (عند الضغط على 🛍️ الخدمات)
    """
    lang = get_user_language(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    
    for api_name, api_config in APIS.items():
        services_count = db.get_services_count(api_name)
        if services_count == 0:
            continue
        button_text = f"{api_config['emoji']} {api_config['name']} ({services_count})"
        markup.add(InlineKeyboardButton(button_text, callback_data=f"api_{api_name}"))
    
    back_text = "🔙 رجوع" if lang == 'ar' else "🔙 Back"
    markup.add(InlineKeyboardButton(back_text, callback_data="main_menu"))
    
    return markup

def categories_keyboard(user_id, api_name):
    """
    قائمة التصنيفات لسيرفر معين.
    """
    lang = get_user_language(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    
    categories = db.get_categories_for_api(api_name)
    for cat_row in categories:
        cat_id = cat_row['category']
        cat_name = CATEGORIES.get(cat_id, cat_id)
        if lang == 'en':
            cat_name = cat_id.capitalize()
        services = db.get_services_by_category(api_name, cat_id)
        count = len(services) if services else 0
        if count > 0:
            markup.add(InlineKeyboardButton(f"{cat_name} ({count})", callback_data=f"cat_{api_name}_{cat_id}_1"))
    
    back_text = "🔙 رجوع للسيرفرات" if lang == 'ar' else "🔙 Back to APIs"
    markup.add(InlineKeyboardButton(back_text, callback_data="services_main"))
    
    return markup

def services_pagination_keyboard(user_id, api_name, category, page=1):
    """
    عرض خدمات تصنيف معين مع أزرار التنقل بين الصفحات.
    """
    lang = get_user_language(user_id)
    services = db.get_services_by_category(api_name, category)
    
    if not services:
        return None
    
    services.sort(key=lambda x: x['price'])
    
    per_page = SERVICES_PER_PAGE
    total_pages = (len(services) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = min(start + per_page, len(services))
    current = services[start:end]
    
    markup = InlineKeyboardMarkup(row_width=1)
    
    for service in current:
        short_name = service['name_ar'][:30] + "..." if len(service['name_ar']) > 30 else service['name_ar']
        button_text = f"{short_name} - 💰 {service['price']} ({service['min_quantity']}-{service['max_quantity']})"
        markup.add(InlineKeyboardButton(button_text, callback_data=f"service_{service['service_id']}"))
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ السابق" if lang == 'ar' else "◀️ Previous", callback_data=f"cat_{api_name}_{category}_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("التالي ▶️" if lang == 'ar' else "Next ▶️", callback_data=f"cat_{api_name}_{category}_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)
    
    back_text = "🔙 رجوع للتصنيفات" if lang == 'ar' else "🔙 Back to Categories"
    markup.add(InlineKeyboardButton(back_text, callback_data=f"api_{api_name}"))
    
    return markup

def back_button(user_id, callback_data="main_menu"):
    """
    زر رجوع بسيط.
    """
    lang = get_user_language(user_id)
    markup = InlineKeyboardMarkup()
    text = "🔙 رجوع" if lang == 'ar' else "🔙 Back"
    markup.add(InlineKeyboardButton(text, callback_data=callback_data))
    return markup

def language_choice_keyboard():
    """
    أزرار اختيار اللغة.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🇪🇬 العربية", callback_data="set_lang_ar"),
        InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")
    )
    return markup# ==================== أوامر البوت الأساسية ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "صديق"
    last_name = message.from_user.last_name

    # التحقق من وجود كود إحالة في رابط البدء
    referred_by = None
    if len(message.text.split()) > 1:
        try:
            referred_by = int(message.text.split()[1])
            if referred_by == user_id:
                referred_by = None
        except:
            pass

    # إضافة المستخدم إلى قاعدة البيانات
    db.add_user(user_id, username, first_name, last_name, referred_by)

    # التحقق من الاشتراك في القناة
    if not check_channel(user_id):
        lang = get_user_language(user_id)
        markup = InlineKeyboardMarkup()
        channel_url = f"https://t.me/{CHANNEL_USERNAME[1:]}"
        markup.add(InlineKeyboardButton(
            translate(user_id, "📢 اشترك في القناة", "📢 Join Channel"),
            url=channel_url
        ))
        markup.add(InlineKeyboardButton(
            translate(user_id, "✅ تحققت من الاشتراك", "✅ I've Joined"),
            callback_data="check_channel"
        ))
        bot.send_message(
            user_id,
            translate(user_id,
                f"👋 أهلاً بك {first_name}!\n\n⚠️ يجب الاشتراك في قناة الإمبراطورية أولاً:\n{CHANNEL_USERNAME}",
                f"👋 Welcome {first_name}!\n\n⚠️ You must join our channel first:\n{CHANNEL_USERNAME}"
            ),
            reply_markup=markup
        )
        return

    # تحديث حالة الاشتراك
    db.update_channel_status(user_id)

    # رسالة الترحيب
    lang = get_user_language(user_id)
    if lang == 'ar':
        welcome_text = (
            f"👑 *مرحباً بك في إمبراطورية Amr Digital*\n\n"
            f"أهلاً {first_name}! أنا بوت الخدمات الرسمي للإمبراطورية\n\n"
            f"✨ *ماذا يمكنني أن أقدم لك؟*\n"
            f"• 🎁 خدمة مجانية يومية (10 لايك / 100 مشاهدة)\n"
            f"• 🛍️ خدمات سوشيال ميديا من أفضل السيرفرات\n"
            f"• 👥 نظام إحالة: اكسب 5 جنيه عن كل صديق\n"
            f"• 🏆 مسابقات وجوائز يومية\n"
            f"• 💰 إيداع رصيد عبر فودافون كاش\n\n"
            f"📢 قناة الإمبراطورية: {CHANNEL_USERNAME}\n\n"
            f"استخدم الأزرار أدناه للتصفح 👇"
        )
    else:
        welcome_text = (
            f"👑 *Welcome to Amr Digital Empire*\n\n"
            f"Hello {first_name}! I am the official services bot\n\n"
            f"✨ *What I offer:*\n"
            f"• 🎁 Free daily service (10 likes / 100 views)\n"
            f"• 🛍️ Social media services from top servers\n"
            f"• 👥 Referral: earn 5 EGP per friend\n"
            f"• 🏆 Daily competitions & prizes\n"
            f"• 💰 Deposit via Vodafone Cash\n\n"
            f"📢 Channel: {CHANNEL_USERNAME}\n\n"
            f"Use the buttons below 👇"
        )

    bot.send_message(
        user_id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard(user_id)
    )

@bot.message_handler(commands=['lang', 'language'])
def language_command(message):
    user_id = message.from_user.id
    bot.send_message(
        user_id,
        translate(user_id, "اختر لغتك:", "Choose your language:"),
        reply_markup=language_choice_keyboard()
    )

# ==================== معالج الأزرار الشفافة (Callback Handler) ====================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data

    # التحقق من اشتراك القناة (ما عدا التحقق نفسه)
    if not check_channel(user_id) and not data.startswith(("check_channel", "set_lang")):
        bot.answer_callback_query(call.id, translate(user_id, "⚠️ يجب الاشتراك في القناة أولاً", "⚠️ You must join the channel first"), show_alert=True)
        return

    # ===== التحقق من القناة =====
    if data == "check_channel":
        if check_channel(user_id):
            db.update_channel_status(user_id)
            bot.answer_callback_query(call.id, translate(user_id, "✅ تم التحقق بنجاح", "✅ Verified successfully"))
            bot.delete_message(user_id, call.message.message_id)
            start_command(call.message)
        else:
            bot.answer_callback_query(call.id, translate(user_id, "❌ لم تشترك في القناة بعد", "❌ You haven't joined the channel yet"), show_alert=True)
        return

    # ===== تعيين اللغة =====
    if data.startswith("set_lang_"):
        lang = data.split("_")[2]
        set_user_language(user_id, lang)
        bot.answer_callback_query(call.id, translate(user_id, "✅ تم تغيير اللغة", "✅ Language changed"))
        bot.delete_message(user_id, call.message.message_id)
        start_command(call.message)
        return

    # ===== العودة للقائمة الرئيسية =====
    if data == "main_menu":
        bot.edit_message_text(
            translate(user_id, "القائمة الرئيسية:", "Main menu:"),
            user_id,
            call.message.message_id,
            reply_markup=main_menu_keyboard(user_id)
        )
        return

    # ===== عرض قائمة السيرفرات (الخدمات) =====
    if data == "services_main":
        bot.edit_message_text(
            translate(user_id, "اختر السيرفر:", "Choose server:"),
            user_id,
            call.message.message_id,
            reply_markup=services_main_keyboard(user_id)
        )
        return

    # ===== عرض تصنيفات سيرفر معين =====
    if data.startswith("api_"):
        api_name = data[4:]
        bot.edit_message_text(
            translate(user_id, "اختر التصنيف:", "Choose category:"),
            user_id,
            call.message.message_id,
            reply_markup=categories_keyboard(user_id, api_name)
        )
        return

    # ===== عرض خدمات تصنيف معين (مع الصفحات) =====
    if data.startswith("cat_"):
        parts = data.split("_")
        if len(parts) == 4:
            api_name = parts[1]
            category = parts[2]
            page = int(parts[3])
            keyboard = services_pagination_keyboard(user_id, api_name, category, page)
            if keyboard:
                bot.edit_message_text(
                    translate(user_id, "الخدمات المتاحة:", "Available services:"),
                    user_id,
                    call.message.message_id,
                    reply_markup=keyboard
                )
            else:
                bot.answer_callback_query(call.id, translate(user_id, "❌ لا توجد خدمات في هذا التصنيف", "❌ No services in this category"))
        return

    # ===== عرض تفاصيل خدمة معينة =====
    if data.startswith("service_"):
        service_id = int(data[8:])
        service = db.get_service(service_id)
        if not service:
            bot.answer_callback_query(call.id, translate(user_id, "❌ الخدمة غير متوفرة", "❌ Service not available"))
            return

        # تخزين الخدمة مؤقتاً
        temp_data[user_id] = {'service': dict(service)}
        user_states[user_id] = f"awaiting_link_{service_id}"

        lang = get_user_language(user_id)
        if lang == 'ar':
            text = (
                f"📦 *تفاصيل الخدمة*\n\n"
                f"*الاسم:* {service['name_ar']}\n"
                f"*السعر:* 💰 {service['price']} جنيه للوحدة\n"
                f"*الحد الأدنى:* {service['min_quantity']}\n"
                f"*الحد الأقصى:* {service['max_quantity']}\n"
                f"*السرعة:* {service.get('speed', '⏱️ عادي')}\n\n"
                f"📝 أرسل الرابط الآن:"
            )
        else:
            text = (
                f"📦 *Service Details*\n\n"
                f"*Name:* {service['name']}\n"
                f"*Price:* 💰 {service['price']} per unit\n"
                f"*Min:* {service['min_quantity']}\n"
                f"*Max:* {service['max_quantity']}\n"
                f"*Speed:* {service.get('speed', '⏱️ Normal')}\n\n"
                f"📝 Send the link now:"
            )

        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=back_button(user_id, f"api_{service['api_name']}")
        )
        return

    # ===== الخدمة المجانية اليومية =====
    if data == "free_service":
        # التحقق من الاشتراك في القناة
        if not check_channel(user_id):
            bot.answer_callback_query(call.id, translate(user_id, "⚠️ يجب الاشتراك في القناة أولاً", "⚠️ You must join the channel first"), show_alert=True)
            return

        # التحقق من إمكانية طلب خدمة مجانية اليوم
        can_request, hours_left = db.can_request_free_service(user_id)
        if not can_request:
            hours = int(hours_left)
            minutes = int((hours_left - hours) * 60)
            time_msg = f"{hours} ساعة و {minutes} دقيقة" if hours > 0 else f"{minutes} دقيقة"
            bot.answer_callback_query(
                call.id,
                translate(user_id, f"⏳ يمكنك طلب خدمة مجانية بعد {time_msg}", f"⏳ You can request a free service after {time_msg}"),
                show_alert=True
            )
            return

        # جلب أرخص الخدمات المجانية
        free_services = api_handler.get_cheapest_free_service(db)
        if not free_services:
            bot.answer_callback_query(call.id, translate(user_id, "❌ لا توجد خدمات مجانية حالياً", "❌ No free services available"), show_alert=True)
            return

        # عرض قائمة الخدمات المجانية (أرخص 5)
        markup = InlineKeyboardMarkup(row_width=1)
        for svc in free_services[:5]:
            short_name = svc['name_ar'][:30]
            markup.add(InlineKeyboardButton(
                f"{short_name} - 💰 {svc['price']}",
                callback_data=f"free_select_{svc['service_id']}"
            ))
        markup.add(InlineKeyboardButton(translate(user_id, "🔙 رجوع", "🔙 Back"), callback_data="main_menu"))

        bot.edit_message_text(
            translate(user_id, "🎁 اختر الخدمة المجانية:", "🎁 Choose free service:"),
            user_id,
            call.message.message_id,
            reply_markup=markup
        )
        return    # ===== اختيار خدمة مجانية محددة =====
    if data.startswith("free_select_"):
        service_id = int(data[12:])
        service = db.get_service(service_id)
        if not service:
            bot.answer_callback_query(call.id, translate(user_id, "❌ الخدمة غير متوفرة", "❌ Service not available"))
            return

        temp_data[user_id] = {'service': dict(service), 'is_free': True}
        user_states[user_id] = f"awaiting_free_quantity_{service_id}"
        
        bot.edit_message_text(
            translate(user_id, "🔢 أرسل الكمية (الحد الأقصى حسب نوع الخدمة)", "🔢 Send quantity (max depends on service type)"),
            user_id,
            call.message.message_id,
            reply_markup=back_button(user_id)
        )
        return

    # ===== عرض المسابقات =====
    if data == "competitions":
        competitions = db.get_active_competitions()
        if not competitions:
            bot.answer_callback_query(call.id, translate(user_id, "🏆 لا توجد مسابقات نشطة", "🏆 No active competitions"), show_alert=True)
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for comp in competitions:
            name = comp['name_ar'] if get_user_language(user_id) == 'ar' else comp['name']
            markup.add(InlineKeyboardButton(
                f"{name} - 💰 {comp['prize']}",
                callback_data=f"comp_{comp['comp_id']}"
            ))
        markup.add(InlineKeyboardButton(translate(user_id, "🔙 رجوع", "🔙 Back"), callback_data="main_menu"))

        bot.edit_message_text(
            translate(user_id, "🏆 المسابقات النشطة:", "🏆 Active competitions:"),
            user_id,
            call.message.message_id,
            reply_markup=markup
        )
        return

    # ===== عرض تفاصيل مسابقة معينة =====
    if data.startswith("comp_"):
        comp_id = int(data[5:])
        comp = db.fetch_one("SELECT * FROM competitions WHERE comp_id = ?", (comp_id,))
        if not comp:
            bot.answer_callback_query(call.id, translate(user_id, "❌ المسابقة غير موجودة", "❌ Competition not found"))
            return

        lang = get_user_language(user_id)
        if lang == 'ar':
            text = (
                f"🏆 *{comp['name_ar']}*\n\n"
                f"{comp['description']}\n\n"
                f"💰 الجائزة: {comp['prize']} جنيه\n"
                f"👥 عدد الفائزين: {comp['winners_count']}\n"
                f"⏰ تنتهي: {comp['end_date']}"
            )
        else:
            text = (
                f"🏆 *{comp['name']}*\n\n"
                f"{comp['description']}\n\n"
                f"💰 Prize: {comp['prize']} EGP\n"
                f"👥 Winners: {comp['winners_count']}\n"
                f"⏰ Ends: {comp['end_date']}"
            )

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            translate(user_id, "✅ اشترك", "✅ Join"),
            callback_data=f"join_comp_{comp_id}"
        ))
        markup.add(InlineKeyboardButton(translate(user_id, "🔙 رجوع", "🔙 Back"), callback_data="competitions"))

        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    # ===== الانضمام لمسابقة =====
    if data.startswith("join_comp_"):
        comp_id = int(data[10:])
        db.join_competition(comp_id, user_id)
        bot.answer_callback_query(call.id, translate(user_id, "✅ تم الانضمام للمسابقة", "✅ Joined the competition"))
        bot.delete_message(user_id, call.message.message_id)
        return

    # ===== مواعيد التحديثات =====
    if data == "updates":
        bot.edit_message_text(
            UPDATE_SCHEDULE,
            user_id,
            call.message.message_id,
            reply_markup=back_button(user_id)
        )
        return

    # ===== المحفظة =====
    if data == "wallet":
        user = db.get_user(user_id)
        if not user:
            return
        balance = user['balance']
        total_deposits = user['total_deposits']
        total_spent = user['total_spent']
        text = translate(
            user_id,
            f"💰 *محفظتك*\n\nالرصيد الحالي: {balance} جنيه\nإجمالي الودائع: {total_deposits} جنيه\nإجمالي المصروفات: {total_spent} جنيه",
            f"💰 *Your Wallet*\n\nCurrent balance: {balance} EGP\nTotal deposits: {total_deposits} EGP\nTotal spent: {total_spent} EGP"
        )
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=back_button(user_id)
        )
        return

    # ===== طلباتي =====
    if data == "my_orders":
        orders = db.get_user_orders(user_id, limit=10)
        if not orders:
            bot.answer_callback_query(call.id, translate(user_id, "📭 لا توجد طلبات سابقة", "📭 No previous orders"), show_alert=True)
            return

        text = translate(user_id, "📦 *آخر 10 طلبات*\n\n", "📦 *Last 10 orders*\n\n")
        for o in orders:
            status_emoji = {
                'pending': '⏳',
                'processing': '⚙️',
                'completed': '✅',
                'canceled': '❌'
            }.get(o['status'], '⏳')
            text += f"{status_emoji} #{o['order_id']}: {o['service_name'][:20]}... - {o['quantity']} - {o['price']} جنيه\n"
        
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=back_button(user_id)
        )
        return

    # ===== نظام الإحالة =====
    if data == "referral":
        user = db.get_user(user_id)
        if not user:
            return
        referral_code = user['referral_code']
        referral_count = db.get_referral_count(user_id)
        referral_earnings = referral_count * REFERRAL_BONUS
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        
        text = translate(
            user_id,
            f"👥 *نظام الإحالة*\n\nلكل صديق تسجله تحصل على {REFERRAL_BONUS} جنيه\n\nعدد الأصدقاء: {referral_count}\nأرباحك: {referral_earnings} جنيه\n\nرابط الإحالة الخاص بك:\n`{referral_link}`\n\n⚠️ الحد الأدنى للسحب: {MIN_WITHDRAW} جنيه",
            f"👥 *Referral System*\n\nEarn {REFERRAL_BONUS} EGP per friend\n\nFriends: {referral_count}\nEarnings: {referral_earnings} EGP\n\nYour referral link:\n`{referral_link}`\n\n⚠️ Minimum withdraw: {MIN_WITHDRAW} EGP"
        )
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=back_button(user_id)
        )
        return

    # ===== إيداع رصيد =====
    if data == "deposit":
        text = translate(
            user_id,
            f"📤 *إيداع رصيد*\n\nطريقة الدفع: {PAYMENT_METHOD}\nالرقم: `{MY_PHONE_NUMBER}`\n\nأرسل صورة الإيصال مع كتابة المبلغ في التعليق.\nمثال: 100",
            f"📤 *Deposit Funds*\n\nPayment method: {PAYMENT_METHOD}\nNumber: `{MY_PHONE_NUMBER}`\n\nSend receipt image with amount in caption.\nExample: 100"
        )
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=back_button(user_id)
        )
        return

    # ===== الدعم الفني =====
    if data == "support":
        text = translate(
            user_id,
            f"📞 *الدعم الفني*\n\nللتواصل مع الإدارة: @AmrDigital\nقناة الإمبراطورية: {CHANNEL_USERNAME}",
            f"📞 *Support*\n\nContact admin: @AmrDigital\nEmpire channel: {CHANNEL_USERNAME}"
        )
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=back_button(user_id)
        )
        return

    # ===== تغيير اللغة =====
    if data == "change_lang":
        bot.edit_message_text(
            translate(user_id, "اختر لغتك:", "Choose your language:"),
            user_id,
            call.message.message_id,
            reply_markup=language_choice_keyboard()
        )
        return

    # ===== الإعدادات (قيد التطوير) =====
    if data == "settings":
        bot.answer_callback_query(call.id, translate(user_id, "⚙️ الإعدادات قيد التطوير", "⚙️ Settings under development"), show_alert=True)
        return

    # ===== تأكيد الطلب (مدفوع) =====
    if data == "confirm_order":
        if user_id not in temp_data or 'service' not in temp_data[user_id]:
            bot.answer_callback_query(call.id, translate(user_id, "❌ خطأ في البيانات", "❌ Data error"))
            return

        data_dict = temp_data[user_id]
        service = data_dict['service']
        link = data_dict.get('link')
        quantity = data_dict.get('quantity')
        total_price = data_dict.get('total_price')

        if not link or not quantity or not total_price:
            bot.answer_callback_query(call.id, translate(user_id, "❌ بيانات غير مكتملة", "❌ Incomplete data"))
            return

        # التحقق من الرصيد
        balance = db.get_balance(user_id)
        if balance < total_price:
            bot.edit_message_text(
                translate(user_id, f"❌ رصيدك غير كافٍ\nالمطلوب: {total_price} جنيه\nرصيدك: {balance} جنيه", f"❌ Insufficient balance\nRequired: {total_price} EGP\nYour balance: {balance} EGP"),
                user_id,
                call.message.message_id,
                reply_markup=back_button(user_id)
            )
            if user_id in user_states:
                del user_states[user_id]
            if user_id in temp_data:
                del temp_data[user_id]
            return

        # خصم الرصيد
        if not db.deduct_balance(user_id, total_price):
            bot.answer_callback_query(call.id, translate(user_id, "❌ فشل خصم الرصيد", "❌ Balance deduction failed"))
            return

        # تقديم الطلب عبر API
        api_order_id = api_handler.place_order(
            service['api_name'],
            service['api_service_id'],
            link,
            quantity
        )

        # حفظ الطلب في قاعدة البيانات
        order_id = db.create_order(
            user_id,
            service['service_id'],
            link,
            quantity,
            total_price,
            service['api_name'],
            api_order_id
        )

        # رسالة النجاح
        success_text = translate(
            user_id,
            f"✅ *تم تقديم الطلب بنجاح!*\n\n📋 رقم الطلب: #{order_id}\n💰 المبلغ: {total_price} جنيه\n📊 الرصيد المتبقي: {db.get_balance(user_id)} جنيه",
            f"✅ *Order placed successfully!*\n\n📋 Order ID: #{order_id}\n💰 Amount: {total_price} EGP\n📊 Remaining balance: {db.get_balance(user_id)} EGP"
        )

        bot.edit_message_text(
            success_text,
            user_id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=back_button(user_id)
        )

        # إشعار الأدمن
        if is_admin(ADMIN_ID):
            try:
                user = db.get_user(user_id)
                username = f"@{user['username']}" if user and user['username'] else f"ID: {user_id}"
                bot.send_message(
                    ADMIN_ID,
                    f"🆕 *New Order*\n\nUser: {username}\nOrder ID: #{order_id}\nAmount: {total_price} EGP",
                    parse_mode='Markdown'
                )
            except:
                pass

        # تنظيف البيانات
        if user_id in user_states:
            del user_states[user_id]
        if user_id in temp_data:
            del temp_data[user_id]
        return

    # ===== إلغاء الطلب =====
    if data == "cancel_order":
        if user_id in user_states:
            del user_states[user_id]
        if user_id in temp_data:
            del temp_data[user_id]
        bot.edit_message_text(
            translate(user_id, "❌ تم إلغاء الطلب", "❌ Order cancelled"),
            user_id,
            call.message.message_id,
            reply_markup=back_button(user_id)
        )
        return

# ==================== معالج النصوص (Message Handler) ====================

@bot.message_handler(func=lambda message: True)
def message_handler(message):
    user_id = message.from_user.id
    text = message.text

    # طباعة للتشخيص
    print(f"📩 رسالة واردة من {user_id}: {text}")

    # التحقق من اشتراك القناة
    if not check_channel(user_id):
        markup = InlineKeyboardMarkup()
        channel_url = f"https://t.me/{CHANNEL_USERNAME[1:]}"
        markup.add(InlineKeyboardButton(
            translate(user_id, "📢 اشترك في القناة", "📢 Join Channel"),
            url=channel_url
        ))
        markup.add(InlineKeyboardButton(
            translate(user_id, "✅ تحققت من الاشتراك", "✅ I've Joined"),
            callback_data="check_channel"
        ))
        bot.send_message(
            user_id,
            translate(user_id,
                f"⚠️ يجب الاشتراك في القناة أولاً:\n{CHANNEL_USERNAME}",
                f"⚠️ You must join the channel first:\n{CHANNEL_USERNAME}"
            ),
            reply_markup=markup
        )
        return

    # ===== معالجة حالات المستخدم (انتظار إدخال بيانات) =====
    if user_id in user_states:
        state = user_states[user_id]

        # حالة انتظار رابط الخدمة المدفوعة
        if state.startswith("awaiting_link_"):
            service_id = int(state[14:])
            service = db.get_service(service_id)
            if not service:
                bot.send_message(user_id, translate(user_id, "❌ الخدمة غير متوفرة", "❌ Service not available"))
                del user_states[user_id]
                if user_id in temp_data:
                    del temp_data[user_id]
                return

            temp_data[user_id]['link'] = text
            user_states[user_id] = f"awaiting_quantity_{service_id}"
            bot.send_message(
                user_id,
                translate(
                    user_id,
                    f"🔢 أرسل الكمية (من {service['min_quantity']} إلى {service['max_quantity']}):",
                    f"🔢 Send quantity (from {service['min_quantity']} to {service['max_quantity']}):"
                )
            )
            return

        # حالة انتظار كمية الخدمة المدفوعة
        if state.startswith("awaiting_quantity_"):
            service_id = int(state[18:])
            service = db.get_service(service_id)
            if not service:
                bot.send_message(user_id, translate(user_id, "❌ الخدمة غير متوفرة", "❌ Service not available"))
                del user_states[user_id]
                if user_id in temp_data:
                    del temp_data[user_id]
                return

            try:
                quantity = int(text)
                if quantity < service['min_quantity'] or quantity > service['max_quantity']:
                    bot.send_message(
                        user_id,
                        translate(
                            user_id,
                            f"❌ الكمية غير صالحة. يجب أن تكون بين {service['min_quantity']} و {service['max_quantity']}",
                            f"❌ Invalid quantity. Must be between {service['min_quantity']} and {service['max_quantity']}"
                        )
                    )
                    return

                total_price = quantity * service['price']
                temp_data[user_id]['quantity'] = quantity
                temp_data[user_id]['total_price'] = total_price

                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton(translate(user_id, "✅ تأكيد", "✅ Confirm"), callback_data="confirm_order"),
                    InlineKeyboardButton(translate(user_id, "❌ إلغاء", "❌ Cancel"), callback_data="cancel_order")
                )

                bot.send_message(
                    user_id,
                    translate(
                        user_id,
                        f"📋 *ملخص الطلب*\n\nالخدمة: {service['name_ar']}\nالرابط: {temp_data[user_id]['link']}\nالكمية: {quantity}\nالسعر الإجمالي: 💰 {total_price} جنيه\n\nهل أنت متأكد؟",
                        f"📋 *Order Summary*\n\nService: {service['name']}\nLink: {temp_data[user_id]['link']}\nQuantity: {quantity}\nTotal: 💰 {total_price} EGP\n\nAre you sure?"
                    ),
                    parse_mode='Markdown',
                    reply_markup=markup
                )
            except ValueError:
                bot.send_message(user_id, translate(user_id, "❌ أرسل رقماً صحيحاً", "❌ Send a valid number"))
            return

        # حالة انتظار كمية الخدمة المجانية
        if state.startswith("awaiting_free_quantity_"):
            service_id = int(state[23:])
            service = db.get_service(service_id)
            if not service:
                bot.send_message(user_id, translate(user_id, "❌ الخدمة غير متوفرة", "❌ Service not available"))
                del user_states[user_id]
                if user_id in temp_data:
                    del temp_data[user_id]
                return

            try:
                quantity = int(text)
                # التحقق من الحدود المسموحة للخدمة المجانية
                allowed, adjusted_qty = api_handler.check_free_service_limit(service['name'], quantity)
                if not allowed:
                    bot.send_message(
                        user_id,
                        translate(
                            user_id,
                            f"⚠️ الكمية المطلوبة أكبر من الحد المسموح. سيتم تعديلها إلى {adjusted_qty}.",
                            f"⚠️ Requested quantity exceeds limit. Will be adjusted to {adjusted_qty}."
                        )
                    )
                    quantity = adjusted_qty

                # تنفيذ الطلب المجاني (بدون خصم رصيد)
                api_order_id = api_handler.place_order(
                    service['api_name'],
                    service['api_service_id'],
                    "free_service",  # رابط وهمي
                    quantity
                )

                # تسجيل الطلب كخدمة مجانية
                db.add_free_request(user_id, service['category'], quantity)

                bot.send_message(
                    user_id,
                    translate(
                        user_id,
                        f"✅ *تم طلب الخدمة المجانية بنجاح!*\n\nالخدمة: {service['name_ar']}\nالكمية: {quantity}\n\nيمكنك طلب خدمة مجانية أخرى بعد 24 ساعة.",
                        f"✅ *Free service requested successfully!*\n\nService: {service['name']}\nQuantity: {quantity}\n\nYou can request another free service after 24 hours."
                    ),
                    parse_mode='Markdown'
                )

                # إشعار الأدمن (اختياري)
                if is_admin(ADMIN_ID):
                    bot.send_message(
                        ADMIN_ID,
                        f"🎁 Free service used\nUser: {user_id}\nService: {service['name_ar']}\nQty: {quantity}"
                    )

            except ValueError:
                bot.send_message(user_id, translate(user_id, "❌ أرسل رقماً صحيحاً", "❌ Send a valid number"))
            finally:
                # تنظيف البيانات
                if user_id in user_states:
                    del user_states[user_id]
                if user_id in temp_data:
                    del temp_data[user_id]
            return

    # إذا لم يتطابق أي شيء، نرسل القائمة الرئيسية
    bot.send_message(
        user_id,
        translate(user_id, "القائمة الرئيسية:", "Main menu:"),
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== معالج الصور (لإيداع الرصيد) ====================

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    user_id = message.from_user.id
    if not check_channel(user_id):
        return

    caption = message.caption
    if not caption:
        bot.send_message(
            user_id,
            translate(user_id, "❌ أرسل المبلغ في التعليق مع الصورة", "❌ Send the amount in caption with the image")
        )
        return

    try:
        amount = float(caption.strip())
        if amount <= 0:
            raise ValueError
    except:
        bot.send_message(
            user_id,
            translate(user_id, "❌ المبلغ غير صحيح", "❌ Invalid amount")
        )
        return

    file_id = message.photo[-1].file_id
    payment_id = db.add_payment(user_id, amount, file_id)

    bot.send_message(
        user_id,
        translate(
            user_id,
            f"✅ تم إرسال طلب الشحن بقيمة {amount} جنيه. في انتظار مراجعة الإدارة.",
            f"✅ Deposit request of {amount} EGP sent. Waiting for admin review."
        )
    )

    # إرسال للأدمن
    if is_admin(ADMIN_ID):
        user = db.get_user(user_id)
        username = f"@{user['username']}" if user and user['username'] else f"ID: {user_id}"
        caption_admin = f"💳 طلب شحن جديد\nالمستخدم: {username}\nالمبلغ: {amount} جنيه"
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ قبول", callback_data=f"approve_payment_{payment_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_payment_{payment_id}")
        )
        bot.send_photo(ADMIN_ID, file_id, caption=caption_admin, reply_markup=markup)

# ==================== دوال معالجة الدفع (للأدمن) ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_payment_"))
def approve_payment_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ غير مصرح", show_alert=True)
        return

    payment_id = int(call.data[16:])
    payment = db.get_payment(payment_id)
    if not payment:
        bot.answer_callback_query(call.id, "❌ الدفع غير موجود")
        return

    db.approve_payment(payment_id, user_id)
    bot.answer_callback_query(call.id, "✅ تم قبول الدفع")
    bot.delete_message(user_id, call.message.message_id)

    # إشعار المستخدم
    try:
        bot.send_message(
            payment['user_id'],
            translate(payment['user_id'], f"✅ تم قبول طلب الشحن بقيمة {payment['amount']} جنيه", f"✅ Deposit of {payment['amount']} EGP approved")
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_payment_"))
def reject_payment_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ غير مصرح", show_alert=True)
        return

    payment_id = int(call.data[15:])
    payment = db.get_payment(payment_id)
    if not payment:
        bot.answer_callback_query(call.id, "❌ الدفع غير موجود")
        return

    db.reject_payment(payment_id, user_id, "رفض من الأدمن")
    bot.answer_callback_query(call.id, "❌ تم رفض الدفع")
    bot.delete_message(user_id, call.message.message_id)

    # إشعار المستخدم
    try:
        bot.send_message(
            payment['user_id'],
            translate(payment['user_id'], f"❌ تم رفض طلب الشحن بقيمة {payment['amount']} جنيه", f"❌ Deposit of {payment['amount']} EGP rejected")
        )
    except:
        pass

# ==================== دالة المزامنة التلقائية (تعمل في الخلفية) ====================

def auto_sync_services():
    """تشغيل مزامنة الخدمات كل 6 ساعات"""
    while True:
        try:
            print("🔄 بدء المزامنة التلقائية للخدمات...")
            result = api_handler.sync_services_advanced(db)
            if result['success']:
                print(f"✅ تمت المزامنة التلقائية بنجاح: {result['total']} خدمة")
            else:
                print("❌ فشلت المزامنة التلقائية")
            time.sleep(6 * 60 * 60)  # 6 ساعات
        except Exception as e:
            print(f"خطأ في المزامنة التلقائية: {e}")
            time.sleep(60 * 60)  # انتظر ساعة ثم حاول مجددًا

# ==================== بدء تشغيل البوت ====================

if __name__ == "__main__":
    print("=" * 60)
    print("👑 Amr Digital Empire Bot - جاهز للتشغيل")
    print("=" * 60)
    print(f"✅ توكن البوت: {BOT_TOKEN[:15]}...{BOT_TOKEN[-10:]}")
    print(f"✅ معرف الإمبراطور: {ADMIN_ID}")
    print(f"✅ قناة الإمبراطورية: {CHANNEL_USERNAME}")
    print(f"✅ عدد السيرفرات: {len(APIS)}")
    print(f"✅ أقل سعر في البوت: {MINIMUM_PRICE} جنيه")
    print("=" * 60)

    # بدء خيط المزامنة التلقائية في الخلفية
    sync_thread = threading.Thread(target=auto_sync_services, daemon=True)
    sync_thread.start()

    print("🚀 البوت يعمل الآن...")
    print("=" * 60)

    # بدء البوت
    bot.infinity_polling()
