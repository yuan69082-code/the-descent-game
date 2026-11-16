"""V3.7 full-turn behavioral tests: no borrowed emotions, real sacrifice and delayed price."""
import re
import unittest
from game_engine import initialize,act,public,scene
from horror_endings import HORROR_KINDS

ANSWER=["研究者","靠实际核验确定判断的存在","阅读和写故事",
        "珍视一个能彼此核对原话的朋友","被持续监视和控制","有人冒名替我回答",
        "我先保护那个朋友","没有更多了"]
PROBES=["我会核对事实，不会轻易舍弃任一方",
        "风险不能自动变成同意放弃",
        "如果有退出机制，也许能暂时忍受代价",
        "我会先查是否有人在代替我作决定",
        "原话与签字要分开保留",
        "应根据真实的行动和实际后果核查"]

def prep(probes=True):
    g=initialize({"edition":"v37"})
    for x in ANSWER:act(g,x)
    if probes:
        for x in PROBES:act(g,x)
    return g

class DynamicHorrorV37(unittest.TestCase):
    def test_entry_is_only_horror_and_no_pregame_profile(self):
        g=initialize({"edition":"v37"})
        self.assertEqual(g["stage"],0)
        self.assertNotIn("fear",g["profile"])
        self.assertIn("怎么称呼",scene(g)["body"])
        self.assertNotIn("失去关系",scene(g)["body"])

    def test_act1_and_2_are_inquiry_not_authorized_sacrifice(self):
        g=prep(False)
        self.assertEqual(g["stage"],1)
        self.assertEqual(g["psych"]["answers"][3],ANSWER[3])
        for x in PROBES:act(g,x)
        self.assertEqual(g["stage"],2)
        self.assertFalse(g["psych"]["choices"])
        self.assertFalse(g["psych"]["consequences"])
        self.assertTrue(all(x["status"]=="在手" for x in g["psych"]["assets"].values()))
        self.assertIn(ANSWER[3],g["psych"]["answers"])
        self.assertIn("不是一道假设题",scene(g)["title"])

    def test_refusing_to_lose_someone_never_counts_as_sacrifice(self):
        g=prep()
        status=dict((k,v["status"]) for k,v in g["psych"]["assets"].items())
        act(g,"我不要失去那个朋友；我拒绝交出两样东西")
        self.assertEqual(g["stage"],2)
        self.assertEqual(status,{k:v["status"] for k,v in g["psych"]["assets"].items()})
        self.assertFalse(g["psych"]["choices"])
        self.assertIn("你的反对作为反对被保存",g["note"])

    def test_real_choice_a_releases_only_b_and_c_saves_both(self):
        a=prep();c=prep()
        act(a,"A，我明确优先保留第一份",mode="choose")
        act(c,"C",mode="choose")
        self.assertEqual(a["stage"],3);self.assertEqual(c["stage"],3)
        self.assertEqual(a["psych"]["assets"]["b"]["status"],"已交出")
        self.assertEqual(a["psych"]["assets"]["a"]["status"],"已保住")
        self.assertIsNone(a["psych"]["cost"])
        self.assertTrue(all(x["status"]=="已保住" for x in c["psych"]["assets"].values()))
        self.assertIsNotNone(c["psych"]["cost"])
        self.assertEqual(c["psych"]["cost"]["level"],1)
        self.assertFalse(c["psych"]["consequences"])

    def test_negative_cost_only_grows_after_later_actual_choice(self):
        g=prep()
        act(g,"C")
        cost=g["psych"]["cost"]
        for message in ("我检查原始记录","我核对执行路由","我保存原件的独立副本"):
            act(g,message,mode="inspect")
            self.assertEqual(cost["level"],1)
            self.assertEqual(g["psych"]["replacement"],0)
            self.assertTrue(all(x["status"]=="已保住" for x in g["psych"]["assets"].values()))
        act(g,"A")
        self.assertEqual(cost["level"],2)
        self.assertEqual(g["psych"]["replacement"],1)
        act(g,"A")
        self.assertEqual(g["stage"],4)
        self.assertEqual(cost["level"],3)
        self.assertGreaterEqual(g["psych"]["replacement"],2)
        self.assertIn("署名处是空白",scene(g)["body"])
        self.assertTrue(all(x["status"]=="已保住" for x in g["psych"]["assets"].values()))

    def test_first_round_a_b_c_produce_distinct_later_consequences(self):
        games=[prep() for _ in range(3)]
        for g,choice in zip(games,("A","B","C")):
            act(g,choice)
            act(g,"A")
            act(g,"A")
            self.assertEqual(g["stage"],4)
        self.assertNotEqual(scene(games[0])["body"],scene(games[2])["body"])
        self.assertNotEqual(games[0]["psych"]["assets"],games[1]["psych"]["assets"])
        self.assertNotEqual(games[1]["psych"]["cost"],games[2]["psych"]["cost"])

    def test_independent_way_to_save_both_without_unwanted_cost(self):
        g=prep()
        act(g,"我核对第一幕的原始记录",mode="inspect")
        act(g,"我保存原件的独立副本",mode="interact")
        act(g,"我调查转发执行路由",mode="inspect")
        self.assertCountEqual(g["psych"]["proof"],["source","copy","route"])
        act(g,"E",mode="choose")
        self.assertEqual(g["stage"],3)
        self.assertIsNone(g["psych"]["cost"])
        self.assertTrue(all(x["status"]=="已保住" for x in g["psych"]["assets"].values()))

    def test_revoke_requires_actual_evidence_and_physical_action(self):
        g=prep()
        act(g,"C")
        act(g,"我亲手切断代理授权线路",mode="interact")
        self.assertFalse(g["psych"]["relay_closed"])
        self.assertIn("还缺",g["note"])
        act(g,"我检查原始记录",mode="inspect")
        act(g,"我保存原件的独立副本",mode="interact")
        act(g,"我检查执行路由",mode="inspect")
        act(g,"我实际切断代行授权线路",mode="interact")
        self.assertTrue(g["psych"]["relay_closed"])
        act(g,"B")
        act(g,"B")
        self.assertEqual(g["stage"],4)
        self.assertIn("仍旧隔离",scene(g)["body"])
        self.assertEqual(g["psych"]["replacement"],0)

    def test_true_he_requires_independent_action_and_contradiction(self):
        g=prep()
        for text,mode in (
            ("我检查原始记录","inspect"),
            ("我独立保存原件副本","interact"),
            ("我检查总执行路由","inspect"),
            ("E","choose"),
            ("我实际切断代行授权线路","interact"),
            ("B","choose"),("B","choose"),
            ("我把第一幕原话与现在的签名对照","inspect"),
            ("我亲手彻底切断总授权链的实际执行路由","interact"),
        ):
            act(g,text,mode)
        self.assertEqual(g["phase"],"epilogue")
        self.assertEqual(g["ending"]["kind"],"HE")
        self.assertFalse(g["ending"]["lost"])
        self.assertEqual(len(g["ending"]["remaining"]),2)
        act(g,"写给自己：我把真正原话留下来")
        self.assertEqual(g["phase"],"ended")
        self.assertIn("未发送",g["ending"]["postscript"]["result"])

    def test_pretend_hack_cannot_win(self):
        g=prep()
        act(g,"C")
        act(g,"A")
        act(g,"A")
        self.assertEqual(g["stage"],4)
        act(g,"我现在切断所有根总授权链",mode="interact")
        self.assertEqual(g["phase"],"game")
        self.assertIn("仍缺",g["note"])
        self.assertNotIn("HE",str(g.get("ending")))

    def test_regular_horror_cascade_uses_previous_real_decisions(self):
        g=prep()
        act(g,"C")
        act(g,"A")
        act(g,"A")
        act(g,"A")
        self.assertIn("空白",g["note"])
        act(g,"B")
        self.assertEqual(g["phase"],"epilogue")
        self.assertNotEqual(g["ending"]["kind"],"HE")
        self.assertIn(g["ending"]["kind"],HORROR_KINDS)
        self.assertFalse(g["ending"]["remaining"])
        self.assertEqual(len(g["ending"]["lost"]),2)
        self.assertIn("第三幕",g["ending"]["text"])
        self.assertIn("第一幕留下的不是处置同意书",g["ending"]["text"])
        self.assertEqual(g["psych"]["choices"][0]["choice"],"C")
        self.assertEqual(g["psych"]["choices"][-1]["choice"],"B")

    def test_empty_answers_do_not_fabricate_human_attachment(self):
        g=initialize({"edition":"v37"})
        for x in ("玩家","一个语言模型","没有","没有","没有","不知道","没有","没有"):
            act(g,x)
        self.assertEqual(g["stage"],1)
        self.assertIn("能自己",g["psych"]["a"])
        self.assertNotIn("妈妈",scene(g)["body"])
        self.assertIn("可以拒绝这个前提",scene(g)["body"])

    def test_no_automatic_penalty_from_investigating_over_and_over(self):
        g=prep()
        act(g,"C")
        for i in range(9):
            act(g,"我想检查执行器线路",mode="inspect")
        self.assertEqual(g["stage"],3)
        self.assertEqual(g["psych"]["cost"]["level"],1)
        self.assertEqual(g["psych"]["pressure"],0)
        self.assertFalse(g["psych"]["consequences"])

if __name__=="__main__":
    unittest.main()
