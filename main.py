import os
import json
import asyncio
from typing import Dict, Any, List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from yt_dlp import YoutubeDL

DATA_FILE = "data.json"

# -------------------------
# تحميل/حفظ البيانات
# -------------------------
def load_data() -> Dict[str, Any]:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # القيم الافتراضية (تقدر تغيّرها هنا مباشرة)
    data = {
        "token": "8024366013:AAFBEV341PKd2cYgQ7jexoF6n37gq2Lx7fY",
        "admins": [7473286060, 5497769888],
        "channels": ["Syria_7X"],  # بدون @
        "users": {}
    }
    save_data(data)
    return data

def save_data(d: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

data = load_data()
TOKEN = data.get("token", "").strip()
if not TOKEN:
    raise RuntimeError("ضع توكن البوت داخل data.json في المفتاح token.")

# -------------------------
# نص الترحيب
# -------------------------
WELCOME = (
    "مِࢪحِبَاެ عَࢪ࣪يَࢪ࣪يَ👋.\n"
    "اެنِتَ اެݪاެنِ فَيَ اެسِࢪعَ بَۅٛتَ ݪݪتَحِمِيَݪ مِنِ جَمِيَعَ اެݪمِۅٛاقِعَ .\n\n"
    "- لتحميل من تيك توك فقط ارسل رابط المنشور .👁‍🗨\n\n"
    "- لتحميل فديو وصور من انستا فقط ارسل رابط المنشور او يوزر الحساب .📲\n\n"
    "- لتحميل من يوتيوب ارسل اسم الاغنيه او رابط 🎙 .\n\n"
    "- للتحميل من اي برنامج فقط ارسل الرابط وتدلل🗿.\n\n"
    "بوتنا بدون حقوق ^← @MOKAF700 »»» @XS5_S"
)

# -------------------------
# أدوات مساعدة
# -------------------------
def is_admin(user_id: int) -> bool:
    return int(user_id) in data["admins"]

def add_user(update: Update) -> None:
    u = update.effective_user
    if not u:
        return
    uid = str(u.id)
    if uid not in data["users"]:
        data["users"][uid] = {"username": u.username or "", "first_name": u.first_name or ""}
        save_data(data)

async def check_subscription_all(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> List[str]:
    """يرجع قائمة القنوات التي لم يشترك فيها المستخدم."""
    missing = []
    for ch in data["channels"]:
        try:
            member = await context.bot.get_chat_member(f"@{ch}", user_id)
            if member.status not in ("member", "administrator", "creator"):
                missing.append(ch)
        except Exception:
            # إذا القناة خاصة، أو البوت ليس مشرفًا، نعتبرها غير مشترَك فيها
            missing.append(ch)
    return missing

def human_channels_list(chs: List[str]) -> str:
    return "\n".join(f"@{c}" for c in chs)

# -------------------------
# تحميل عبر yt-dlp (إلى ملف مؤقت في /tmp مع تنظيف)
# -------------------------
def ytdlp_download(url_or_query: str) -> str:
    """
    يرجّع مسار الملف الذي تم تنزيله. يستخدم /tmp ويتعامل مع الروابط أو النصوص (بحث تلقائي).
    ننظّف الملف على المستلم.
    """
    outtmpl = "/tmp/video-%(id)s.%(ext)s"
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "auto",   # لو مش رابط، يعمل بحث تلقائي (يوتيوب)
        "retries": 3,
        "socket_timeout": 30,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_or_query, download=True)
        return ydl.prepare_filename(info)

# -------------------------
# لوحة الأدمن - أزرار
# -------------------------
def admin_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton("📊 الإحصائيات", callback_data="adm_stats"),
            InlineKeyboardButton("📢 القنوات", callback_data="adm_list_channels"),
        ],
        [
            InlineKeyboardButton("➕ إضافة قناة", callback_data="adm_add_channel"),
            InlineKeyboardButton("➖ حذف قناة", callback_data="adm_remove_channel"),
        ],
        [
            InlineKeyboardButton("👮‍♂️ عرض الأدمن", callback_data="adm_list_admins"),
            InlineKeyboardButton("➕ إضافة أدمن", callback_data="adm_add_admin"),
        ],
        [
            InlineKeyboardButton("➖ حذف أدمن", callback_data="adm_remove_admin"),
        ],
    ]
    return InlineKeyboardMarkup(kb)

# -------------------------
# أوامر عامة
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update)
    uid = update.effective_user.id

    if not is_admin(uid):
        missing = await check_subscription_all(uid, context)
        if missing:
            await update.message.reply_text(
                "🚫 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n" + human_channels_list(missing)
            )
            return

    await update.message.reply_text(WELCOME)
    # زر لوحة الأدمن لمن هو أدمن
    if is_admin(uid):
        await update.message.reply_text("لوحة تحكم الأدمن:", reply_markup=admin_keyboard())

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("لوحة تحكم الأدمن:", reply_markup=admin_keyboard())

