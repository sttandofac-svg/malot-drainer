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
chats = []        # список чатов для рассылки

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
        .section { margin: 25px 0; padding: 15px; background: #2a2a2a; border-radius: 10px; }
        .success { color: #00ff88; }
        .error { color: #ff6666; }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Mass Sender</h1>

    <!-- === СЕКЦИЯ АВТОРИЗАЦИИ === -->
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

    <!-- === СЕКЦИЯ РАССЫЛКИ === -->
    <div class="section">
        <h2>2. Панель рассылки</h2>
        
        <h3>Каналы/чаты (до 10)</h3>
        <input type="text" id="newChat" placeholder="@channel или -1001234567890">
        <button onclick="addChat()">+ Добавить</button>
        <div id="chatList" style="margin:10px 0; min-height:60px;"></div>

        <h3>Текст сообщения</h3>
        <textarea id="text" rows="5" placeholder="Текст для рассылки..."></textarea>

        <h3>Фото (опционально)</h3>
        <input type="text" id="photo" placeholder="Ссылка на фото (https://...) или оставь пустым">

        <button onclick="startBroadcast()" style="background:#00cc00; padding:15px;">▶ Запустить рассылку</button>
    </div>

    <div id="result" style="margin-top:20px; padding:15px; border-radius:8px; min-height:50px;"></div>
</div>

<script>
let chats = [];

function updateChatList() {
    let html = chats.map((c,i) => `<div>${i+1}. ${c}</div>`).join('');
    document.getElementById('chatList').innerHTML = html || 'Пока нет каналов';
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
        document.getElementById('result').innerHTML = '<p class="error">Добавьте хотя бы один канал!</p>';
        return;
    }
    if (!text) {
        document.getElementById('result').innerHTML = '<p class="error">Введите текст сообщения!</p>';
        return;
    }

    document.getElementById('result').innerHTML = '<p>Запускаю рассылку...</p>';

    const res = await fetch('/broadcast', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({chats: chats, text: text, photo: photo})
    });

    const data = await res.json();
    document.getElementById('result').innerHTML = `<p class="${data.status==='success'?'success':'error'}">${data.message}</p>`;
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
                return {"status": "need_code", "message": "Код отправлен в SMS. Введите его ниже."}
            await client.sign_in(phone=phone, code=code, password=password or None)

        return {"status": "success", "message": "Аккаунт успешно авторизован!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/broadcast")
async def broadcast(data: dict):
    global client
    if not client:
        return {"status": "error", "message": "Аккаунт не авторизован"}

    chats = data.get("chats", [])
    text = data.get("text", "")
    photo = data.get("photo", "")

    success = 0
    for chat in chats:
        try:
            if photo:
                await client.send_file(chat, photo, caption=text)
            else:
                await client.send_message(chat, text)
            success += 1
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"Ошибка в {chat}: {e}")

    return {"status": "success", "message": f"Рассылка завершена! Успешно отправлено в {success} из {len(chats)} чатов."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
