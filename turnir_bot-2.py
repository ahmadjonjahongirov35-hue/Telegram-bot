import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import psycopg2
from psycopg2.extras import RealDictCursor

# ===================== SOZLAMALAR =====================
# Bu qiymatlar endi kod ichida emas, Railway "Variables" bo'limidan olinadi.
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
DATABASE_URL = os.environ["DATABASE_URL"]
KANAL_ID = os.environ.get("KANAL_ID", "")  # Masalan: "@kanalingiz" (ixtiyoriy)
# ======================================================

logging.basicConfig(level=logging.INFO)

ISM, YOSH, TELEFON = range(3)


def db():
    return psycopg2.connect(DATABASE_URL)


def db_init():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ishtirokchilar (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE,
            username TEXT,
            ism TEXT,
            yosh INTEGER,
            telefon TEXT,
            bal INTEGER DEFAULT 0,
            qatnashgan INTEGER DEFAULT 0,
            vaqt TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS turnirlar (
            id SERIAL PRIMARY KEY,
            nomi TEXT,
            tavsif TEXT,
            sana TEXT,
            faol BOOLEAN DEFAULT TRUE,
            vaqt TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def db_royxatdan_otish(user_id, username, ism, yosh, telefon):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ishtirokchilar (user_id, username, ism, yosh, telefon)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET ism=%s, yosh=%s, telefon=%s
    """, (user_id, username, ism, yosh, telefon, ism, yosh, telefon))
    conn.commit()
    cur.close()
    conn.close()


def db_ishtirokchi(user_id):
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM ishtirokchilar WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def db_reyting():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM ishtirokchilar ORDER BY bal DESC LIMIT 20")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def db_hammasi():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM ishtirokchilar ORDER BY bal DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def db_bal_qosh(user_id, bal):
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE ishtirokchilar SET bal=bal+%s WHERE user_id=%s", (bal, user_id))
    conn.commit()
    cur.close()
    conn.close()


def db_bal_ozgartir(user_id, bal):
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE ishtirokchilar SET bal=%s WHERE user_id=%s", (bal, user_id))
    conn.commit()
    cur.close()
    conn.close()


def db_turnir_qosh(nomi, tavsif, sana):
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO turnirlar (nomi, tavsif, sana) VALUES (%s, %s, %s)", (nomi, tavsif, sana))
    conn.commit()
    cur.close()
    conn.close()


def db_turnirlar():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM turnirlar WHERE faol=TRUE ORDER BY vaqt DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def db_stat():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ishtirokchilar")
    jami = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ishtirokchilar WHERE DATE(vaqt)=CURRENT_DATE")
    bugun = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jami, bugun


def asosiy_menyu():
    keyboard = [
        [KeyboardButton("📝 Ro'yxatdan o'tish")],
        [KeyboardButton("🏆 Reyting"), KeyboardButton("👤 Mening balim")],
        [KeyboardButton("📅 Turnirlar")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def admin_menyu():
    keyboard = [
        [KeyboardButton("👥 Ishtirokchilar"), KeyboardButton("📊 Statistika")],
        [KeyboardButton("⭐ Bal qo'shish"), KeyboardButton("✏️ Bal o'zgartirish")],
        [KeyboardButton("📢 Turnir e'lon qilish"), KeyboardButton("📋 Reyting")],
        [KeyboardButton("📝 Ro'yxatdan o'tish"), KeyboardButton("👤 Mening balim")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    menyu = admin_menyu() if user_id == ADMIN_ID else asosiy_menyu()
    await update.message.reply_text(
        "Assalomu alaykum! Botimizga xush kelibsiz! 🎉\n\n"
        "Bu bot turnirlarimizga ro'yxatdan o'tish va natijalarni kuzatish uchun.",
        reply_markup=menyu
    )


async def royxatdan_otish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Ro'yxatdan o'tish\n\nIsmingizni kiriting (Ism Familiya):")
    return ISM


async def ism_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ism"] = update.message.text
    await update.message.reply_text("Yoshingizni kiriting (masalan: 18):")
    return YOSH


async def yosh_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        yosh = int(update.message.text)
        if yosh < 5 or yosh > 100:
            await update.message.reply_text("❌ Yoshni to'g'ri kiriting (5-100):")
            return YOSH
        context.user_data["yosh"] = yosh
        keyboard = [
            [KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton("⏭ O'tkazib yuborish")]
        ]
        await update.message.reply_text(
            "Telefon raqamingiz (ixtiyoriy):",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return TELEFON
    except:
        await update.message.reply_text("❌ Faqat son kiriting:")
        return YOSH


async def telefon_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        telefon = update.message.contact.phone_number
    elif update.message.text == "⏭ O'tkazib yuborish":
        telefon = "-"
    else:
        telefon = update.message.text

    user = update.effective_user
    ism = context.user_data["ism"]
    yosh = context.user_data["yosh"]
    db_royxatdan_otish(user.id, user.username or "-", ism, yosh, telefon)

    menyu = admin_menyu() if user.id == ADMIN_ID else asosiy_menyu()
    await update.message.reply_text(
        f"✅ Ro'yxatdan o'tdingiz!\n\n"
        f"👤 Ism: {ism}\n🎂 Yosh: {yosh}\n📱 Telefon: {telefon}\n⭐ Bal: 0",
        reply_markup=menyu
    )
    return ConversationHandler.END


async def mening_balim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ishtirokchi = db_ishtirokchi(update.effective_user.id)
    if not ishtirokchi:
        await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz!\n\n📝 Ro'yxatdan o'tish tugmasini bosing.")
        return
    reyting = db_reyting()
    orni = next((i+1 for i, r in enumerate(reyting) if r["user_id"] == update.effective_user.id), "-")
    await update.message.reply_text(
        f"👤 *{ishtirokchi['ism']}*\n\n"
        f"🎂 Yosh: {ishtirokchi['yosh']}\n"
        f"⭐ Bal: *{ishtirokchi['bal']}*\n"
        f"🏆 O'rin: *{orni}*",
        parse_mode="Markdown"
    )


async def reyting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db_reyting()
    if not rows:
        await update.message.reply_text("Hozircha ishtirokchilar yo'q.")
        return
    medallar = ["🥇", "🥈", "🥉"]
    matn = "🏆 *Reyting Jadvali:*\n\n"
    for i, r in enumerate(rows):
        medal = medallar[i] if i < 3 else f"{i+1}."
        matn += f"{medal} {r['ism']} — *{r['bal']}* bal\n"
    await update.message.reply_text(matn, parse_mode="Markdown")


async def turnirlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db_turnirlar()
    if not rows:
        await update.message.reply_text("📅 Hozircha turnirlar yo'q.")
        return
    matn = "📅 *Faol Turnirlar:*\n\n"
    for t in rows:
        matn += f"🏆 *{t['nomi']}*\n📝 {t['tavsif']}\n📆 {t['sana']}\n\n"
    await update.message.reply_text(matn, parse_mode="Markdown")


async def admin_ishtirokchilar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    rows = db_hammasi()
    if not rows:
        await update.message.reply_text("Ishtirokchilar yo'q.")
        return
    matn = f"👥 *Ishtirokchilar ({len(rows)} ta):*\n\n"
    for i, r in enumerate(rows[:30], 1):
        matn += f"{i}. {r['ism']} ({r['yosh']} yosh) — {r['bal']} bal | ID: `{r['user_id']}`\n"
    await update.message.reply_text(matn, parse_mode="Markdown")


async def admin_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    jami, bugun = db_stat()
    await update.message.reply_text(
        f"📊 *Statistika:*\n\n👥 Jami: *{jami}*\n📅 Bugun: *{bugun}*",
        parse_mode="Markdown"
    )


async def bal_qosh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        bal = int(context.args[1])
        db_bal_qosh(user_id, bal)
        ishtirokchi = db_ishtirokchi(user_id)
        await update.message.reply_text(f"✅ {ishtirokchi['ism']} ga {bal} bal qo'shildi!\nJami: {ishtirokchi['bal']}")
        try:
            await context.bot.send_message(user_id, f"🎉 Sizga {bal} bal qo'shildi!\n⭐ Jami balingiz: {ishtirokchi['bal']}")
        except:
            pass
    except:
        await update.message.reply_text("❌ Format: /bal_qosh USER_ID BAL")


async def bal_ozgartir_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        bal = int(context.args[1])
        db_bal_ozgartir(user_id, bal)
        ishtirokchi = db_ishtirokchi(user_id)
        await update.message.reply_text(f"✅ {ishtirokchi['ism']} bali {bal} ga o'zgartirildi!")
    except:
        await update.message.reply_text("❌ Format: /bal_ozgartir USER_ID BAL")


async def turnir_qosh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        matn = " ".join(context.args)
        qismlar = matn.split("|")
        nomi = qismlar[0].strip()
        tavsif = qismlar[1].strip()
        sana = qismlar[2].strip()
        db_turnir_qosh(nomi, tavsif, sana)
        await update.message.reply_text(f"✅ Turnir qo'shildi: *{nomi}*", parse_mode="Markdown")
        if KANAL_ID:
            try:
                await context.bot.send_message(
                    KANAL_ID,
                    f"🏆 *Yangi Turnir!*\n\n📌 {nomi}\n📝 {tavsif}\n📆 {sana}",
                    parse_mode="Markdown"
                )
            except:
                pass
    except:
        await update.message.reply_text("❌ Format: /turnir_qosh NOMI | TAVSIF | SANA")


async def xabar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    user_id = update.effective_user.id
    if matn in ["🏆 Reyting", "📋 Reyting"]:
        await reyting(update, context)
    elif matn == "👤 Mening balim":
        await mening_balim(update, context)
    elif matn == "📅 Turnirlar":
        await turnirlar(update, context)
    elif matn == "👥 Ishtirokchilar" and user_id == ADMIN_ID:
        await admin_ishtirokchilar(update, context)
    elif matn == "📊 Statistika" and user_id == ADMIN_ID:
        await admin_stat(update, context)
    elif matn == "⭐ Bal qo'shish" and user_id == ADMIN_ID:
        await update.message.reply_text("Format: /bal_qosh USER_ID BAL\n\nMasalan: /bal_qosh 123456789 10")
    elif matn == "✏️ Bal o'zgartirish" and user_id == ADMIN_ID:
        await update.message.reply_text("Format: /bal_ozgartir USER_ID BAL")
    elif matn == "📢 Turnir e'lon qilish" and user_id == ADMIN_ID:
        await update.message.reply_text("Format: /turnir_qosh NOMI | TAVSIF | SANA")


def main():
    db_init()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Ro'yxatdan o'tish$"), royxatdan_otish)],
        states={
            ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ism_olish)],
            YOSH: [MessageHandler(filters.TEXT & ~filters.COMMAND, yosh_olish)],
            TELEFON: [
                MessageHandler(filters.CONTACT, telefon_olish),
                MessageHandler(filters.TEXT & ~filters.COMMAND, telefon_olish)
            ],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bal_qosh", bal_qosh_cmd))
    app.add_handler(CommandHandler("bal_ozgartir", bal_ozgartir_cmd))
    app.add_handler(CommandHandler("turnir_qosh", turnir_qosh_cmd))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, xabar_handler))
    print("✅ Turnir boti ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
