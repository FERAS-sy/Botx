import os
import sqlite3
from datetime import datetime
from typing import List, Tuple

from yt_dlp import YoutubeDL
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# =========================
# إعدادات أساسية
# =========================
BOT_TOKEN = "8024366013:AAFBEV341PKd2cYgQ7jexoF6n37gq2Lx7fY"
DEFAULT_ADMINS = [7473286060, 5497769888]
DEFAULT_CHANNELS = ["Syria_7X"]  # بدون @

DB_PATH = "bot.db"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

WELCOME = (
    "مِࢪحِبَاެ عَࢪ࣪يَࢪ࣪يَ👋.\n"
    "اެنِتَ اެݪاެنِ فَيَ اެسِࢪعَ بَۅٛتَ ݪݪتَحِمِيَݪ مِنِ جَمِيَعَ اެݪمِۅٛاقِعَ .\n\n"
    "- لتحميل من تيك توك فقط ارسل رابط المنشور .👁‍🗨\n"
    "- لتحميل فديو وصور من انستا فقط ارسل رابط المنشور او يوزر الحساب .📲\n"
    "- لتحميل من يوتيوب ارسل اسم الاغنيه او رابط 🎙 .\n"
    "- للتحميل من اي برنامج فقط ارسل الرابط وتدلل🗿.\n\n"
    "بوتنا بدون حقوق ^← @MOKAF700 »»» @XS5_S"
)

# =========================
# قاعدة البيانات
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # جداول
    c.execute("""CREATE TABLE IF NOT EXISTS admins(
                    user_id INTEGER PRIMARY KEY
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS channels(
                    username TEXT PRIMARY KEY
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS users(
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    joined_at TEXT
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS downloads(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT,
                    created_at TEXT
                )""")
    conn.commit()
    # بذور أولية
    for a in DEFAULT_ADMINS:
        c.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (a,))
    for ch in DEFAULT_CHANNELS:
        c.execute("INSERT OR IGNORE INTO channels(username) VALUES(?)", (ch.replace("@", ""),))
    conn.commit()
    conn.close()

def db_conn():
    return sqlite3.connect(DB_PATH)

def get_admins() -> List[int]:
    with db_conn() as conn:
        rows = conn.execute("SELECT user_id FROM admins").fetchall()
    return [r[0] for r in rows]

