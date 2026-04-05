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
photo_bytes = None   # храним фото в памяти

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Mass Sender</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: #000; 
            color: #fff; 
            margin: 0; 
            padding: 15px; 
            line-height: 1.4;
        }
        .container { 
            max-width: 100%; 
            background: #111; 
            border-radius: 20px; 
            padding: 25px 20px; 
            box-shadow: 0 4px 30px rgba(0,0,0,0.6);
        }
        h1 { text-align: center; color: #00ffaa; margin-bottom: 25px; }
        input, textarea, button { 
            width: 100%; 
            padding: 16px; 
            margin: 12px 0; 
            border-radius: 14px; 
            border: none; 
            font-size: 17px;
        }
        input, textarea { background: #222; color: #fff; }
        button { 
            background: #0066ff; 
            color: white; 
            font-weight: 600; 
            font-size: 18px; 
            padding: 18px;
        }
        button.red { background: #ff2d55; }
        .section { 
            background: #1c1c1e; 
            padding: 20px; 
            border-radius: 18px; 
            margin: 25px 0; 
        }
        .status { 
            padding: 18px; 
            border-radius: 14px; 
            font-size: 17px; 
            margin: 15px 0; 
            text-align: center;
        }
        .success { background: #004d00; }
        .error { background: #4d0000; }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Mass Sender</h1>

    <div class="section">
        <h2>Авторизация</h2>
        <input type="text" id="phone" placeholder="+79xxxxxxxxx" style="font-size:18px;">
        <button onclick="sendPhone()">Отправить номер</button>

        <div id="codeBlock" style="display:none;">
            <input type="text" id="code" placeholder="Код из SMS" style="font-size:18px;">
            <input type="password" id="password" placeholder="Пароль 2FA (если есть)">
            <button onclick="sendCode()">Отправить код и пароль</button>
        </div>
    </div>

    <div class="section">
        <h2>Бесконечная рассылка</h2>
        
        <input type="text" id="newChat" placeholder="@канал или -1001234567890" style="font-size:17px;">
        <button onclick="addChat()">+ Добавить чат</button>
        <div id="chatList" style="margin:15px 0; background:#2c2c2e; padding:15px; border-radius:12px; min-height:70px;"></div>

        <textarea id="text" rows="5" placeholder="Текст сообщения..." style="font-size:17px;"></textarea>

        <h3 style="margin:15px 0 8px 0;">Фото (можно загрузить)</h3>
        <input type="file" id="photoFile" accept="image/*">

        <button onclick="startBroadcast()" style="background:#00cc00; padding:20px; font-size:20px; margin-top:15px;">▶ Запустить бесконечную рассылку</button>
        <button onclick="stopBroadcast()" class="red" style="padding:20px; font-size:20px;">⛔ Остановить рассылку</button>

        <div id="status" class="status"></div>
    </div>
</div>

<script>
let chats = [];

function updateList() {
    document.getElementById('chatList').innerHTML = chats.map((c,i) => `<div style="padding:8px 0;border-bottom:1px solid #444;">${i+1}. ${c}</div>`).join('');
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
    if (c) {
        chats.push(c);
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

    document.getElementById('status').innerHTML = '🔄 Рассылка запущена (задержка 60 сек между сообщениями)';
    await fetch('/start_broadcast', {method: 'POST', body: formData});
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
                return {"status": "need_code", "message": "Код отправлен в SMS"}
            await client.sign_in(phone=phone, code=code, password=password or None)

        return {"status": "success", "message": "✅ Аккаунт авторизован!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/start_broadcast")
async def start_broadcast(text: str = Form(...), chats: list = Form(...), photo: UploadFile = File(None)):
    global client, broadcast_task, is_broadcasting, photo_bytes

    if not client:
        return {"status": "error", "message": "Аккаунт не авторизован"}

    # Сохраняем фото в память один раз
    photo_bytes = None
    if photo and photo.filename:
        photo_bytes = await photo.read()

    is_broadcasting = True

    async def infinite():
        count = 0
        while is_broadcasting:
            for chat in chats:
                if not is_broadcasting: break
                try:
                    if photo_bytes:
                        await client.send_file(chat, photo_bytes, caption=text)
                    else:
                        await client.send_message(chat, text)
                    count += 1
                    print(f"[{count}] Успешно отправлено в {chat}")
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
