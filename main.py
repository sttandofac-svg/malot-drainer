from fastapi import FastAPI, Form, UploadFile, File
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

app = FastAPI(title="Mass Sender Pro")

client = None
chats = []
broadcast_task = None
is_broadcasting = False

# ==================== HTML ====================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mass Sender Pro</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0a0a0a; color: #eee; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: #1a1a1a; padding: 30px; border-radius: 16px; }
        h1 { text-align: center; color: #00ffaa; }
        input, textarea, button { width: 100%; padding: 14px; margin: 10px 0; border-radius: 10px; border: none; font-size: 16px; }
        input, textarea { background: #333; color: white; }
        button { background: #0066ff; color: white; font-weight: bold; cursor: pointer; }
        button:hover { background: #0055dd; }
        .red { background: #cc0000 !important; }
        .section { background: #252525; padding: 20px; border-radius: 12px; margin: 25px 0; }
        .status { font-size: 18px; padding: 15px; border-radius: 10px; margin: 15px 0; background: #333; }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Mass Sender Pro</h1>

    <div class="section">
        <h2>Авторизация Telegram аккаунта</h2>
        <input type="text" id="phone" placeholder="+79xxxxxxxxx">
        <button onclick="sendPhone()">1. Отправить номер</button>

        <div id="codeBlock" style="display:none; margin-top:15px;">
            <input type="text" id="code" placeholder="Код из SMS">
            <input type="password" id="password" placeholder="Пароль 2FA (если есть)">
            <button onclick="sendCode()">2. Отправить код и пароль</button>
        </div>
    </div>

    <div class="section">
        <h2>Бесконечная рассылка</h2>
        
        <h3>Каналы / чаты (до 10)</h3>
        <input type="text" id="newChat" placeholder="@username или -1001234567890">
        <button onclick="addChat()">+ Добавить чат</button>
        <div id="chatList" style="margin:15px 0; background:#222; padding:12px; border-radius:8px; min-height:60px;"></div>

        <h3>Текст сообщения</h3>
        <textarea id="text" rows="6" placeholder="Текст, который будет отправляться бесконечно..."></textarea>

        <h3>Фото (загрузить реальный файл)</h3>
        <input type="file" id="photoFile" accept="image/*">

        <button onclick="startBroadcast()" style="background:#00cc00; padding:18px; font-size:20px;">▶ Запустить БЕСКОНЕЧНУЮ рассылку (задержка 60 сек)</button>
        <button onclick="stopBroadcast()" class="red" style="margin-top:10px; padding:18px; font-size:20px;">⛔ Остановить рассылку</button>

        <div id="status" class="status"></div>
        <div id="result"></div>
    </div>
</div>

<script>
let chats = [];

function updateList() {
    let html = chats.map((c,i) => `<div>${i+1}. ${c}</div>`).join('');
    document.getElementById('chatList').innerHTML = html || 'Добавьте чаты';
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
    const pass = document.getElementById('password').value.trim();
    const res = await fetch('/auth', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:`phone=${encodeURIComponent(phone)}&code=${encodeURIComponent(code)}&password=${encodeURIComponent(pass)}`});
    const data = await res.json();
    document.getElementById('result').innerHTML = `<p>${data.message}</p>`;
}

async function addChat() {
    let chat = document.getElementById('newChat').value.trim();
    if (chat && chats.length < 10) {
        chats.push(chat);
        updateList();
        document.getElementById('newChat').value = '';
    }
}

async function startBroadcast() {
    const text = document.getElementById('text').value.trim();
    const file = document.getElementById('photoFile').files[0];

    const formData = new FormData();
    formData.append('text', text);
    chats.forEach(c => formData.append('chats', c));
    if (file) formData.append('photo', file);

    document.getElementById('status').innerHTML = '🔄 Рассылка запущена. Работает бесконечно с задержкой 60 секунд...';
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
    return HTML_CONTENT

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
                return {"status": "need_code", "message": "Код отправлен в SMS. Введите его ниже."}
            await client.sign_in(phone=phone, code=code, password=password or None)

        return {"status": "success", "message": "✅ Аккаунт успешно авторизован!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/start_broadcast")
async def start_broadcast(text: str = Form(...), chats: list = Form(...), photo: UploadFile = File(None)):
    global client, broadcast_task, is_broadcasting

    if not client:
        return {"status": "error", "message": "Сначала авторизуйте Telegram аккаунт"}

    is_broadcasting = True

    async def infinite_loop():
        while is_broadcasting:
            for chat in chats:
                if not is_broadcasting:
                    break
                try:
                    if photo and photo.filename:
                        file_bytes = await photo.read()
                        await client.send_file(chat, file_bytes, caption=text)
                    else:
                        await client.send_message(chat, text)
                    print(f"✅ Отправлено в {chat}")
                except Exception as e:
                    print(f"Ошибка в {chat}: {e}")
                await asyncio.sleep(60)  # 60 секунд задержка

    broadcast_task = asyncio.create_task(infinite_loop())
    return {"status": "success", "message": "Рассылка запущена"}

@app.post("/stop_broadcast")
async def stop_broadcast():
    global is_broadcasting
    is_broadcasting = False
    return {"status": "success", "message": "Рассылка остановлена"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
