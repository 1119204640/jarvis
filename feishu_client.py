import json
import os
import sqlite3
import httpx
import time
from constants import DB_DIR, DB_FILE, FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_BASE_URL, FEISHU_REDIRECT_URI
import logger
from uuid import uuid4

# --- 飞书工具类：管理 Token 和 API ---
class FeiShuClient:
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.base_url = FEISHU_BASE_URL
        self.websocket_data = None
        self.token = None
        self.expire = 0

    async def exchange_code_for_token(self, code: str):
        """
        用 OAuth 授权码换取 user_access_token + refresh_token。
        """
        url = f"{FEISHU_BASE_URL}/authen/v2/oauth/token"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        json_body = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": FEISHU_APP_ID,
            "client_secret": FEISHU_APP_SECRET,
            "redirect_uri": FEISHU_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.request("POST", url, headers=headers, json=json_body)
            data = resp.json()
            return data

    async def refresh_user_token(self, refresh_token: str):
        """
        用 refresh_token 刷新过期的 user_access_token。
        """
        url = f"{FEISHU_BASE_URL}/authen/v2/oauth/token"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        json_body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": FEISHU_APP_ID,
            "client_secret": FEISHU_APP_SECRET,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.request("POST", url, headers=headers, json=json_body)
            data = resp.json()
            return data

    # ---------- user token 持久化 ----------
    def _load_user_token(self, open_id: str):
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_FILE)
        try:
            row = conn.execute(
                "SELECT access_token, refresh_token, access_expire, refresh_expire FROM user_tokens WHERE open_id=?",
                (open_id,),
            ).fetchone()
            if row:
                return {
                    "access_token": row[0],
                    "refresh_token": row[1],
                    "access_expire": row[2],
                    "refresh_expire": row[3],
                }
            return None
        finally:
            conn.close()

    def save_user_token(self, open_id: str, access_token: str, refresh_token: str,
                        access_expire: int, refresh_expire: int):
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_FILE)
        try:
            conn.execute(
                """INSERT INTO user_tokens (open_id, access_token, refresh_token, access_expire, refresh_expire)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(open_id) DO UPDATE SET
                   access_token=excluded.access_token,
                   refresh_token=excluded.refresh_token,
                   access_expire=excluded.access_expire,
                   refresh_expire=excluded.refresh_expire,
                   updated_at=CURRENT_TIMESTAMP""",
                (open_id, access_token, refresh_token, access_expire, refresh_expire),
            )
            conn.commit()
        finally:
            conn.close()

    async def get_user_token(self, open_id: str):
        """
        获取有效的 user_access_token。
        仿照 get_enant_token 模式：缓存有效则直接返回，过期则静默刷新并写 DB。
        返回 None 表示 refresh_token 也失效，需要重新授权。
        """
        token_data = self._load_user_token(open_id)
        if token_data and time.time() < token_data["access_expire"]:
            return token_data["access_token"]

        if token_data and token_data["refresh_token"]:
            resp = await self.refresh_user_token(token_data["refresh_token"])
            if resp.get("code") == 0:
                access_token = resp.get("access_token")
                self.save_user_token(
                    open_id,
                    access_token=access_token,
                    refresh_token=resp.get("refresh_token"),
                    access_expire=int(time.time()) + resp.get("expires_in", 7200),
                    refresh_expire=int(time.time()) + resp.get("refresh_expires_in", 2592000),
                )
                return access_token

        return None

    async def get_user_info(self, user_access_token: str):
        """
        用 user_access_token 获取用户身份信息（open_id, name, email 等）。
        """
        url = f"{FEISHU_BASE_URL}/authen/v1/user_info"
        headers = {"Authorization": f"Bearer {user_access_token}"}

        async with httpx.AsyncClient() as client:
            resp = await client.request("GET", url, headers=headers)
            data = resp.json()
            return data

    async def get_enant_token(self):
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
            self.token = data.get("tenant_access_token")
            self.expire = time.time() + data.get("expires", 7200) - 600 # 提前10分钟过期
            return self.token

    async def _request(self, request_type: str, path: str, **kwargs):
        """
        通用请求封装，自动带上 Token
        """
        token = await self.get_enant_token()
        
        # 飞书 API 通用 http request 头部
        # Authorization: 飞书要求的鉴权头，所有接口都必须带。token 就是上一步拿到的"门禁卡"
        # Content-Type: 告诉飞书请求体是 JSON 格式、UTF-8 编码,飞书会按这个格式解析你传过去的 body
        headers = {"Authorization": f"Bearer {token}", 
                   "Content-Type": "application/json; charset=utf-8"}

        async with httpx.AsyncClient() as client:
            resp = await client.request(request_type, f"{self.base_url}{path}", headers=headers, **kwargs)
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