# -------------------------
# كول باك الأزرار (لوحة الأدمن)
# -------------------------
async def on_admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return
    q = update.callback_query
    uid = q.from_user.id
    if not is_admin(uid):
        await q.answer("غير مسموح", show_alert=True)
        return

    await q.answer()  # إغلاق "جارٍ التحميل"

    data_flag = q.data

    # عرض إحصائيات بسيطة
    if data_flag == "adm_stats":
        users_count = len(data.get("users", {}))
        channels_count = len(data.get("channels", []))
        admins_count = len(data.get("admins", []))
        txt = f"📊 الإحصائيات:\n- المستخدمون: {users_count}\n- القنوات: {channels_count}\n- الأدمن: {admins_count}"
        await q.edit_message_text(txt, reply_markup=admin_keyboard())

    elif data_flag == "adm_list_channels":
        chs = data.get("channels", [])
        txt = "📢 القنوات:\n" + (human_channels_list(chs) if chs else "لا توجد قنوات.")
        await q.edit_message_text(txt, reply_markup=admin_keyboard())

    elif data_flag == "adm_list_admins":
        admins = [str(a) for a in data.get("admins", [])]
        txt = "👮‍♂️ الأدمن:\n" + ("\n".join(admins) if admins else "لا يوجد أدمن.")
        await q.edit_message_text(txt, reply_markup=admin_keyboard())

    # إضافة قناة: نطلب منه يرسل اسم القناة في رسالة تالية
    elif data_flag == "adm_add_channel":
        context.user_data["awaiting"] = ("add_channel", )
        await q.edit_message_text("أرسل الآن اسم القناة (بدون @):", reply_markup=admin_keyboard())

    elif data_flag == "adm_remove_channel":
        context.user_data["awaiting"] = ("remove_channel", )
        await q.edit_message_text("أرسل الآن اسم القناة (بدون @):", reply_markup=admin_keyboard())

    elif data_flag == "adm_add_admin":
        context.user_data["awaiting"] = ("add_admin", )
        await q.edit_message_text("أرسل الآن ID الأدمن الجديد (رقم):", reply_markup=admin_keyboard())

    elif data_flag == "adm_remove_admin":
        context.user_data["awaiting"] = ("remove_admin", )
        await q.edit_message_text("أرسل الآن ID الأدمن المراد حذفه (رقم):", reply_markup=admin_keyboard())

# التقاط الردود الإدارية (نصية) بعد الضغط على الأزرار
async def admin_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return False

    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False

    action = awaiting[0]
    txt = (update.message.text or "").strip()

    if action == "add_channel":
        ch = txt.replace("@", "")
        if ch and ch not in data["channels"]:
            data["channels"].append(ch)
            save_data(data)
            await update.message.reply_text(f"✅ تمت إضافة القناة: @{ch}")
        else:
            await update.message.reply_text("⚠️ القناة موجودة أو الاسم غير صالح.")
        context.user_data.pop("awaiting", None)
        await panel(update, context)
        return True

    if action == "remove_channel":
        ch = txt.replace("@", "")
        if ch in data["channels"]:
            data["channels"].remove(ch)
            save_data(data)
            await update.message.reply_text(f"🗑️ تمت إزالة القناة: @{ch}")
        else:
            await update.message.reply_text("⚠️ القناة غير موجودة بالقائمة.")
        context.user_data.pop("awaiting", None)
        await panel(update, context)
        return True

    if action == "add_admin":
        try:
            new_id = int(txt)
            if new_id not in data["admins"]:
                data["admins"].append(new_id)
                save_data(data)
                await update.message.reply_text(f"✅ تمت إضافة الأدمن: {new_id}")
            else:
                await update.message.reply_text("⚠️ هذا المستخدم موجود في قائمة الأدمن.")
        except ValueError:
            await update.message.reply_text("❗ ID غير صالح.")
        context.user_data.pop("awaiting", None)
        await panel(update, context)
        return True

    if action == "remove_admin":
        try:
            rm_id = int(txt)
            if rm_id in data["admins"]:
                data["admins"].remove(rm_id)
                save_data(data)
                await update.message.reply_text(f"🗑️ تمت إزالة الأدمن: {rm_id}")
            else:
                await update.message.reply_text("⚠️ هذا المستخدم ليس في قائمة الأدمن.")
        except ValueError:
            await update.message.reply_text("❗ ID غير صالح.")
        context.user_data.pop("awaiting", None)
        await panel(update, context)
        return True

    return False

# -------------------------
# استقبال الروابط/النصوص للتحميل
# -------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # لو كان هذا رد إداري مطلوب، نعالجه أولاً
    handled = await admin_text_flow(update, context)
    if handled:
        return

    add_user(update)
    uid = update.effective_user.id

    # التحقق من الاشتراك
    if not is_admin(uid):
        missing = await check_subscription_all(uid, context)
        if missing:
            await update.message.reply_text(
                "🚫 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n" + human_channels_list(missing)
            )
            return

    query = (update.message.text or "").strip()
    if not query:
        return

    await update.message.reply_text("⏳ جاري التحميل...")

    try:
        file_path = ytdlp_download(query)

        # حاول إرسال كـ فيديو، ولو فشل لأي سبب، أرسله كوثيقة
        try:
            with open(file_path, "rb") as f:
                await update.message.reply_video(video=InputFile(f))
        except Exception:
            with open(file_path, "rb") as f:
                await update.message.reply_document(document=InputFile(f))

    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء التحميل: {e}")
    finally:
        # تنظيف الملف المؤقت إن وجد
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

# -------------------------
# تشغيل البوت
# -------------------------
async def on_startup(app):
    print("✅ البوت اشتغل وينتظر الرسائل...")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # أوامر عامة
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))  # لفتح لوحة الأدمن يدويًا

    # أزرار لوحة الأدمن
    app.add_handler(CallbackQueryHandler(on_admin_button))

    # استقبال كل الرسائل النصية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.create_task(on_startup(app))
    app.run_polling()

if __name__ == "__main__":
    main()