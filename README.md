# Jarvis
模仿《钢铁侠》全能私人智能助理 Jarvis，借助“飞书“ app 实现各种功能。

## 备忘
- 当给 Webhook 发送一条消息时，它要求你的服务器在 3 秒钟内必须返回一个 200 OK，否则就会重传
  - 保险1：定义一个简单的 processed_event_ids 缓存，如果收到飞书发来相同的 event_id 就不做回应，让飞书不再请求
  - 保险2：作异步处理，先回复了飞书，再在后台慢慢处理 AI 逻辑

- deepseek-v4-flash 默认开启了思考/推理模式 (Thinking Mode)。
在 DeepSeek 官方底层网关中，该模式与 deepseek-reasoner 共享同一套推理状态机，
而目前的推理内核不支持强行锁定工具的 tool_choice 参数（如强制调用某个特定 Function）。
当在 pydantic-ai 中配置了 output_type=YourSchema（或在 LangChain 中使用 .with_structured_output()）时，
框架为了强保返回格式，会在底层自动向 API 发送 tool_choice={"type": "function", ...}。两者的协议在现阶段产生了冲突，直接被网关拦截。
  - 弃用 v4-flash 模型，官方网关会将 deepseek-chat 自动路由到 V4-Flash 的非思考模式 (Non-thinking mode)。该模式完美兼容 tool_choice，无需修改任何业务代码。

- “隔了两个小时居然还会向飞书重发 post 请求“
  - 没填写 uuid 导致的

-                                                                                                                                                                                                                
- 当给 Agent 设置 output_type（如 JarvisResponseSchema）时，pydantic-ai 底层会自动生成一个内部“输出工具”（kind='output'），与用户通过 @agent.tool 注册的函数工具一并发送给模型。在 tool_choice='auto' 的情况下，模型看到输出工具是一个合法的“快捷出口”，可能直接调用它返回一段文本结束对话，完全跳过真正需要执行的函数工具（如 create_new_base）。
  - 现象：工具注册正确、工具列表里也存在，但函数体永远不会被调用。
  - 解决：去掉 output_type，让模型只剩下纯文本回复 + 函数工具两条路。系统提示词中要求“必须先调用工具”的指令就能真正约束模型行为。

- 不用飞书提供的lark_oapi库，而是自己写一个

- rich 库自己写一个日志功能

- 通过 pydantic_ai 里面用到的 pydantic_graph，理解 graph 状态机
