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