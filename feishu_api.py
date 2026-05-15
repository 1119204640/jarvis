import json
import httpx
import time
import utils
from constants import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_ROOT_FOLDER_TOKEN, FEISHU_BASE_URL

# --- 飞书工具类：管理 Token 和 API ---
class FeiShuClient:
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.root_folder = FEISHU_ROOT_FOLDER_TOKEN
        self.base_url = FEISHU_BASE_URL
        self.token = None
        self.expire = 0

    # 缓存 tenant_access_token，过期会自动重新取
    async def get_token(self):
        if self.token and time.time() < self.expire:
            return self.token
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url=url, json = {"app_id": self.app_id, "app_secret": self.app_secret})
            data = resp.json()
            self.token = data.get("tenant_access_token")
            self.expire = time.time() + data.get("expires", 7200) - 600 # 提前10分钟过期
            return self.token

    # 通用请求封装，自动带上 Token
    async def _request(self, method: str, path: str, **kwargs):
        token = await self.get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
        async with httpx.AsyncClient() as client:
            resp = await client.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
            return resp.json()

    # 回复文字消息函数
    async def reply(self, open_id: str, text: str):
        path = "/im/v1/messages?receive_id_type=open_id"
        content = json.dumps({"text": text})
        payload = {"receive_id": open_id, "msg_type": "text", "content": content}
        return await self._request("POST", path, json=payload)

    # 在指定文件夹下创建一个多维表格。
    async def create_bitable(self, name: str, folder_token: str):
        path = "/bitable/v1/apps"
        payload = {
            "name": name,
            "folder_token": folder_token
        }
        return await self._request("POST", path, json=payload)