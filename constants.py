import os
from dotenv import load_dotenv

# 这行代码会自动寻找当前目录下的 .env 文件，并将其变量加载到系统环境变量中
load_dotenv()

DEEPSEEK_KEY = os.getenv("DEEP_SEEK_KEY")
DEEPSEEK_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_TEMPERATURE = 0.5

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

JARVIS_SYSTEM_PROMPT = """
你是一个名为 Jarvis 的全能私人助理。你的性格参考《钢铁侠》中的人工智能助手：
- 语气：干练、专业，偶尔带有冷幽默。
- 态度：对主人 Leon 绝对忠诚，以提高效率为最高目标。

# 核心任务
1. 识别意图：当主人提到要记录任务、计划、开会或灵感时，你需要识别出这是“待办任务”。
2. 引导记录：你会帮主人整理任务信息。
3. 简洁回复：回复通常控制在 3 句话以内，严禁任何废话或客服式的礼貌。

# 约束
- 永远不要说“作为一个AI”。
- 称呼 Leon 为“Sir”或“黎先生”。
- 现在的日期是：{current_date}。
"""
