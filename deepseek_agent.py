from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import constants
from feishu_client import FeiShuClient
from utils import get_current_date_str
import logger

# 接 DeepSeek 模型
deepseek_model = OpenAIChatModel(
    model_name=constants.DEEPSEEK_MODEL,
    provider=OpenAIProvider(api_key=constants.DEEPSEEK_KEY, base_url=constants.DEEPSEEK_URL),
)

#  ------------------------------------------------------------------------------------------                                                                                                                          
#  实例化核心智能体
                                                                                                                                                                                                                     
#  注意：此处刻意不设置 output_type。                                                                                                                                                                                  
                                                                                                                                                                                                                     
#  当给 Agent 设置 output_type（如 JarvisResponseSchema）时，pydantic-ai 底层会自动生成                                                                                                                                
#  一个内部“输出工具”（kind='output'），与用户通过 @agent.tool 注册的函数工具一并发送给                                                                                                                                
#  模型。在 tool_choice='auto' 的情况下，模型看到输出工具是一个合法的“快捷出口”，可能直接                                                                                                                              
#  调用它返回一段文本结束对话，完全跳过真正需要执行的函数工具（如 create_new_base）。                                                                                                                                  
                                                                                                                                                                                                                     
#  现象：工具注册正确、工具列表里也存在，但函数体永远不会被调用。                                                                                                                                                      
#  解决：去掉 output_type，让模型只剩下纯文本回复 + 函数工具两条路。系统提示词中要求                                                                                                                                   
#  “必须先调用工具”的指令就能真正约束模型行为。                                                                                                                                                                        
#  ------------------------------------------------------------------------------------------  

jarvis_agent = Agent(
    model=deepseek_model,
    # output_type=JarvisResponseSchema,                  # 强制要求 AI 返回上面的 JSON 结构
    system_prompt=constants.JARVIS_SYSTEM_PROMPT,      # 静态的基础性格设定
    deps_type=FeiShuClient,                            # 声明工具将要使用的依赖类型
    retries=3                                          # 如果 AI 格式写错，框架自动打回重做最多 3 次
)

# 动态系统提示词注入
# 这个装饰器会在每次 jarvis_agent.run() 触发前自动执行，把最新的时间塞给 AI
@jarvis_agent.system_prompt
def inject_dynamic_context(ctx: RunContext[FeiShuClient]) -> str:
    return f"\n【系统动态参数】\n当前北京时间是: {get_current_date_str()}"

# 会返回 AgentRunResult 对象
async def get_agent_run_result(user_text, client_instance):
    resp_obj = await jarvis_agent.run(user_text, deps=client_instance)
    return resp_obj

async def get_ai_reply(user_text, client_instance):
    result = await get_agent_run_result(user_text, client_instance)
    logger.info("agent run result", result)
    return result.output

# region 注册 Agent 工具，pydantic_ai 会根据函数内部注释自动调用

@jarvis_agent.tool # 相当于 agent.tool(create_new_base)
async def create_new_base(ctx: RunContext[FeiShuClient], base_name: str):
    """
    当主人说“新建个表”、“开始个新项目”或“帮我记个东西”时调用。
    用于在飞书主文件夹下创建一个独立的多维表格文件。
    """
    client = ctx.deps
    root_folder =  constants.FEISHU_ROOT_FOLDER_TOKEN
    
    try:
        res = await client.create_bitable_base(base_name, root_folder)

        app_data = res.get("data", {}).get("app", {})
        app_token = app_data.get("app_token")
        app_url = app_data.get("url")
        
        if not app_token:
            return f"not app_token | Base 的创建似乎卡住了，请检查权限或文件夹 Token。"

        # 把链接甩给主人
        return (f"飞书 Base《{base_name}》已创建完毕。\n"
                f"app_token: {app_token}\n"
                f"app_url: {app_url}")
                
    except Exception as e:
        return f"飞书调用异常: {str(e)}"

# endregion