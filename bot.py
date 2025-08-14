import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

# بياناتك
TOKEN = "8024366013:AAFBEV341PKd2cYgQ7jexoF6n37gq2Lx7fY"
ADMIN_IDS = [7473286060, 5497769888]  # أكثر من آدمن
CHANNELS_FILE = "channels.txt"
USERS_FILE = "users.txt"

# تحميل القنوات من ملف أو إنشاء ملف جديد
if not os.path.exists(CHANNELS_FILE):
    with open(CHANNELS_FILE, "w") as f:
        f.write("Syria_7X\n")  # قناة افتراضية
with open(CHANNELS_FILE, "r") as f:
    CHANNELS = [line.strip() for line in f if line.strip()]

# حفظ القنوات في الملف
def save_channels():
    with open(CHANNELS_FILE, "w") as f:
        for ch in CHANNELS:
            f.write(ch + "\n")

# دالة التحقق من الاشتراك
async def check_subscription(user_id, context):
    not_subscribed = []
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(f"@{channel}", user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    return not_subscribed

# حفظ المستخدمين
def save_user(user_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            pass
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(str(user_id) + "\n")

# تحميل الفيديو
def download_video(url):
    ydl_opts = {
        'outtmpl': 'video.%(ext)s',
        'format': 'best',
        'noplaylist': True,
        'quiet': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    not_subscribed = await check_subscription(update.effective_user.id, context)
    if not_subscribed:
        channels_list = "\n".join([f"@{ch}" for ch in not_subscribed])
        await update.message.reply_text(f"🚫 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n{channels_list}")
        return
    await update.message.reply_text("✅ أهلاً بك! أرسل أي رابط لتحميله 📥")

# استقبال الروابط
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    not_subscribed = await check_subscription(update.effective_user.id, context)
    if not_subscribed:
        channels_list = "\n".join([f"@{ch}" for ch in not_subscribed])
        await update.message.reply_text(f"🚫 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n{channels_list}")
        return
    url = update.message.text.strip()
    await update.message.reply_text("⏳ جاري التحميل...")
    try:
        file_path = download_video(url)
        await update.message.reply_video(video=open(file_path, "rb"))
        os.remove(file_path)
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ: {e}")

# أوامر الأدمن
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("❌ استخدم: /addchannel اسم_القناة")
        return
    channel = context.args[0].replace("@", "")
    if channel not in CHANNELS:
        CHANNELS.append(channel)
        save_channels()
        await update.message.reply_text(f"✅ تمت إضافة القناة: @{channel}")
    else:
        await update.message.reply_text("⚠️ القناة موجودة بالفعل.")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("❌ استخدم: /removechannel اسم_القناة")
        return
    channel = context.args[0].replace("@", "")
    if channel in CHANNELS:
        CHANNELS.remove(channel)
        save_channels()
        await update.message.reply_text(f"✅ تمت إزالة القناة: @{channel}")
    else:
        await update.message.reply_text("⚠️ القناة غير موجودة.")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if CHANNELS:
        await update.message.reply_text("📢 القنوات الحالية:\n" + "\n".join([f"@{ch}" for ch in CHANNELS]))
    else:
        await update.message.reply_text("❌ لا توجد قنوات.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = f.read().splitlines()
        await update.message.reply_text(f"👥 عدد المستخدمين: {len(users)}")
    else:
        await update.message.reply_text("👥 عدد المستخدمين: 0")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # أوامر عامة
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    # أوامر الأدمن
    app.add_handler(CommandHandler("addchannel", add_channel))
    app.add_handler(CommandHandler("removechannel", remove_channel))
    app.add_handler(CommandHandler("listchannels", list_channels))
    app.add_handler(CommandHandler("stats", stats))

    app.run_polling()