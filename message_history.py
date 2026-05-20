"""
简单的内存字典存储用户消息历史。
Key: chat_id (飞书会话ID，一对一或群聊)
Value: list[dict] 格式为 OpenAI 标准 messages: [{"role": "user"/"assistant", "content": "..."}, ...]
"""

MAX_HISTORY = 20  # 每个会话最多保留多少轮（一轮 = user + assistant 各一条）

_history: dict[str, list[dict]] = {}


def get_history(chat_id: str) -> list[dict]:
    """返回该会话的完整历史记录（浅拷贝，调用方可安全追加）。"""
    return list(_history.get(chat_id, []))


def append(chat_id: str, role: str, content: str) -> None:
    """向该会话的历史记录追加一条消息，超出上限时裁剪最早的消息。"""
    if chat_id not in _history:
        _history[chat_id] = []
    _history[chat_id].append({"role": role, "content": content})
    # 保持最近 N 轮（一轮 = user + assistant）
    if len(_history[chat_id]) > MAX_HISTORY * 2:
        _history[chat_id] = _history[chat_id][-(MAX_HISTORY * 2):]
