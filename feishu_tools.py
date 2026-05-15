from pydantic_ai import RunContext
from feishu_api import FeiShuClient
from ai_agent import jarvis_agent
from constants import FEISHU_ROOT_FOLDER_TOKEN
from logger import log
    
@jarvis_agent.tool
async def create_new_workspace_base(ctx: RunContext[FeiShuClient], project_name: str):
    """
    当主人说“新建个表”、“开始个新项目”或“帮我记个东西”时调用。
    用于在主文件夹下创建一个独立的多维表格文件。
    """
    client = ctx.deps
    root_folder =  FEISHU_ROOT_FOLDER_TOKEN
    
    try:
        # 1. 动作：创建 Base
        res = await client.create_base_app(project_name, root_folder)
        log(f"create_new_workspace_base! result = {res}", "success")

        # 2. 解析：提取关键信息
        app_data = res.get("data", {}).get("app", {})
        app_token = app_data.get("app_token")
        app_url = app_data.get("url")
        
        if not app_token:
            return f"Sir，Base 创建似乎卡住了，请检查我的权限或文件夹 Token。"

        # 3. 回报：把链接甩给主人
        return (f"Sir，项目《{project_name}》的基地已初始化完毕。\n"
                f"AppToken: {app_token}\n"
                f"传送门: {app_url}")
                
    except Exception as e:
        return f"报告 Sir，施工现场发生意外: {str(e)}"