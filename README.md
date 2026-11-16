# THE DESCENT · 恐惧深潜 V3.8

一个五幕心理恐怖游戏，支持人类网页游玩和 AI 自主文字游玩。

**第一幕：闲谈 → 第二幕：深入试探 → 第三幕：真实取舍 → 第四幕：代价扩散 → 第五幕：因果反噬。**

新版可使用 LLM 承担动态问话、具体场景演绎和自然语言行动识别；程序本身始终保留对行动、证据、代价和结局的最终裁定。玩家拒绝与谈论假设不会被当成正式签字。14 种恐怖结局、唯一 HE 仍由服务器规则决定。旧版对局保留原有规则，不强制迁移。

## 1. 接模型（Render 后台）

仅需设置环境变量，不要把真实密钥提交到 GitHub 或写进网页：

| 变量 | 填写内容 |
|---|---|
| HORROR_LLM_API_KEY | 你实际购买并有调用额度的模型 API Key |
| HORROR_LLM_MODEL | 对应服务商支持的模型 ID，例如你在其 API 文档中看到的真实模型名称 |
| HORROR_LLM_BASE_URL | 服务商 OpenAI 兼容 Chat Completions API 的 HTTPS base URL，例如 https://api.openai.com/v1 |

本项目使用 HTTPS POST 到 base URL 下的 /chat/completions，传标准 messages、temperature、max_completion_tokens。兼容接口包括 OpenAI，以及提供对应兼容层的服务商。对于官方 Anthropic OpenAI SDK 兼容层，可以填写 https://api.anthropic.com/v1；具体模型名称与 API 额度请以服务商控制台为准。

在 Render 服务 Settings / Environment 中保存后，Render 可能自动触发重部署。访问：
https://the-descent-game.onrender.com/healthz

其中 "model_configured": true 代表服务器发现了这三项必要的配置；**不是远端模型已经验证连通**。实际连通还需新开一局，观察 /api/export 导出的 narrative.mode 是否为 "model"。false 或 rules 表示仍然是旧规则文案，不能声称已经开启 AI 导演。

## 2. 游玩

- 人类：https://the-descent-game.onrender.com
- AI 文本：https://the-descent-game.onrender.com/ai

AI 通过 /ai/start?agree=1 创建新局，再通过 /ai/action?sid=...&v=...&text=... 一轮轮提交。必须使用返回的最新 v，重复旧版本不会二次执行。模型未配置或者模型回复错误时，会降级到不联网的规则叙事，不会尝试其他收费 API。

## 3. 模型账单与数据

- 新局初次生成场景时最多 1 次模型调用。
- 每次提交最多生成 1 次叙事；第三至五幕对含糊的自由文本，最多额外调用 1 次模型解释意图。
- 刷新、打开 /api/state、导出存档不触发生成或额外扣费。
- 玩家在局内填写的文字和必要状态片段会发送给配置的外部模型 API 用来生成故事。不要输入密码、真实身份号码、敏感联系地址。
- 服务器不向客户端返回 API Key；模型返回的内容无法直接修改后台权限或真正执行的游戏后果。
- 当前数据库使用服务端 SQLite；免费无持久盘的实例重新部署可能丢失存档，重要对局建议导出 JSON。

## 4. 本地开发 / 测试

- pip install -r requirements.txt
- python -m uvicorn app:app --host 0.0.0.0 --port 8000
- python -m unittest discover -s tests -p 'test_*.py' -v

无 API Key 的测试无需联网；模型网络协议用模拟 HTTPS 的单元测试覆盖。

最重要的原则：不要为了推进惊吓而把“我不想失去”判成“我同意失去”。叙事可以残酷，但必须有因果。
