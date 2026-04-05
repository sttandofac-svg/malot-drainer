from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import asyncio
import aiosqlite
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SITE_PASSWORD = os.getenv("SITE_PASSWORD", "admin123")  # пароль для входа на сайт

app = FastAPI(title="Mass Sender Pro")

client = None
chats = []
broadcast_task = None
is_broadcasting = False
current_session = None

# Инициализация базы
async def init_db():
    async with aiosqlite.connect("sender.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tg_accounts (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                string_session TEXT,
                phone TEXT
            )
        """)
        await db.commit()

@app.on_event("startup")
async def startup():
    await init_db()

# ==================== HTML ====================
HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mass Sender Pro</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a0a; color: #eee; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; background: #1a1a1a; padding: 30px; border-radius: 16px; box-shadow: 0 0 20px rgba(0,0,0,0.5); }
        h1 { text-align: center; color: #00ffaa; }
        input, textarea, select, button { width: 100%; padding: 14px; margin: 10px 0; border-radius: 10px; border: none; font-size: 16px; }
        input, textarea, select { background: #333; color: white; }
        button { background: #0066ff; color: white; font-weight: bold; cursor: pointer; }
        button:hover { background: #0055cc; }
        .red { background: #cc0000 !important; }
        .section { background: #252525; padding: 20px; border-radius: 12px; margin: 25px 0; }
        .status { font-size: 18px; padding: 15px; border-radius: 10px; margin: 15px 0; }
        .success { background: #004d00; }
        .error { background: #4d0000; }
        .chat-item { background: #333; padding: 10px; margin: 5px 0; border-radius: 8px; }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Mass Sender Pro</h1>

    <!-- Авторизация сайта -->
    <div class="section">
        <h2>Вход в панель</h2>
        <input type="password" id="sitePass" placeholder="Пароль сайта" value="admin123">
        <button onclick="login()">Войти в панель</button>
    </div>

    <div id="mainPanel" style="display:none;">

        <!-- Добавление TG аккаунта -->
        <div class="section">
            <h2>Добавить Telegram аккаунт</h2>
            <input type="text" id="tgPhone" placeholder="+79xxxxxxxxx">
            <button onclick="addTGAccount()">Добавить TG аккаунт</button>
            <div id="tgResult"></div>
        </div>

        <!-- Рассылка -->
        <div class="section">
            <h2>Бесконечная рассылка</h2>
            
            <h3>Список чатов (до 10)</h3>
            <input type="text" id="newChat" placeholder="@username или -100xxxxxxxxxx">
            <button onclick="addChat()">+ Добавить чат</button>
            <div id="chatList" style="margin:15px 0;"></div>

            <h3>Текст сообщения</h3>
            <textarea id="text" rows="6" placeholder="Текст для рассылки..."></textarea>

            <h3>Фото (можно загрузить файл)</h3>
            <input type="file" id="photoFile" accept="image/*">

            <button onclick="startBroadcast()" style="background:#00cc00; padding:18px; font-size:20px;">▶ Запустить БЕСКОНЕЧНУЮ рассылку</button>
            <button onclick="stopBroadcast()" class="red" style="padding:18px; font-size:20px;">⛔ Остановить рассылку</button>

            <div id="status" class="status"></div>
            <div id="result"></div>
        </div>
    </div>
</div>

<script>
let chats = [];

function login() {
    const pass = document.getElementById('sitePass').value;
    if (pass === "admin123") {
        document.getElementById('mainPanel').style.display = 'block';
    } else {
        alert("Неверный пароль сайта");
    }
}

function addChat() {
    let chat = document.getElementById('newChat').value.trim();
    if (chat && chats.length < 10) {
        chats.push(chat);
        let html = chats.map((c,i) => `<div class="chat-item">${i+1}. ${c}</div>`).join('');
        document.getElementById('chatList').innerHTML = html;
        document.getElementById('newChat').value = '';
    }
}

async function addTGAccount() {
    const phone = document.getElementById('tgPhone').value.trim();
    const res = await fetch('/add_tg', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:`phone=${encodeURIComponent(phone)}`});
    const data = await res.json();
    document.getElementById('tgResult').innerHTML = `<p class="${data.status==='success'?'success':'error'}">${data.message}</p>`;
}

async function startBroadcast() {
    const text = document.getElementById('text').value.trim();
    const file = document.getElementById('photoFile').files[0];

    const formData = new FormData();
    formData.append('text', text);
    chats.forEach(c => formData.append('chats', c));
    if (file) formData.append('photo', file);

    document.getElementById('status').innerHTML = '🔄 Рассылка запущена (работает бесконечно, задержка 60 сек)';
    const res = await fetch('/start_broadcast', {method: 'POST', body: formData});
}

async function stopBroadcast() {
    await fetch('/stop_broadcast', {method: 'POST'});
    document.getElementById('status').innerHTML = '⛔ Рассылка остановлена';
}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.post("/add_tg")
async def add_tg(phone: str = Form(...)):
    global client
    try:
        if not client:
            client = TelegramClient(StringSession(""), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            return {"status": "need_code", "message": "Код отправлен. Введите его в следующей версии (пока упрощённо)."}
        return {"status": "success", "message": "Аккаунт добавлен!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/start_broadcast")
async def start_broadcast(text: str = Form(...), chats: list = Form(...), photo: UploadFile = File(None)):
    global is_broadcasting, broadcast_task, client
    if not client:
        return {"status": "error", "message": "Сначала авторизуйте аккаунт"}

    is_broadcasting = True

    async def loop():
        while is_broadcasting:
            for chat in chats:
                if not is_broadcasting: break
                try:
                    if photo:
                        file_bytes = await photo.read()
                        await client.send_file(chat, file_bytes, caption=text)
                    else:
                        await client.send_message(chat, text)
                except:
                    pass
                await asyncio.sleep(60)
    broadcast_task = asyncio.create_task(loop())
    return {"status": "success"}

@app.post("/stop_broadcast")
async def stop_broadcast():
    global is_broadcasting
    is_broadcasting = False
    return {"status": "success", "message": "Рассылка остановлена"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
