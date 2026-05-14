# TODO: 功能待办
"""第一阶段：强壮体魄 (Stability)
	1.	[ ] 引入 PydanticAI：用 Pydantic 模型彻底规范 get_ai_response 的输入输出。
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

from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
import json
from feishu_api import FeiShuClient
from ai_agent import Agent
from constants import JARVIS_SYSTEM_PROMPT
import utils

# 实例化
jarvis = FeiShuClient()

# 飞书有个“重试机制”，当给 Webhook 发送一条消息时，它要求你的服务器在 3 秒钟内必须返回一个 200 OK，否则就会重传
# 保险1：这里定义一个简单的缓存，如果收到飞书发来相同的 event_id 就不做回应，让飞书不再请求
def preprocess(data):
    processed_event_ids = set() # TODO:转用 redis 或者 diskcache，设置一个 10 分钟自动过期的 key

    event_id = data.get("header", {}).get("event_id")
    if event_id in processed_event_ids:
        print(f"--- 拦截到重试请求: {event_id} ---")
        return {"code": 0} # 假装处理过了，让飞书闭嘴

    processed_event_ids.add(event_id)   # 没处理过的存进去
    if len(processed_event_ids) > 1000:
        processed_event_ids.clear() # 避免 set 会越来越大，最终吃光内存

# 飞书有个“重试机制”，当给 Webhook 发送一条消息时，它要求你的服务器在 3 秒钟内必须返回一个 200 OK，否则就会重传
# 保险2：这里作异步处理，先回复了飞书，再在后台慢慢处理 AI 逻辑
async def handle_logic(open_id, user_text):
    try:
        current_date = utils.format_time(utils.get_beijing_time())
        system_promt = JARVIS_SYSTEM_PROMPT.format(current_date)
        ai_reply = await Agent.get_deepseek_response(system_promt, user_text)
        await jarvis.reply(open_id, ai_reply)

    except Exception as e:
        print(f"AI 调用失败: {e}")
        await jarvis.reply(open_id, "抱歉主人，我的大脑连接 DeepSeek 时出了一点小状况。")

app = FastAPI()

# 主逻辑起点
@app.post("/webhook")
async def feishu_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    preprocess(data)

    # 处理 Challenge 验证（创建机器人的时候用）
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    # 处理消息事件
    if "header" in data:
        event_type = data["header"].get("event_type")
        
        # 判定为“接收消息”事件
        if event_type == "im.message.receive_v1":
            event = data.get("event")
            open_id = event["sender"]["sender_id"]["open_id"]   # 提取 Open ID（回复给谁）
            content_str = event["message"]["content"]
            user_text = json.loads(content_str).get("text", "")

            # 立刻把任务丢给后台，然后直接返回 200 给飞书，防止飞书因为超时而对本服务器重新发起 post 请求
            background_tasks.add_task(handle_logic, open_id, user_text)

    return {"code": 0}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
        