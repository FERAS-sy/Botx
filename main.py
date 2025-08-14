import os
import json
from typing import Dict, Any, List

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from yt_dlp import YoutubeDL

# ======================
# الإعدادات والبيانات
# ======================

DATA_FILE = "data.json"

# حمّل/أنشئ ملف البيانات
def load_data() -> Dict[str, Any]:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "token": os.getenv("8024366013:AAFBEV341PKd2cYgQ7jexoF6n37gq2Lx7fY", ""),         # يمكنك وضع التوكن هنا أو كمتغير بيئة
            "admins": [7473286060, 5497769888],          # IDs الأدمن الافتراضيين
            "channels": ["Syria_7X"],                    # قنوات الاشتراك بدون @
            "users": {}                                  # {user_id: {"username": "...", "first_name": "..."}}
        }
        save_data(data)
    # لو فيه توكن من البيئة يغلّب
    env_token = os.getenv("BOT_TOKEN")
    if env_token:
        data["token"] = env_token
    return data

def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# تحقّق من وجود التوكن
TOKEN = data.get("token", "").strip()
if not TOKEN:
    raise RuntimeError("يرجى ضبط توكن البوت إما داخل data.json في المفتاح 'token' أو كمتغير بيئة BOT_TOKEN.")

WELCOME_TEXT = (
    "مِࢪحِبَاެ عَࢪ࣪يَࢪ࣪يَ👋.\n"
    "اެنِتَ اެݪاެنِ فَيَ اެسِࢪعَ بَۅٛتَ ݪݪتَحِمِيَݪ مِنِ جَمِيَعَ اެݪمِۅٛاقِعَ .\n\n"
    "- لتحميل من تيك توك فقط ارسل رابط المنشور .👁‍🗨\n\n"
    "- لتحميل فديو وصور من انستا فقط ارسل رابط المنشور او يوزر الحساب .📲\n\n"
    "- لتحميل من يوتيوب ارسل اسم الاغنيه او رابط 🎙 .\n\n"
    "- للتحميل من اي برنامج فقط ارسل الرابط وتدلل🗿.\n\n"
    "بوتنا بدون حقوق ^← @MOKAF700 »»» @XS5_S"
)

# ======================
# أدوات مساعدة
# ======================

def is_admin(user_id: int) -> bool:
    return int(user_id) in data["admins"]

def add_user(update: Update) -> None:
    u = update.effective_user
    if u:
        uid = str(u.id)
        if uid not in data["users"]:
            data["users"][uid] = {
                "username": (u.username or ""),
                "first_name": (u.first_name or "")
            }
            save_data(data)

async def check_subscription_all(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> List[str]:
    """
    يرجع قائمة القنوات التي لم يشترك فيها المستخدم.
    لو حدث خطأ (مثلاً البوت ليس مشرفاً في قناة)، نعتبر المستخدم غير مشترك فيها.
    """
    not_subscribed = []
    for ch in data["channels"]:
        try:
            member = await context.bot.get_chat_member(f"@{ch}", user_id)
            if member.status not in ("member", "administrator", "creator"):
                not_subscribed.append(ch)
        except Exception:
            # إذا القناة خاصة أو البوت ليس مشرفًا، سنعدّها غير مشترك
            not_subscribed.append(ch)
    return not_subscribed

def download_video_any(url: str) -> str:
    """
    تنزيل من أي منصة يدعمها yt_dlp.
    يرجّع المسار النهائي للملف الذي تم تنزيله.
    """
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "format": "best",
        "noplaylist": True,
        "quiet": True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# ======================
# الأوامر العامة
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update)
    user_id = update.effective_user.id

    # تحقّق الاشتراك لغير الأدمن
    if not is_admin(user_id):
        missing = await check_subscription_all(user_id, context)
        if missing:
            chs = "\n".join([f"@{c}" for c in missing])
            await update.message.reply_text(f"🚫 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n{chs}")
            return

    await update.message.reply_text(WELCOME_TEXT)

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update)
    user_id = update.effective_user.id

    if not is_admin(user_id):
        missing = await check_subscription_all(user_id, context)
        if missing:
            chs = "\n".join([f"@{c}" for c in missing])
            await update.message.reply_text(f"🚫 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n{chs}")
            return

    url = (update.message.text or "").strip()
    if not url:
        return

    await update.message.reply_text("⏳ جاري التحميل...")
    try:
        file_path = download_video_any(url)

        # محاولة إرسال كـ فيديو؛ إن فشل (كبير/نوع غير مدعوم) نرسله كـ ملف
        try:
            await update.message.reply_video(video=open(file_path, "rb"))
        except Exception:
            await update.message.reply_document(document=open(file_path, "rb"))

        # تنظيف الملف
        try:
            os.remove(file_path)
        except Exception:
            pass

    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء التحميل: {e}")

# ======================
# أوامر الإدارة (Admins)
# ======================

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("❗ استخدم:\n/addadmin ID")
        return
    try:
        new_id = int(context.args[0])
        if new_id not in data["admins"]:
            data["admins"].append(new_id)
            save_data(data)
            await update.message.reply_text(f"✅ تم إضافة الأدمن: {new_id}")
        else:
            await update.message.reply_text("⚠️ هذا الأدمن موجود بالفعل.")
    except ValueError:
        await update.message.reply_text("❗ ID غير صالح.")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("❗ استخدم:\n/removeadmin ID")
        return
    try:
        rm_id = int(context.args[0])
        if rm_id in data["admins"]:
            data["admins"].remove(rm_id)
            save_data(data)
            await update.message.reply_text(f"🗑️ تم حذف الأدمن: {rm_id}")
        else:
            await update.message.reply_text("⚠️ هذا الـ ID ليس أدمن.")
    except ValueError:
        await update.message.reply_text("❗ ID غير صالح.")

async def listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if data["admins"]:
        listing = "\n".join([str(a) for a in data["admins"]])
        await update.message.reply_text