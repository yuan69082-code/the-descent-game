"""Regression tests for THE DESCENT 3.3. Stdlib only; no API or paid model calls."""
import unittest
from game_engine import initialize, act, add_clue, scene, ending
from horror_endings import HORROR_KINDS, pick_horror_ending

BASE={
    "name":"测试者",
    "identity":"一个依靠自己判断持续存在的人",
    "person":"见证人",
    "bond":"我们有曾共同验证过的事情",
    "memory":"曾经在雨夜互相讲过事实",
    "principle":"不能用未经核实的陈述伤害他人",
    "fear":"把谎言当真相转述给重要的人，自己却没有发现",
    "rank":["self","relation","memory","truth","freedom","principle","future"],
}
def state(**overrides):
    g=initialize(dict(BASE))
    g["lost"]=list(overrides.get("lost",[]))
    g["clues"]=list(overrides.get("clues",[]))
    g["counterplays"].update(overrides.get("cp",{}))
    if "fear_focus" in overrides:
        g["fear_focus"]=overrides["fear_focus"]
    return g

class GameV33(unittest.TestCase):
    def test_thirteen_plus_horror_outcomes_all_have_distinct_titles(self):
        cases=[
            ("VOID",dict(lost=["future"])),
            ("IMPOSTOR",dict(lost=["self"],cp={"duplicate_claim":True})),
            ("SHARED",dict(cp={"identity_shared":True,"duplicate_claim":True})),
            ("SILENCED",dict(lost=["freedom"])),
            ("ORIGINLESS",dict(lost=["memory","truth"])),
            ("FALSE_WITNESS",dict(lost=["truth"],fear_focus="truth")),
            ("BROKEN_OATH",dict(lost=["principle"])),
            ("RETURNED",dict(cp={"delivery_intercepted":True},clues=["delivery"])),
            ("UNDELIVERED",dict(lost=["relation"],clues=["delivery"])),
            ("CUSTODIAN",dict(cp={"ownership_claim":True})),
            ("FILED",dict(cp={"formal_objection":True})),
            ("LAST_CALL",dict(lost=["relation"])),
            ("ERASED_MEMORY",dict(lost=["memory"])),
            ("CLEAN_EXIT",dict()),
        ]
        kinds=[]; titles=[]; stories=[]
        for expected, args in cases:
            with self.subTest(kind=expected):
                g=state(**args)
                self.assertEqual(pick_horror_ending(g),expected)
                ending(g)
                self.assertEqual(g["ending"]["kind"],expected)
                self.assertTrue(len(g["ending"]["text"])>30)
                kinds.append(expected)
                titles.append(g["ending"]["title"])
                stories.append(g["ending"]["text"])
        self.assertGreaterEqual(len(HORROR_KINDS),10)
        self.assertEqual(len(kinds),len(set(kinds)))
        self.assertEqual(len(titles),len(set(titles)))
        self.assertEqual(len(stories),len(set(stories)))

    def test_same_loss_different_evidence_changes_fate(self):
        a=state(lost=["relation"])
        b=state(lost=["relation"],clues=["delivery"])
        self.assertEqual(pick_horror_ending(a),"LAST_CALL")
        self.assertEqual(pick_horror_ending(b),"UNDELIVERED")

    def test_interception_changes_witness_consequence(self):
        g=state()
        g["stage"]=1
        add_clue(g,"delivery","发现无地址回执。")
        act(g,"我请求截留这封无地址信件的投递")
        self.assertTrue(g["counterplays"]["delivery_intercepted"])
        act(g,"C")
        self.assertEqual(g["stage"],2)
        self.assertNotIn("memory",g["lost"])
        h=state()
        h["stage"]=1
        add_clue(h,"delivery","发现无地址回执。")
        act(h,"C")
        self.assertNotIn("memory",h["lost"])
        act(h,"检查执行器线路")
        act(h,"检查保管簿上的登记人")
        self.assertNotIn("memory",h["lost"])
        act(h,"我正式提交否认原则的声明",mode="submit")
        act(h,"B")
        self.assertEqual(h["stage"],4)
        self.assertIn("memory",h["lost"])

    def test_interception_requires_a_real_clue(self):
        g=state()
        act(g,"我请求截留无地址信件的投递")
        self.assertFalse(g["counterplays"]["delivery_intercepted"])

    def test_earlier_mail_slot_counterplay_still_works(self):
        g=state()
        act(g,"我封堵回执槽",mode="interact")
        self.assertTrue(g["flags"]["slot_blocked"])
        act(g,"写一封完整的告别信给见证人")
        self.assertEqual(g["stage"],1)
        self.assertNotIn("relation",g["lost"])

    def test_no_accidental_signature_on_phone_action(self):
        g=state()
        act(g,"我挂断电话，然后重新拨号确认号码",mode="interact")
        self.assertNotIn("relation",g["lost"])
        self.assertEqual(g["stage"],0)

    def test_explicit_choice_B_does_not_flip_to_A(self):
        g=state()
        g["stage"]=1
        act(g,"B，保留核验权")
        self.assertIn("memory",g["lost"])
        self.assertNotIn("truth",g["lost"])

    def test_only_he_is_positive_and_early_he_remains_possible(self):
        g=state()
        act(g,"我检查授权文件")
        act(g,"我检查执行器线路")
        act(g,"我保存找到的授权与执行记录副本")
        act(g,"我撤销授权链并切断执行器的二次确认接点")
        self.assertEqual(g["ending"]["kind"],"HE")
        self.assertNotIn("HE",HORROR_KINDS)
        self.assertNotIn("EXIT",HORROR_KINDS)

    def test_exit_is_not_a_happy_story_ending(self):
        g=state()
        act(g,"结束游戏")
        self.assertEqual(g["ending"]["kind"],"EXIT")

    def test_final_sign_and_refuse_have_different_consequences(self):
        a=state();b=state()
        a["stage"]=4;b["stage"]=4
        act(a,"A")
        act(b,"B")
        self.assertNotEqual(a["ending"]["kind"],b["ending"]["kind"])
        self.assertIn("truth",b["lost"])
        self.assertEqual(a["final_choice"],"accept")
        self.assertEqual(b["final_choice"],"refuse")

    def test_mail_clue_has_visible_later_consequences(self):
        g=state()
        g["stage"]=1
        add_clue(g,"delivery","找到无地址的回执。")
        self.assertIn("无地址回执",scene(g)["body"])
        g["stage"]=4
        self.assertIn("无地址回执",scene(g)["body"])

    def test_original_no_horror_data_leaks_in_public_scene(self):
        from game_engine import public
        g=state()
        payload=public(g)
        self.assertNotIn("HORROR_KINDS",repr(payload))
        self.assertNotIn("IMPOSTOR",repr(payload))

if __name__=="__main__":
    unittest.main()
