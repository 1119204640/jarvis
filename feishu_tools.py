from pydantic_ai import RunContext
from feishu_api import FeiShuClient
from ai_agent import jarvis_agent  # 导入你的 agent 实例
from constants import FEISHU_ROOT_FOLDER_TOKEN

@jarvis_agent.tool
async def create_new_base(ctx: RunContext[FeiShuClient], table_name: str):
    """
    当主人想要创建一个新的多维表格（Base）、开始一个新项目、或者建立新的数据库时调用。
    table_name: 提取主人话语中的项目名称，例如 '游戏攻略'、'TikTok 运营表'。
    """
    client = ctx.deps  # 获取 main.py 传进来的飞书客户端实例
    
    root_folder =  FEISHU_ROOT_FOLDER_TOKEN
    
    try:
        res = await client.create_bitable(table_name, root_folder)
        
        # 飞书返回的数据里包含新表的链接和 Token
        app_data = res.get("data", {}).get("app", {})
        app_url = app_data.get("url", "未知链接")
        
        return f"Sir，新表《{table_name}》已在您的 Workspace 中创建完毕。\n查看地址：{app_url}"
    
    except Exception as e:
        return f"报告 Sir，创建表格时遇到阻碍：{str(e)}"