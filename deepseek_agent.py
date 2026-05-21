import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ModelMessage, UserPromptPart
from pydantic_ai.mcp import MCPServerStdio
import constants
from feishu_client import FeiShuClient
from utils import get_current_date_str
import logger

# 接 DeepSeek 模型
deepseek_model = OpenAIChatModel(
    model_name=constants.DEEPSEEK_MODEL,
    provider=OpenAIProvider(api_key=constants.DEEPSEEK_KEY, base_url=constants.DEEPSEEK_URL),
)

def _log_mcp_message(message: str):
    """捕获 lark-mcp 子进程的日志（含飞书 API 错误详情）"""
    logger.info(f"[MCP] {message}")

async def _on_mcp_tool_call(ctx, call_tool, tool_name, args):
    """拦截每次 MCP 工具调用，记录请求和结果"""
    logger.info(f"[MCP] 调用工具 {tool_name} | 参数: {args}")
    try:
        result = await call_tool(tool_name, args)
        logger.success(f"[MCP] {tool_name} 成功: {result}")
        return result
    except Exception as e:
        logger.error(f"[MCP] {tool_name} 失败: {e}")
        raise

# 创建飞书 MCP Server（stdio 传输，启动 npx 子进程）
mcp_server = MCPServerStdio(
    'npx',
    args=[
        '-y', '@larksuiteoapi/lark-mcp', 'mcp',
        '-a', constants.FEISHU_APP_ID,
        '-s', constants.FEISHU_APP_SECRET,
    ],
    env=os.environ,
    timeout=30,
    log_handler=_log_mcp_message,
    process_tool_call=_on_mcp_tool_call,
)

#  ------------------------------------------------------------------------------------------                                                                                                                          
#  实例化核心智能体
                                                                                                                                                                                                                     
#  注意：此处刻意不设置 output_type。                                                                                                                                                                                  
                                                                                                                                                                                                                     
#  当给 Agent 设置 output_type（如 JarvisResponseSchema）时，pydantic-ai 底层会自动生成                                                                                                                                
#  一个内部“输出工具”（kind='output'），与用户通过 @agent.tool 注册的函数工具一并发送给                                                                                                                                
#  模型。在 tool_choice='auto' 的情况下，模型看到输出工具是一个合法的“快捷出口”，可能直接                                                                                                                              
#  调用它返回一段文本结束对话，完全跳过真正需要执行的函数工具。                                                                                                                                  
                                                                                                                                                                                                                     
#  现象：工具注册正确、工具列表里也存在，但函数体永远不会被调用。                                                                                                                                                      
#  解决：去掉 output_type，让模型只剩下纯文本回复 + 函数工具两条路。系统提示词中要求                                                                                                                                   
#  “必须先调用工具”的指令就能真正约束模型行为。                                                                                                                                                                        
#  ------------------------------------------------------------------------------------------  

jarvis_agent = Agent(
    model=deepseek_model,
    system_prompt=constants.JARVIS_SYSTEM_PROMPT,
    deps_type=FeiShuClient,
    toolsets=[mcp_server],
    retries=3
)

# 动态系统提示词注入
# 这个装饰器会在每次 jarvis_agent.run() 触发前自动执行，把最新的时间塞给 AI
@jarvis_agent.system_prompt
def inject_dynamic_context(ctx: RunContext[FeiShuClient]) -> str:
    return f"\n【系统动态参数】\n当前北京时间是: {get_current_date_str()}"

# 会返回 AgentRunResult 对象
async def get_agent_run_result(user_text, client_instance, history=None):
    model_messages = _convert_history(history) if history else None
    resp_obj = await jarvis_agent.run(user_text, deps=client_instance, message_history=model_messages)
    return resp_obj

async def get_ai_reply(user_text, client_instance, history=None):
    result = await get_agent_run_result(user_text, client_instance, history)
    return result.output

def _convert_history(history: list[dict]) -> list[ModelMessage]:
    """将内存字典格式的历史记录转换为 pydantic-ai 的 ModelMessage 列表"""
    messages = []
    for msg in history:
        if msg["role"] == "user":
            part = UserPromptPart(content=msg["content"])
            messages.append(ModelRequest(parts=[part]))
        elif msg["role"] == "assistant":
            part = TextPart(content=msg["content"])
            messages.append(ModelResponse(parts=[part]))
    return messages

async def init_mcp():
    """在服务启动时连接 MCP Server，保持长连接"""
    try:
        await mcp_server.__aenter__()
        tools = await mcp_server.list_tools()
        logger.success(f"MCP 已连接，可用工具 {len(tools)} 个: {[t.name for t in tools]}")
    except Exception as e:
        logger.error(f"MCP 连接失败: {e}")

async def shutdown_mcp():
    """服务关闭时断开 MCP 连接"""
    try:
        await mcp_server.__aexit__(None, None, None)
        logger.info("MCP 连接已关闭")
    except Exception:
        pass