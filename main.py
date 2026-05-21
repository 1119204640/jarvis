# TODO: 功能待办
"""第一阶段：强壮体魄 (Stability)
	1.	[X] 引入 PydanticAI：用 Pydantic 模型彻底规范 ai 的输入输出。
	2.	[ ] 工具解耦：改为 PydanticAI 装饰器模式。
	3.	[ ] 消息签名校验：利用飞书 Secret 校验请求合法性，挡掉那些 404 扫描器。
    4.  [ ] 增加消息卡片：机器人回一个按钮卡片，上面直接带“结束任务”、“撤销任务“、“查看所有任务“的按钮
第二阶段：短期记忆 (Context)
	1.	[ ] SQLite 对话持久化：存储最近 20 轮对话，让 Jarvis 知道“它”是指代刚才说的那个任务。
	2.	[ ] Action Log 记录：在 SQLite 中记录每一次 API 操作的详细结果（包含 Bitable 的 ID）。
第三阶段：逻辑闭环 (Reasoning)
	1.	[ ] LangGraph 状态机：构建任务流，正式实现 “撤销刚才的记录” 指令。
	2.	[ ] 流式输出（可选）：优化响应体验，虽然飞书不支持打字机效果，但可以内部做流式处理。
第四阶段：长期智能 (Knowledge)
	1.	[ ] RAG 知识库：引入 ChromaDB，实现基于历史记录的任务搜索。
	2.	[ ] 主动提醒：结合服务器定时任务，让 AI 主动分析表格并发送“早报”。"""
# ------------------------------------------------------

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
import uvicorn
import json
import sqlite3
import time
from contextlib import contextmanager, asynccontextmanager
import os
import asyncio
import threading
import lark_oapi as lark
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler

from feishu_client import FeiShuClient
import deepseek_agent as agent
import logger
import message_history
from constants import DB_DIR, DB_FILE, FEISHU_OAUTH_AUTHORIZE_URL, FEISHU_APP_ID, FEISHU_APP_SECRET

# 极其稳健的数据库连接上下文管理器，自动处理关闭和事务
@contextmanager
def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                open_id TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                access_expire INTEGER,
                refresh_expire INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def check_and_record_event(event_id):
    """
    检查飞书消息事件是否重复。
    返回 True: 首次出现，已成功记录（放行）
    返回 False: 重复出现（拦截）
    """
    if not event_id:
        return True # 如果没有 event_id，默认放行防漏（虽然飞书一定有）

    with get_db() as conn:
        try:
            # 尝试插入。如果 event_id 已存在，会触发主键冲突报错
            conn.execute(
                "INSERT INTO processed_events (event_id) VALUES (?)",
                (event_id,)
            )
            conn.commit()
            return True # 没有报错，说明是第一次见的新消息
        except sqlite3.IntegrityError:
            return False # 触发冲突，说明是重复的重试消息

# 主事件循环引用，供 WS 回调线程投递协程
_main_loop: asyncio.AbstractEventLoop = None

def on_ws_message(event: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """WS 长连接回调（SDK 内部线程调用），收到消息后投递到主事件循环"""
    msg_type = event.event.message.message_type
    if msg_type != "text":
        return

    open_id = event.event.sender.sender_id.open_id
    chat_id = event.event.message.chat_id
    content = event.event.message.content
    user_text = json.loads(content).get("text", "")

    event_id = event.header.event_id
    if not check_and_record_event(event_id):
        return

    asyncio.run_coroutine_threadsafe(_handle_logic(chat_id, open_id, user_text), _main_loop)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop
    _main_loop = asyncio.get_running_loop()

    handler = (
        EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_ws_message)
        .build()
    )
    ws_client = lark.ws.Client(
        app_id=FEISHU_APP_ID,
        app_secret=FEISHU_APP_SECRET,
        event_handler=handler,
        log_level=lark.LogLevel.INFO,
    )
    t = threading.Thread(target=ws_client.start, daemon=True)
    t.start()
    logger.success("WebSocket 长连接已启动")

    await agent.init_mcp()

    yield

    await agent.shutdown_mcp()
    # daemon 线程随进程退出自动结束

async def _handle_logic(chat_id, open_id, user_text):
    """作异步处理，先回复了飞书，再在后台慢慢处理 AI 逻辑"""
    feishu = FeiShuClient()

    user_token = await feishu.get_user_token(open_id)
    if not user_token:
        await feishu.reply(open_id, f"请先授权：{FEISHU_OAUTH_AUTHORIZE_URL}")
        return

    try:
        history = message_history.get_history(chat_id)
        message_history.append(chat_id, "user", user_text)
        ai_reply = await agent.get_ai_reply(user_text, feishu, history)
        message_history.append(chat_id, "assistant", ai_reply)
        await feishu.reply(open_id, ai_reply)

    except Exception as e:
        logger.error(f"AI 调用失败，飞书报错", str(e))
        await feishu.reply(open_id, "抱歉主人，我的大脑连接 DeepSeek 时出了一点小状况。")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def feishu_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    # 处理 Challenge 验证（创建机器人的时候用）
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    # 处理消息事件
    if "header" in data:
        event_type = data["header"].get("event_type")
        event_id = data["header"].get("event_id")
        if not check_and_record_event(event_id):
            return {"code": 200, "msg": "ignore duplicate historical event"}

        try:
            # 判定为“接收消息”事件
            if event_type == "im.message.receive_v1":
                event = data.get("event")
                open_id = event["sender"]["sender_id"]["open_id"]   # 提取 Open ID（回复给谁）
                chat_id = event["message"]["chat_id"]
                content_str = event["message"]["content"]
                user_text = json.loads(content_str).get("text", "")

                # 立刻把任务丢给后台，然后直接返回 200 给飞书，防止飞书因为超时而对本服务器重新发起 post 请求
                background_tasks.add_task(_handle_logic, chat_id, open_id, user_text)
                
        except Exception as e:
            # 如果内部业务崩了，这里可以不返回 200，让飞书待会儿合理重试
            raise HTTPException(status_code=500, detail=str(e))

    return {"code": 0}

@app.get("/oauth/callback")
async def oauth_callback(code: str):
    if not code:
        raise HTTPException(status_code=400, detail="缺少 authorization code")

    feishu = FeiShuClient()
    data = await feishu.exchange_code_for_token(code)

    if data.get("code") != 0:
        raise HTTPException(status_code=400, detail=f"换 token 失败: {data}")

    # 用 access_token 获取用户 open_id
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    access_expire = int(time.time()) + data.get("expires_in", 7200)
    refresh_expire = int(time.time()) + data.get("refresh_expires_in", 2592000)

    user_info = await feishu.get_user_info(access_token)
    if user_info.get("code") != 0:
        raise HTTPException(status_code=400, detail=f"获取用户信息失败: {user_info}")

    open_id = user_info.get("data", {}).get("open_id")
    if not open_id:
        raise HTTPException(status_code=400, detail="未能获取到 open_id")

    feishu.save_user_token(open_id, access_token, refresh_token, access_expire, refresh_expire)
    logger.success("OAuth 授权成功", {"open_id": open_id, "access_token": access_token})

    return {"code": 0, "msg": "授权成功", "open_id": open_id}

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8001)