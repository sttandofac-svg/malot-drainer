from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

app = FastAPI(title="Mass Sender - Один файл")

client = None
string_session = None

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mass Sender</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: #1f1f1f; padding: 30px; border-radius: 12px; }
        input, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: none; }
        input { background: #333; color: white; }
        button { background: #0066ff; color: white; font-weight: bold; cursor: pointer; }
        button:hover { background: #0055dd; }
        .result { margin-top: 20px; padding: 15px; border-radius: 8px; }
        .success { background: #004d00; }
        .error { background: #4d0000; }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Mass Sender</h1>
    <h2>Добавить аккаунт</h2>
    
    <input type="text" id="phone" placeholder="+79161234567" required>
    <button onclick="sendPhone()">1. Отправить номер</button>

    <div id="codeBlock" style="display:none;">
        <input type="text" id="code" placeholder="Код из SMS">
        <input type="password" id="password" placeholder="Пароль 2FA (если есть, иначе оставь пустым)">
        <button onclick="sendCode()">2. Отправить код и пароль</button>
    </div>

    <div id="result" class="result"></div>
</div>

<script>
async function sendPhone() {
    const phone = document.getElementById('phone').value;
    const res = await fetch('/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `phone=${encodeURIComponent(phone)}`
    });
    const data = await res.json();
    document.getElementById('result').innerHTML = `<p>${data.message}</p>`;
    if (data.status === "need_code") {
        document.getElementById('codeBlock').style.display = 'block';
    }
}

async function sendCode() {
    const phone = document.getElementById('phone').value;
    const code = document.getElementById('code').value;
    const password = document.getElementById('password').value || "";

    const res = await fetch('/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `phone=${encodeURIComponent(phone)}&code=${encodeURIComponent(code)}&password=${encodeURIComponent(password)}`
    });
    const data = await res.json();
    
    const resultDiv = document.getElementById('result');
    if (data.status === "success") {
        resultDiv.className = "result success";
        resultDiv.innerHTML = `<strong>✅ Успех!</strong><br>${data.message}`;
    } else {
        resultDiv.className = "result error";
        resultDiv.innerHTML = `<strong>❌ Ошибка</strong><br>${data.message}`;
    }
}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.post("/add")
async def add_account(phone: str = Form(...), code: str = Form(None), password: str = Form(None)):
    global client, string_session

    try:
        if not client:
            client = TelegramClient(StringSession(""), API_ID, API_HASH)

        await client.connect()

        if not await client.is_user_authorized():
            if code is None:
                await client.send_code_request(phone)
                return {"status": "need_code", "message": "Код отправлен в SMS. Введите его ниже."}

            await client.sign_in(phone=phone, code=code, password=password or None)

        string_session = client.session.save()
        return {"status": "success", "message": "Аккаунт успешно авторизован! Теперь можно делать рассылку."}

    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
