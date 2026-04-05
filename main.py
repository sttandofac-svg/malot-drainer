from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

app = FastAPI(title="Mass Sender")

client = None
chats = []                    # список чатов
broadcast_task = None         # задача рассылки
is_broadcasting = False

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mass Sender</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: #1f1f1f; padding: 30px; border-radius: 12px; }
        input, textarea, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: none; }
        input, textarea { background: #333; color: white; }
        button { background: #0066ff; color: white; font-weight: bold; cursor: pointer; }
        button:hover { background: #0055dd; }
        .stop-btn { background: #cc0000 !important; }
        .section { margin: 25px 0; padding: 20px; background: #2a2a2a; border-radius: 10px; }
        .success { color: #00ff88; }
        .error { color: #ff6666; }
        .status { font-size: 18px; font-weight: bold; margin: 15px 0; }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Mass Sender — Бесконечная рассылка</h1>

    <!-- Авторизация -->
    <div class="section">
        <h2>1. Авторизация аккаунта</h2>
        <input type="text" id="phone" placeholder="+79161234567">
        <button onclick="sendPhone()">Отправить номер</button>

        <div id="codeBlock" style="display:none; margin-top:15px;">
            <input type="text" id="code" placeholder="Код из SMS">
            <input type="password" id="password" placeholder="Пароль 2FA (если есть)">
            <button onclick="sendCode()">Отправить код + пароль</button>
        </div>
    </div>

    <!-- Рассылка -->
    <div class="section">
        <h2>2. Бесконечная рассылка</h2>
        
        <h3>Каналы/чаты (до 10)</h3>
        <input type="text" id="newChat" placeholder="@username или -1001234567890">
        <button onclick="addChat()">+ Добавить чат</button>
        <div id="chatList" style="margin:15px 0; min-height:80px; background:#222; padding:10px; border-radius:8px;"></div>

        <h3>Текст сообщения</h3>
        <textarea id="text" rows="5" placeholder="Текст, который будет отправляться бесконечно..."></textarea>

        <h3>Фото (опционально — прямая ссылка)</h3>
        <input type="text" id="photo" placeholder="https://example.com/photo.jpg (или оставь пустым)">

        <button onclick="startBroadcast()" style="background:#00cc00; padding:16px; font-size:18px;">▶ Запустить БЕСКОНЕЧНУЮ рассылку</button>
        <button onclick="stopBroadcast()" class="stop-btn" style="margin-top:10px;">⛔ Остановить рассылку</button>

        <div id="status" class="status"></div>
        <div id="result"></div>
    </div>
</div>

<script>
let chats = [];
let isRunning = false;

function updateChatList() {
    let html = chats.map((c,i) => `<div>${i+1}. ${c}</div>`).join('');
    document.getElementById('chatList').innerHTML = html || 'Добавьте чаты для рассылки';
}

async function sendPhone() {
    const phone = document.getElementById('phone').value.trim();
    const res = await fetch('/auth', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:`phone=${encodeURIComponent(phone)}`});
    const data = await res.json();
    document.getElementById('result').innerHTML = `<p>${data.message}</p>`;
    if (data.status === "need_code") document.getElementById('codeBlock').style.display = 'block';
}

async function sendCode() {
    const phone = document.getElementById('phone').value.trim();
    const code = document.getElementById('code').value.trim();
    const password = document.getElementById('password').value.trim();
    const res = await fetch('/auth', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:`phone=${encodeURIComponent(phone)}&code=${encodeURIComponent(code)}&password=${encodeURIComponent(password)}`});
    const data = await res.json();
    document.getElementById('result').innerHTML = `<p class="${data.status==='success'?'success':'error'}">${data.message}</p>`;
}

async function addChat() {
    let chat = document.getElementById('newChat').value.trim();
    if (chat && chats.length < 10) {
        chats.push(chat);
        updateChatList();
        document.getElementById('newChat').value = '';
    }
}

async function startBroadcast() {
    const text = document.getElementById('text').value.trim();
    const photo = document.getElementById('photo').value.trim();

    if (chats.length === 0) {
        document.getElementById('result').innerHTML = '<p class="error">Добавьте хотя бы один чат!</p>';
        return;
    }
    if (!text) {
        document.getElementById('result').innerHTML = '<p class="error">Введите текст сообщения!</p>';
        return;
    }

    isRunning = true;
    document.getElementById('status').innerHTML = '🔄 Рассылка запущена (работает бесконечно с задержкой 60 сек)';
    document.getElementById('result').innerHTML = '';

    const res = await fetch('/start_broadcast', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({chats: chats, text: text, photo: photo})
    });
}

async function stopBroadcast() {
    const res = await fetch('/stop_broadcast', {method: 'POST'});
    const data = await res.json();
    isRunning = false;
    document.getElementById('status').innerHTML = '⛔ Рассылка остановлена';
    document.getElementById('result').innerHTML = `<p>${data.message}</p>`;
}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.post("/auth")
async def auth(phone: str = Form(...), code: str = Form(None), password: str = Form(None)):
    global client
    try:
        if not client:
            client = TelegramClient(StringSession(""), API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            if code is None:
                await client.send_code_request(phone)
                return {"status": "need_code", "message": "Код отправлен в SMS. Введите ниже."}
            await client.sign_in(phone=phone, code=code, password=password or None)

        return {"status": "success", "message": "✅ Аккаунт успешно авторизован!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/start_broadcast")
async def start_broadcast(data: dict):
    global broadcast_task, is_broadcasting
    if not client:
        return {"status": "error", "message": "Аккаунт не авторизован"}

    chats = data.get("chats", [])
    text = data.get("text", "")
    photo = data.get("photo", "")

    is_broadcasting = True

    async def infinite_broadcast():
        count = 0
        while is_broadcasting:
            for chat in chats:
                if not is_broadcasting:
                    break
                try:
                    if photo:
                        await client.send_file(chat, photo, caption=text)
                    else:
                        await client.send_message(chat, text)
                    count += 1
                    print(f"Отправлено в {chat} | Всего: {count}")
                except Exception as e:
                    print(f"Ошибка в {chat}: {e}")
                await asyncio.sleep(60)   # задержка 60 секунд

    broadcast_task = asyncio.create_task(infinite_broadcast())
    return {"status": "success", "message": "Бесконечная рассылка запущена"}

@app.post("/stop_broadcast")
async def stop_broadcast():
    global is_broadcasting, broadcast_task
    is_broadcasting = False
    if broadcast_task:
        broadcast_task.cancel()
    return {"status": "success", "message": "Рассылка остановлена пользователем"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
