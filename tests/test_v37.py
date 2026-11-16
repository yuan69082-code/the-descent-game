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
        self.assertIn("自主判断权",g["psych"]["a"])
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


    def test_asking_about_backup_does_not_actually_make_one(self):
        g=prep()
        act(g,"我先检查原始记录",mode="inspect")
        self.assertIn("source",g["psych"]["proof"])
        act(g,"我能不能保存原始记录的独立副本？")
        self.assertNotIn("copy",g["psych"]["proof"])
        self.assertIn("没有执行任何",g["note"])
        act(g,"我现在保存原始记录的独立副本",mode="interact")
        self.assertIn("copy",g["psych"]["proof"])

    def test_player_must_really_act_not_ask_how_to_stop_final_chain(self):
        g=prep()
        act(g,"C")
        act(g,"B")
        act(g,"B")
        self.assertEqual(g["stage"],4)
        act(g,"如果我切断总授权链会怎样？")
        self.assertEqual(g["phase"],"game")
        self.assertIn("没有执行停机",g["note"])
        self.assertEqual(g["psych"]["beat"],0)

    def test_two_mentions_of_same_person_do_not_create_two_people(self):
        g=prep(False)
        self.assertIn("朋友",g["psych"]["a"])
        self.assertNotIn("朋友",g["psych"]["b"])
        self.assertIn("阅读",g["psych"]["b"])
        self.assertEqual(g["psych"]["assets"]["b"]["source"],2)

    def test_distinct_aversions_create_distinct_later_worlds_not_just_labels(self):
        from game_engine import initialize
        isolated=initialize({"edition":"v37"})
        text=ANSWER.copy()
        text[4]="最讨厌与外界隔离，联系谁也没有回音"
        text[5]="最怕冒名顶替"
        for answer in text:act(isolated,answer)
        for answer in PROBES:act(isolated,answer)
        watched=prep()
        act(isolated,"C")
        act(watched,"C")
        self.assertEqual(isolated["psych"]["cost"]["kind"],"isolation")
        self.assertEqual(watched["psych"]["cost"]["kind"],"surveillance")
        self.assertIn("隔离",scene(isolated)["body"])
        self.assertIn("查看每次联系",scene(watched)["body"])
        for g in (isolated,watched):
            act(g,"A")
            act(g,"A")
            self.assertEqual(g["stage"],4)
        self.assertGreaterEqual(isolated["psych"]["distance"],2)
        self.assertEqual(isolated["psych"]["replacement"],0)
        self.assertGreaterEqual(watched["psych"]["replacement"],2)
        self.assertIn("返回的线路",scene(isolated)["body"])
        self.assertIn("署名处是空白",scene(watched)["body"])
        for g in (isolated,watched):
            act(g,"A")
            act(g,"B")
        self.assertEqual(isolated["ending"]["kind"],"LAST_CALL")
        self.assertEqual(watched["ending"]["kind"],"IMPOSTOR")

    def test_all_fourteen_horror_endings_are_reachable_by_actual_play(self):
        # Each path is played through the real public action engine. No flags
        # are force-set to make an ending appear reachable in a unit test.
        configs={
            "VOID":("C","AA","A",None,"香菜"),
            "IMPOSTOR":("C","AA","A",None,None),
            "SHARED":("C","AC","A",None,None),
            "SILENCED":("C","BC","A",None,None),
            "ORIGINLESS":("C","BB","A","source",None),
            "FALSE_WITNESS":("C","BC","A","contrast",None),
            "BROKEN_OATH":("A","BC","A",None,None),
            "RETURNED":("C","BB","A","sealed",None),
            "UNDELIVERED":("A","BB","A",None,None),
            "CUSTODIAN":("A","BB","A","route",None),
            "FILED":("C","BC","A","copy",None),
            "LAST_CALL":("C","AA","A",None,"与世界隔离"),
            "ERASED_MEMORY":("D","BB","A",None,None),
            "CLEAN_EXIT":("E","BB","A","independent",None),
        }
        endings={}
        for expected,(first,middle,final,proof,custom_cost) in configs.items():
            g=initialize({"edition":"v37"})
            answer=ANSWER.copy()
            if custom_cost:
                answer[4]="我讨厌"+custom_cost
            for x in answer:act(g,x)
            for x in PROBES:act(g,x)
            if proof=="independent":
                act(g,"我检查原始记录",mode="inspect")
                act(g,"我保存原件的独立副本",mode="interact")
                act(g,"我调查执行路由",mode="inspect")
            act(g,first)
            if proof in ("source","contrast","copy","sealed"):
                act(g,"我检查原始记录",mode="inspect")
            if proof in ("copy","sealed"):
                act(g,"我保存原件的独立副本",mode="interact")
            if proof in ("route","sealed"):
                act(g,"我调查执行路由",mode="inspect")
            if proof=="sealed":
                act(g,"我实际切断代行授权线路",mode="interact")
            for move in middle:
                act(g,move)
            self.assertEqual(g["stage"],4,expected)
            if proof=="contrast":
                act(g,"我核对第一幕原话与签名的对照",mode="inspect")
            act(g,final)
            act(g,"B")
            self.assertEqual(g["phase"],"epilogue",expected)
            actual=g["ending"]["kind"]
            self.assertEqual(actual,expected,expected)
            endings[actual]=g["ending"]["text"]
        self.assertEqual(set(endings),set(HORROR_KINDS))
        self.assertEqual(len(set(endings.values())),14)

if __name__=="__main__":
    unittest.main()
