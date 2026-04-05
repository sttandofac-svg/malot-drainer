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

app = FastAPI(title="Mass Sender")

client = None
chats = []
broadcast_task = None
is_broadcasting = False

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Mass Sender</title>
    <style>
        body { background:#0a0a0a; color:#eee; font-family:Arial; padding:20px; }
        .container { max-width:800px; margin:auto; background:#1a1a1a; padding:30px; border-radius:16px; }
        input, textarea, button { width:100%; padding:14px; margin:10px 0; border-radius:10px; border:none; }
        input, textarea { background:#333; color:white; }
        button { background:#0066ff; color:white; font-weight:bold; cursor:pointer; }
        button:hover { background:#0055cc; }
        .red { background:#cc0000 !important; }
        .section { background:#252525; padding:20px; border-radius:12px; margin:25px 0; }
        .status { padding:15px; border-radius:10px; margin:15px 0; font-size:18px; }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Mass Sender</h1>

    <div class="section">
        <h2>Авторизация</h2>
        <input type="text" id="phone" placeholder="+79xxxxxxxxx">
        <button onclick="sendPhone()">Отправить номер</button>
        <div id="codeBlock" style="display:none;margin-top:15px;">
            <input type="text" id="code" placeholder="Код из SMS">
            <input type="password" id="password" placeholder="Пароль 2FA">
            <button onclick="sendCode()">Отправить код и пароль</button>
        </div>
    </div>

    <div class="section">
        <h2>Рассылка</h2>
        <input type="text" id="newChat" placeholder="@username или -1001234567890">
        <button onclick="addChat()">+ Добавить чат</button>
        <div id="chatList" style="margin:15px 0; background:#222; padding:12px; border-radius:8px;"></div>

        <textarea id="text" rows="5" placeholder="Текст сообщения..."></textarea>
        <input type="file" id="photoFile" accept="image/*">

        <button onclick="startBroadcast()" style="background:#00cc00;padding:18px;font-size:20px;">▶ Запустить БЕСКОНЕЧНУЮ рассылку</button>
        <button onclick="stopBroadcast()" class="red" style="margin-top:10px;padding:18px;font-size:20px;">⛔ Остановить</button>

        <div id="status" class="status"></div>
    </div>
</div>

<script>
let chats = [];

function updateList() {
    document.getElementById('chatList').innerHTML = chats.map((c,i) => `<div>${i+1}. ${c}</div>`).join('') || 'Чатов пока нет';
}

async function sendPhone() {
    const phone = document.getElementById('phone').value.trim();
    const res = await fetch('/auth', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:`phone=${encodeURIComponent(phone)}`});
    const data = await res.json();
    if (data.status === "need_code") document.getElementById('codeBlock').style.display = 'block';
    document.getElementById('status').innerHTML = data.message;
}

async function sendCode() {
    const phone = document.getElementById('phone').value.trim();
    const code = document.getElementById('code').value.trim();
    const pass = document.getElementById('password').value.trim();
    const res = await fetch('/auth', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:`phone=${encodeURIComponent(phone)}&code=${encodeURIComponent(code)}&password=${encodeURIComponent(pass)}`});
    const data = await res.json();
    document.getElementById('status').innerHTML = data.message;
}

async function addChat() {
    let c = document.getElementById('newChat').value.trim();
    if (c) chats.push(c);
    updateList();
    document.getElementById('newChat').value = '';
}

async function startBroadcast() {
    const text = document.getElementById('text').value.trim();
    const file = document.getElementById('photoFile').files[0];

    const formData = new FormData();
    formData.append('text', text);
    chats.forEach(chat => formData.append('chats', chat));
    if (file) formData.append('photo', file);

    document.getElementById('status').innerHTML = '🔄 Рассылка запущена (задержка 60 сек)...';
    await fetch('/start_broadcast', {method:'POST', body:formData});
}

async function stopBroadcast() {
    await fetch('/stop_broadcast', {method:'POST'});
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
                return {"status": "need_code", "message": "Код отправлен в SMS"}
            await client.sign_in(phone=phone, code=code, password=password or None)

        return {"status": "success", "message": "✅ Аккаунт авторизован!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/start_broadcast")
async def start_broadcast(text: str = Form(...), chats: list = Form(...), photo: UploadFile = File(None)):
    global client, broadcast_task, is_broadcasting

    if not client:
        return {"status": "error", "message": "Аккаунт не авторизован"}

    is_broadcasting = True

    async def infinite():
        count = 0
        while is_broadcasting:
            for chat in chats:
                if not is_broadcasting: break
                try:
                    if photo and photo.filename:
                        bytes_data = await photo.read()
                        await client.send_file(chat, bytes_data, caption=text)
                    else:
                        await client.send_message(chat, text)
                    count += 1
                    print(f"[{count}] Отправлено в {chat}")
                except Exception as e:
                    print(f"Ошибка отправки в {chat}: {e}")
                await asyncio.sleep(60)
    broadcast_task = asyncio.create_task(infinite())
    return {"status": "success"}

@app.post("/stop_broadcast")
async def stop_broadcast():
    global is_broadcasting
    is_broadcasting = False
    return {"status": "success", "message": "Рассылка остановлена"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
