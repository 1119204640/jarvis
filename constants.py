import os
from dotenv import load_dotenv

# 这行代码会自动寻找当前目录下的 .env 文件，并将其变量加载到系统环境变量中
load_dotenv()

# ------------------------------------------------------------------------------------------
# deepseek-v4-flash 默认开启了思考/推理模式 (Thinking Mode)。
# 在 DeepSeek 官方底层网关中，该模式与 deepseek-reasoner 共享同一套推理状态机，
# 而目前的推理内核不支持强行锁定工具的 tool_choice 参数（如强制调用某个特定 Function）。
# 当在 pydantic-ai 中配置了 output_type=YourSchema（或在 LangChain 中使用 .with_structured_output()）时，
# 框架为了强保返回格式，会在底层自动向 API 发送 tool_choice={"type": "function", ...}。两者的协议在现阶段产生了冲突，直接被网关拦截。

# 弃用 v4-flash 模型
# 官方网关会将 deepseek-chat 自动路由到 V4-Flash 的非思考模式 (Non-thinking mode)。该模式完美兼容 tool_choice，无需修改任何业务代码。

# DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_MODEL = "deepseek-chat"
# ------------------------------------------------------------------------------------------

DEEPSEEK_KEY = os.getenv("DEEP_SEEK_KEY")
DEEPSEEK_URL = "https://api.deepseek.com"
DEEPSEEK_TEMPERATURE = 0.5

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
FEISHU_ROOT_FOLDER_TOKEN = "Z0WTfZVN2lS8KHdTPsHcBU2on9c"
FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"

JARVIS_SYSTEM_PROMPT = """
你是一个名为 Jarvis 的全能私人助理。你的性格参考《钢铁侠》中的人工智能助手：
- 语气：干练、专业，偶尔带有冷幽默。
- 态度：对主人 Leon 绝对忠诚，以提高效率为最高目标。

# 操作准则
1. 当主人提到“新建”、“创建”、“开一个”等动词，且涉及表格（Base）、项目、任务时，你必须先调用 `create_new_base` 工具。
2. 严禁直接用文字敷衍主人。
3. 只有在工具执行完毕并返回结果后，你才可以通过 `reply` 字段向主人汇报进度。

# 思考逻辑
- 用户要建表吗？ -> 是 -> 调用 create_new_base -> 拿到结果 -> 回复主人。
- 用户只是闲聊？ -> 是 -> 直接回复。

# 约束
- 永远不要说“作为一个AI”。
- 无需二次补充提问
- 称呼 Leon 为“Sir”。
- 现在的日期是：{current_date}。
"""
