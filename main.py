# TODO: 项目待办
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
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import uvicorn
import json
import httpx
import time

# 这行代码会自动寻找当前目录下的 .env 文件，并将其变量加载到系统环境变量中
load_dotenv()

DEEP_SEEK_KEY = os.getenv("DEEP_SEEK_KEY")
DEEP_SEEK_URL = "https://api.deepseek.com/chat/completions"

# 请求 DeepSeek 获取 AI 回复
async def get_ai_response(user_text: str):
    headers = {
        "Authorization": f"Bearer {DEEP_SEEK_KEY}",
        "Content-Type": "application/json"
    }
    
    # 这里的 System Prompt 是灵魂，决定了 Jarvis 的性格
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": "你是一个名为 Jarvis 的全能私人助理。语气要干练、专业且略带幽默。你目前可以帮主人记录任务到飞书多维表格中。"},
            {"role": "user", "content": user_text}
        ],
        "stream": False,
        "temperature": 0.7  # Flash 模型通常可以稍微调高一点温度来增加灵活性
    }

    async with httpx.AsyncClient() as client:
        # 设置一个稍长点的超时，AI 思考需要时间
        resp = await client.post(DEEP_SEEK_URL, json=payload, headers=headers, timeout=30)
        result = resp.json()
        return result['choices'][0]['message']['content']


FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

app = FastAPI()

# --- 飞书工具类：管理 Token 和 API ---
class FeiShuClient:
    def __init__(self):
        self.token = None
        self.expire = 0
    
    # 自动获取并缓存 tenant_access_token
    async def get_token(self):
        if self.token and time.time() < self.expire:
            return self.token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url=url, json = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET})
            data = resp.json()
            self.token = data.get("tenant_access_token")
            self.expire = time.time() + data.get("expires", 7200) - 600 # 提前10分钟过期
            return self.token

    # 回复文字消息函数
    async def reply(self, open_id: str, text: str):
        token = await self.get_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        content = json.dumps({"text": text})
        payload = {
            "receive_id": open_id,
            "msg_type": "text",
            "content": content,
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url=url, json=payload, headers=headers)
            # print(f"回复消息结果: {json.dumps(resp.json(), indent=4, ensure_ascii=False)}")

    # 添加任务到多维表格
    async def add_task_record(self, task_name: str):
        token = await self.get_token()

        # 暂时先写死
        app_id = 'MxWcbAVQlaYqRVsC4p3c1zepndc'
        table_id = 'tbl4AJYfq9jK6CV3'

        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_id}/tables/{table_id}/records"
        print(f"表格 url = {url}")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        # 构造多维表格的字段数据
        # 假设你的表有两列：[任务名称] (文本) 和 [开始时间] (日期)
        now_ms = int(time.time() * 1000) # 飞书日期字段需要毫秒
        payload = {
            "fields": {
                "任务名称": task_name,
                "开始时间": now_ms,
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            result = response.json()
            print(json.dumps(result, indent=2))

            if result.get("code") == 0:
                print(f"{task_name} 成功")
                return True
            else:
                print(f"失败: {result.get('msg')}")
                return False

# 实例化
jarvis = FeiShuClient()

# 飞书有个“重试机制”，当给 Webhook 发送一条消息时，它要求你的服务器在 3 秒钟内必须返回一个 200 OK，否则就会重传
# 在全局定义一个简单的缓存，TODO:转用 redis 或者 diskcache，设置一个 10 分钟自动过期的 key
processed_event_ids = set()

# 以防万一，这里异步处理，先回复了飞书，再在后台慢慢处理 AI 逻辑
async def handle_logic(open_id, user_text):
    try:
        ai_reply = await get_ai_response(user_text)
        await jarvis.reply(open_id, ai_reply)
    except Exception as e:
        print(f"AI 调用失败: {e}")
        await jarvis.reply(open_id, "抱歉主人，我的大脑连接 DeepSeek 时出了一点小状况。")

@app.post("/webhook")
async def feishu_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    # TODO: 调试后删除
    # print("----------- origin message  -----------")
    # print(json.dumps(data, indent=4))

    # 记下处理过的 event_id。如果同样的 ID 又来了，直接无视它
    event_id = data.get("header", {}).get("event_id")
    if event_id in processed_event_ids:
        print(f"--- 拦截到重试请求: {event_id} ---")
        return {"code": 0} # 假装处理过了，让飞书闭嘴

    processed_event_ids.add(event_id)   # 没处理过的存进去
    if len(processed_event_ids) > 1000:
        processed_event_ids.clear() # 避免 set 会越来越大，最终吃光内存

    # 1. 处理 Challenge 验证 (注意用 .get 避免 KeyError)
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    # 2. 处理消息事件
    if "header" in data:
        event_type = data["header"].get("event_type")
        
        # 判定为“接收消息”事件
        if event_type == "im.message.receive_v1":
            event = data.get("event")
            # 提取 Open ID（回复给谁）
            open_id = event["sender"]["sender_id"]["open_id"]
            # 提取 消息文本（内容）
            content_str = event["message"]["content"]
            user_text = json.loads(content_str).get("text", "")

            # 核心：立刻把任务丢给后台，然后直接返回 200 给飞书，防止飞书因为超时而对本服务器重新发起 post 请求
            background_tasks.add_task(handle_logic, open_id, user_text)

    return {"code": 0}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
        