# from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import constants
from feishu_api import FeiShuClient
from utils import get_current_date_str
from logger import log


# TODO:定义输出模型
# class JarvisResponseSchema(BaseModel):
#     reply: str = Field(description="发给主人的直接回复文本，保持干练和冷幽默")
#     thought: str = Field(description="内部思考过程，记录你决定调用哪个工具、或者为何不调用")

# 接 DeepSeek 模型
deepseek_model = OpenAIChatModel(
    model_name=constants.DEEPSEEK_MODEL,
    provider=OpenAIProvider(api_key=constants.DEEPSEEK_KEY, base_url=constants.DEEPSEEK_URL),
)

 # ------------------------------------------------------------------------------------------                                                                                                                          
 # 实例化核心智能体
 #                                                                                                                                                                                                                     
 # 注意：此处刻意不设置 output_type。                                                                                                                                                                                  
 #                                                                                                                                                                                                                     
 # 当给 Agent 设置 output_type（如 JarvisResponseSchema）时，pydantic-ai 底层会自动生成                                                                                                                                
 # 一个内部“输出工具”（kind='output'），与用户通过 @agent.tool 注册的函数工具一并发送给                                                                                                                                
 # 模型。在 tool_choice='auto' 的情况下，模型看到输出工具是一个合法的“快捷出口”，可能直接                                                                                                                              
 # 调用它返回一段文本结束对话，完全跳过真正需要执行的函数工具（如 create_new_base）。                                                                                                                                  
 #                                                                                                                                                                                                                     
 # 现象：工具注册正确、工具列表里也存在，但函数体永远不会被调用。                                                                                                                                                      
 # 解决：去掉 output_type，让模型只剩下纯文本回复 + 函数工具两条路。系统提示词中要求                                                                                                                                   
 # “必须先调用工具”的指令就能真正约束模型行为。                                                                                                                                                                        
 # ------------------------------------------------------------------------------------------  

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
    log(result.all_messages(), level="info")
    return result.output