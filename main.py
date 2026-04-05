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
chats = []          # список chat_id или username для рассылки
message_text = ""

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mass Sender</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 700px; margin: auto; background: #1f1f1f; padding: 30px; border-radius: 12px; }
        input, textarea, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: none; }
        input, textarea { background: #333; color: white; }
        button { background: #0066ff; color: white; font-weight: bold; cursor: pointer; }
        button:hover { background: #0055dd; }
        .list { background: #2a2a2a; padding: 15px; border-radius: 8px; margin: 10px 0; }
        .success { color: #00ff00; }
        .error { color: #ff4444; }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Mass Sender</h1>
    <h2>Панель рассылки</h2>

    <h3>1. Добавленные каналы/чаты (максимум 10)</h3>
    <div id="chatList" class="list">Пока ничего не добавлено</div>

    <input type="text" id="newChat" placeholder="@username или chat_id">
    <button onclick="addChat()">+ Добавить канал/чат</button>

    <h3>2. Текст сообщения</h3>
    <textarea id="text" rows="6" placeholder="Текст для рассылки..."></textarea>

    <button onclick="startBroadcast()" style="background:#00cc00;">▶ Запустить рассылку</button>

    <div id="result" style="margin-top:20px; padding:15px; border-radius:8px;"></div>
</div>

<script>
let chats = [];

function updateList() {
    let html = chats.map((c, i) => `<div>${i+1}. ${c}</div>`).join('');
    document.getElementById('chatList').innerHTML = html || 'Пока ничего не добавлено';
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
        body: JSON.stringify({chats: chats, text: text})
    });

    const data = await res.json();
    document.getElementById('result').innerHTML = `<p class="${data.status === 'success' ? 'success' : 'error'}">${data.message}</p>`;
}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.post("/broadcast")
async def broadcast(data: dict):
    global client
    chats = data.get("chats", [])
    text = data.get("text", "")

    if not client:
        return {"status": "error", "message": "Аккаунт не авторизован. Добавьте аккаунт сначала."}

    success = 0
    failed = 0

    for chat in chats:
        try:
            await client.send_message(chat, text)
            success += 1
            await asyncio.sleep(2)  # небольшая задержка
        except Exception as e:
            failed += 1
            print(f"Ошибка отправки в {chat}: {e}")

    return {
        "status": "success",
        "message": f"Рассылка завершена! Успешно: {success}, Ошибок: {failed}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
