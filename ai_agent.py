from constants import DEEPSEEK_URL, DEEPSEEK_KEY, DEEPSEEK_MODEL, DEEPSEEK_TEMPERATURE
from openai import AsyncOpenAI

class Agent:
    def __init__(self):
        pass

    # 请求 DeepSeek 获取 AI 回复
    async def get_deepseek_response(system_content, user_content, temperature=None):
        client = AsyncOpenAI(
            api_key=DEEPSEEK_KEY,
            base_url=DEEPSEEK_URL
        )
        try:
            response = await client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content":system_content},
                    {"role": "user", "content":user_content},
                ],
                stream=False,
                temperature=temperature if temperature else DEEPSEEK_TEMPERATURE,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"DeepSeek 调用出错: {e}")
            return None