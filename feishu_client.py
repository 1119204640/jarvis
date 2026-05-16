import json
import httpx
import time
from constants import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_ROOT_FOLDER_TOKEN, FEISHU_BASE_URL
import logger
from uuid import uuid4

# --- 飞书工具类：管理 Token 和 API ---
class FeiShuClient:
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.root_folder = FEISHU_ROOT_FOLDER_TOKEN
        self.base_url = FEISHU_BASE_URL
        self.token = None
        self.expire = 0

    async def get_token(self):
        """
        缓存飞书机器人应用的身份证 tenant_access_token, 过期才重新请求, 避免每次调用 API 都去登录一次
        """
        if self.token and time.time() < self.expire:
            return self.token

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        json_body = {"app_id": self.app_id, 
                     "app_secret": self.app_secret}

        async with httpx.AsyncClient() as client:
            resp = await client.request("POST", url, headers=headers, json=json_body)
            data = resp.json()
            logger.info(f"tenant_access_token 刷新: respond = {json.dumps(data)}")
            self.token = data.get("tenant_access_token")
            self.expire = time.time() + data.get("expires", 7200) - 600 # 提前10分钟过期
            return self.token

    async def _request(self, request_type: str, path: str, **kwargs):
        """
        通用请求封装，自动带上 Token
        """
        token = await self.get_token()
        
        # 飞书 API 通用 http request 头部
        # Authorization: 飞书要求的鉴权头，所有接口都必须带。token 就是上一步拿到的"门禁卡"
        # Content-Type: 告诉飞书请求体是 JSON 格式、UTF-8 编码,飞书会按这个格式解析你传过去的 body
        headers = {"Authorization": f"Bearer {token}", 
                   "Content-Type": "application/json; charset=utf-8"}

        async with httpx.AsyncClient() as client:
            resp = await client.request(request_type, f"{self.base_url}{path}", headers=headers, **kwargs)
            data = resp.json()
            logger.info(f"向飞书发起 http {request_type} 请求: path = {self.base_url}{path}, headers = {headers}, json_body = {kwargs}\n respond = {data}")
            return resp.json()

    async def reply(self, open_id: str, text: str):
        """
        回复文字消息函数
        """
        path = "/im/v1/messages?receive_id_type=open_id"
        json_body = {"content": json.dumps({"text": text}), 
                     "msg_type": "text", 
                     "receive_id": open_id, 
                     "uuid": str(uuid4())}
        return await self._request("POST", path, json=json_body)

    async def create_bitable_base(self, name: str, folder_token: str):
        """
        在文件夹中创建一个新的多维表格文件 (Bitable Base)
        """
        path = "/bitable/v1/apps"
        json_body = {
            "folder_token": folder_token,
            "name": name
        }
        return await self._request("POST", path, json=json_body)