def add_admin(uid: int) -> bool:
    with db_conn() as conn:
        try:
            conn.execute("INSERT INTO admins(user_id) VALUES(?)", (uid,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def remove_admin(uid: int) -> bool:
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM admins WHERE user_id=?", (uid,))
        conn.commit()
        return cur.rowcount > 0

def get_channels() -> List[str]:
    with db_conn() as conn:
        rows = conn.execute("SELECT username FROM channels").fetchall()
    return [r[0] for r in rows]

def add_channel(username: str) -> bool:
    u = username.replace("@", "")
    if not u:
        return False
    with db_conn() as conn:
        try:
            conn.execute("INSERT INTO channels(username) VALUES(?)", (u,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def remove_channel(username: str) -> bool:
    u = username.replace("@", "")
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM channels WHERE username=?", (u,))
        conn.commit()
        return cur.rowcount > 0

def add_user_if_new(update: Update):
    u = update.effective_user
    if not u:
        return
    with db_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO users(user_id, username, first_name, joined_at)
               VALUES(?, ?, ?, ?)""",
            (u.id, u.username or "", u.first_name or "", datetime.utcnow().isoformat())
        )
        conn.commit()

def insert_download(user_id: int, url: str):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO downloads(user_id, url, created_at) VALUES(?, ?, ?)",
            (user_id, url, datetime.utcnow().isoformat())
        )
        conn.commit()

# =========================
# أدوات مساعدة
# =========================
def is_admin(user_id: int) -> bool:
    return user_id in get_admins()

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
            InlineKeyboardButton("👥 المستخدمون", callback_data="adm_list_users"),
        ],
    ]
    return InlineKeyboardMarkup(kb)

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_back")]])

def channels_human_list(chs: List[str]) -> str:
    return "\n".join(f"@{c}" for c in chs) if chs else "لا توجد قنوات"

async def check_subscription_all(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, List[str]]:
    chs = get_channels()
    if not chs:
        return True, []
    missing = []
    for ch in chs:
        try:
            member = await context.bot.get_chat_member(f"@{ch}", user_id)
            if member.status not in ("member", "administrator", "creator"):
                missing.append(ch)
        except Exception:
            # قناة خاصة/اسم خطأ/البوت مو أدمن -> نعتبرها غير متحقق
            missing.append(ch)
    return (len(missing) == 0), missing

def ytdlp_download_to_dir(url_or_query: str) -> str:
    """
    تنزيل إلى مجلد downloads داخل المشروع (بدل /tmp).
    يرجع المسار النهائي للملف.
    """
    outtmpl = os.path.join(DOWNLOAD_DIR, "file-%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "auto",
        "retries": 3,
        "socket_timeout": 30,
        "merge_output_format": "mp4",
        # لا تستخدم /tmp أبداً:
        "paths": {"home": DOWNLOAD_DIR, "temp": DOWNLOAD_DIR},
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_or_query, download=True)
        file_path = ydl.prepare_filename(info)
        base, _ = os.path.splitext(file_path)
        mp4_path = base + ".mp4"
        if os.path.exists(mp4_path):
            return mp4_path
        return file_path

# =========================
# Handlers
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user_if_new(update)
    uid = update.effective_user.id

    if not is_admin(uid):
        ok, missing = await check_subscription_all(uid, context)
        if not ok:
            await update.message.reply_text(
                "🚫 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n" + channels_human_list(missing)
            )
            return

    if is_admin(uid):
        await update.message.reply_text(WELCOME, reply_markup=admin_keyboard())
    else:
        await update.message.reply_text(WELCOME)

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ هذا الأمر للأدمن فقط.")
    await update.message.reply_text("📌 لوحة تحكم الأدمن:", reply_markup=admin_keyboard())

async def on_admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return
    q = update.callback_query
    uid = q.from_user.id

    if not is_admin(uid):
        await q.answer("غير مسموح", show_alert=True)
        return
    await q.answer()
    flag = q.data

    if flag == "adm_back":
        context.user_data.pop("awaiting", None)
        await q.edit_message_text("📌 لوحة تحكم الأدمن:", reply_markup=admin_keyboard())
        return

    if flag == "adm_stats":
        with db_conn() as conn:
            users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            dl_count = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        channels_count = len(get_channels())
        admins_count = len(get_admins())
        txt = (
            "📊 الإحصائيات:\n"
            f"- المستخدمون: {users_count}\n"
            f"- التحميلات: {dl_count}\n"
            f"- القنوات: {channels_count}\n"
            f"- الأدمن: {admins_count}"
        )
        await q.edit_message_text(txt, reply_markup=admin_keyboard())
        return

    if flag == "adm_list_channels":
        await q.edit_message_text("📢 القنوات:\n" + channels_human_list(get_channels()), reply_markup=admin_keyboard())
        return

    if flag == "adm_list_admins":
        admins_txt = "\n".join(str(a) for a in get_admins()) or "لا يوجد أدمن."
        await q.edit_message_text("👮‍♂️ قائمة الأدمن:\n" + admins_txt, reply_markup=admin_keyboard())
        return

    if flag == "adm_list_users":
        with db_conn() as conn:
            users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        await q.edit_message_text(f"👥 عدد المستخدمين: {users_count}", reply_markup=admin_keyboard())
        return

    # تدفقات الإدخال
    if flag == "adm_add_channel":
        context.user_data["awaiting"] = ("add_channel",)
        await q.edit_message_text("✏️ أرسل الآن اسم القناة (بدون @):", reply_markup=back_keyboard())
        return

    if flag == "adm_remove_channel":
        context.user_data["awaiting"] = ("remove_channel",)
        await q.edit_message_text("✏️ أرسل الآن اسم القناة (بدون @) لحذفها:", reply_markup=back_keyboard())
        return

    if flag == "adm_add_admin":
        context.user_data["awaiting"] = ("add_admin",)
        await q.edit_message_text("✏️ أرسل الآن ID الأدمن الجديد (رقم):", reply_markup=back_keyboard())
        return

    if flag == "adm_remove_admin":
        context.user_data["awaiting"] = ("remove_admin",)
        await q.edit_message_text("✏️ أرسل الآن ID الأدمن المراد حذفه (رقم):", reply_markup=back_keyboard())
        return

async def admin_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not is_admin(update.effective_user.id):
        return False

    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False

    action = awaiting[0]
    txt = (update.message.text or "").strip()

    if action == "add_channel":
        if add_channel(txt):
            await update.message.reply_text(f"✅ تمت إضافة القناة: @{txt.replace('@','')}")
        else:
            await update.message.reply_text("⚠️ القناة موجودة أو الاسم غير صالح.")
        context.user_data.pop("awaiting", None)
        await panel(update, context)
        return True

    if action == "remove_channel":
        if remove_channel(txt):
            await update.message.reply_text(f"🗑️ تمت إزالة القناة: @{txt.replace('@','')}")
        else:
            await update.message.reply_text("⚠️ القناة غير موجودة بالقائمة.")
        context.user_data.pop("awaiting", None)
        await panel(update, context)
        return True

    if action == "add_admin":
        try:
            new_id = int(txt)
            if add_admin(new_id):
                await update.message.reply_text(f"✅ تمت إضافة الأدمن: {new_id}")
            else:
                await update.message.reply_text("⚠️ هذا المستخدم موجود مسبقًا.")
        except ValueError:
            await update.message.reply_text("❗ ID غير صالح. أرسل رقماً فقط.")
        context.user_data.pop("awaiting", None)
        await panel(update, context)
        return True

    if action == "remove_admin":
        try:
            rm_id = int(txt)
            if remove_admin(rm_id):
                await update.message.reply_text(f"🗑️ تمت إزالة الأدمن: {rm_id}")
            else:
                await update.message.reply_text("⚠️ هذا المستخدم ليس ضمن قائمة الأدمن.")
        except ValueError:
            await update.message.reply_text("❗ ID غير صالح. أرسل رقماً فقط.")
        context.user_data.pop("awaiting", None)
        await panel(update, context)
        return True

    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # رسائل إدارية قيد الإدخال؟
    if await admin_text_flow(update, context):
        return

    add_user_if_new(update)
    uid = update.effective_user.id

    # تحقق اشتراك لغير الأدمن
    if not is_admin(uid):
        ok, missing = await check_subscription_all(uid, context)
        if not ok:
            await update.message.reply_text(
                "🚫 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n" + channels_human_list(missing)
            )
            return

    query = (update.message.text or "").strip()
    if not query:
        return

    loading_msg = await update.message.reply_text("⏳ جاري التحميل...")
    try:
        # سجّل التحميل
        insert_download(uid, query)

        # نزّل
        try:
            file_path = ytdlp_download_to_dir(query)
        except Exception as e:
            msg = str(e)
            if "registered users" in msg or "cookies" in msg:
                raise RuntimeError("هذا المحتوى يتطلب تسجيل دخول/كوكيز (خصوصًا فيسبوك). وفّر cookies لـ yt-dlp.")
            raise

        # أرسل الملف كفيديو أولاً، إن فشل أرسله كوثيقة
        try:
            with open(file_path, "rb") as f:
                await update.message.reply_video(video=InputFile(f))
        except Exception:
            with open(file_path, "rb") as f:
                await update.message.reply_document(document=InputFile(f))

    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء التحميل: {e}")
    finally:
        # احذف رسالة "جاري التحميل"
        try:
            await loading_msg.delete()
        except Exception:
            pass
        # نظّف الملف الذي نزلناه
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

# =========================
# تشغيل البوت
# =========================
async def on_startup(app):
    print("✅ البوت اشتغل وينتظر الرسائل...")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CallbackQueryHandler(on_admin_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()