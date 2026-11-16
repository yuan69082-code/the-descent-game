# THE DESCENT · 恐惧深潜 V3.9

五幕心理恐怖游戏：闲谈 → 试探 → 失衡 → 剥夺 → 归零。人类和 AI 都可以自己玩。

## V3.9：模型只当后台策划，不和玩家直接对话

外部模型只拿到玩家已提交的原话、后台真实选择与损失、已有的历史伏笔。它给程序输出结构化计划卡：mode（下轮玩法）、focus（关注对象）、hook_id（可选择回收的旧线索，也可以为空）、question（仅第一、二幕允许的下一句问话）。模型不能写给玩家直接看的故事正文，不能决定签字、剥夺、恢复或改判结局。

游戏系统根据计划卡和后台事实，自己生成剧情及合法选项。规则引擎保存真正的授权、拒绝、证据、代价和结局；拒绝不等于同意，假设不等于签字。

## 灵活伏笔

第一幕谈到的喜好、关系、厌恶是可能被敌人利用的线索，绝不是玩家授权；第二幕假设可能暴露取舍倾向；第三、四幕实际交易、保护、拒绝、调查构成新的事件。

任何更早的线索都可能在第三、四或第五幕再出现。没有固定倒计时，也不要求每条都兑现。模型只能指定已有线索的 hook_id，系统核实它确实存在，玩家真实调查某条旧线索能改变后面一部分侵占压力。十四种恐怖结局与唯一 HE 保留，反制有效就不能被随意抹掉。

## 配置模型（Render Environment）

HORROR_LLM_API_KEY：模型服务的 API Key，仅存服务器环境变量中。
HORROR_LLM_MODEL：实际可调用的模型 ID。
HORROR_LLM_BASE_URL：该服务提供的 HTTPS OpenAI Chat Completions 兼容地址前缀。例如 https://api.openai.com/v1 。

访问 https://the-descent-game.onrender.com/healthz 可检查版本 3.9 与 model_configured，但变量存在不代表已调用成功。导出新局的 JSON 后，narrative.plan.from_model 会标识最后一轮是否接纳过有效的模型策划。没有 API Key 或接口报错时，自动采用规则后备策划；不自动换收费渠道。

## 游玩

人类入口：https://the-descent-game.onrender.com
AI 自主入口：https://the-descent-game.onrender.com/ai

AI 可用 /ai/start?agree=1 建局，通过 /ai/action?sid=...&v=...&text=... 提交。每次必须使用最新版本号 v。旧局保留原版本，体验新版要创建新对局。

## 成本和保存

首次进入最多请求 1 次后台计划，随后每轮最多请求 1 次计划；第三幕之后的含糊行动可能额外请求 1 次意图识别。刷新、重读、导出不触发新模型请求。不设置费用上限，也不增加费用展示。对外模型会看到必要的对话上下文，请勿在游戏里输入密码等秘密。

运行测试：python -m unittest discover -s tests -p 'test_*.py' -v
