# TODO: 功能待办
"""第一阶段：强壮体魄 (Stability)
	1.	[X] 引入 PydanticAI：用 Pydantic 模型彻底规范 ai 的输入输出。
	2.	[ ] 工具解耦：将 add_task_record 改为 PydanticAI 装饰器模式，并提取到独立的 tools/ 文件夹。
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
from contextlib import contextmanager
import os

from feishu_client import FeiShuClient
import deepseek_agent as agent
import logger
from constants import DB_DIR, DB_FILE

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


async def _handle_logic(open_id, user_text):
    """作异步处理，先回复了飞书，再在后台慢慢处理 AI 逻辑"""
    client = FeiShuClient()
    try:
        ai_reply = await agent.get_ai_reply(user_text, client)
        await client.reply(open_id, ai_reply)

    except Exception as e:
        logger.error(f"AI 调用失败，飞书报错", e)
        await client.reply(open_id, "抱歉主人，我的大脑连接 DeepSeek 时出了一点小状况。")

app = FastAPI()

# 主逻辑起点
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
                content_str = event["message"]["content"]
                user_text = json.loads(content_str).get("text", "")

                # TODO:立刻把任务丢给后台，然后直接返回 200 给飞书，防止飞书因为超时而对本服务器重新发起 post 请求
                background_tasks.add_task(_handle_logic, open_id, user_text)
                
        except Exception as e:
            # 如果内部业务崩了，这里可以不返回 200，让飞书待会儿合理重试
            raise HTTPException(status_code=500, detail=str(e))

    return {"code": 0}

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8001)
        