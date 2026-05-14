import json
import httpx
import time
from constants import FEISHU_APP_ID, FEISHU_APP_SECRET
import utils

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

    # 添加任务到多维表格
    async def add_task_record(self, task_name: str):
        token = await self.get_token()

        # 暂时先写死
        app_id = 'MxWcbAVQlaYqRVsC4p3c1zepndc'
        table_id = 'tbl4AJYfq9jK6CV3'

        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_id}/tables/{table_id}/records"

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
            utils.log_info(json.dumps(result, indent=2))

            if result.get("code") == 0:
                utils.log_success(f"{task_name} 成功")
                return True
            else:
                utils.log_error(f"失败: {result.get('msg')}")
                return False