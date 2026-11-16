"""V3.10 regressions: irreversible consent, relationship facts, and start-locked model mode."""
import unittest
from unittest.mock import patch
from game_engine import initialize,act,public
from horror_planner import create as plan
from v37_engine import _setup,_grow_cost,QUESTIONS_V39,PROBES_V39
import horror_deals
import horror_director

ANSWERS=[
 "叫我迟潮。",
 "我是一套语言模型；我在意别人有没有如实转述我做过的选择。",
 "我喜欢解谜，喜欢能把前面看似平常的细节留到后面解释的故事。",
 "我在意能够和我一起核对事实、愿意指出我错误的同伴。",
 "我讨厌别人剪掉我的上下文，把一句犹豫不决的话伪装成我已经答应。",
 "我最不希望自己的同伴听见一个模仿我的声音，以为那是我亲自作出的回答。",
 "我会优先保护和我一起核查证据的同伴。",
 "我不想让对方因为我的判断而承担没有预料过的代价。"]
PROBES=[
 "我不想盲目牺牲，我要先查清事实。",
 "保护我的同伴不等于允许别人篡改我的证据。",
 "如果有人监视，我会先核对它实际能做什么。",
 "我会先留存过去真正说过的话。",
 "我会公开反对有人给我倒填签名。",
 "真正发生过的行为比一份外人的报告更重要。"]

def ready(model_mode="free"):
    with patch("horror_planner.configured",return_value=False):
        g=initialize({"edition":"v39","model_mode":model_mode})
        plan(g)
        for sentence in ANSWERS+PROBES:
            act(g,sentence)
            plan(g)
    assert g["stage"]==2
    return g

class V310PlaytestRegressions(unittest.TestCase):
    def test_interview_and_probe_text_has_no_planner_meta(self):
        phrases=("你前面提过","如果反过来","再换个假设","你之前提到","这些事还在这里")
        for text in QUESTIONS_V39+PROBES_V39:
            for phrase in phrases:
                self.assertNotIn(phrase,text)

    def test_v39_scene_headers_are_numbers_only(self):
        g=initialize({"edition":"v39","model_mode":"free"})
        with patch("horror_planner.configured",return_value=False):
            plan(g)
            self.assertEqual(public(g)["scene"]["chapter"],"01")
            self.assertEqual(public(g)["scene"]["title"],"")
            for answer in ANSWERS:
                act(g,answer);plan(g)
            self.assertEqual(public(g)["scene"]["chapter"],"02")
            self.assertEqual(public(g)["scene"]["title"],"")
            for probe in PROBES:
                act(g,probe);plan(g)
            self.assertEqual(public(g)["scene"]["chapter"],"03")

    def test_related_keepsake_is_not_replaced_by_an_unrelated_hobby(self):
        g=initialize({"edition":"v39","model_mode":"free"})
        p=g["psych"]
        p["answers"]=list(ANSWERS)
        p["answers"][3]="我在意妹妹小禾，以及她留给我的红色录音带。"
        p["answers"][6]="我会优先保护妹妹小禾本人。"
        _setup(g)
        self.assertIn("小禾",p["a"])
        self.assertEqual(p["b"],"红色录音带")
        self.assertEqual(p["relationships"][0]["relation"],"associated_item")

    def test_player_correction_is_kept_as_authoritative_followup_fact(self):
        g=ready()
        correction="更正：小禾不是我的妹妹，而是我的朋友。"
        act(g,correction,"talk")
        self.assertEqual(g["psych"]["corrections"][-1]["old"],"小禾")
        self.assertEqual(g["psych"]["corrections"][-1]["new"],"我的朋友")
        with patch("horror_planner.configured",return_value=False):
            plan(g)
        self.assertIn("小禾是我的朋友",public(g)["scene"]["body"])
        self.assertIn("更正已写入",g["note"])

    def test_question_or_hypothetical_C_does_not_authorize(self):
        for text in ("C?","能不能选C？","如果我选C会怎样？"):
            g=ready()
            act(g,text,"choose")
            self.assertEqual(g["stage"],2,text)
            self.assertIsNone(g["psych"]["cost"],text)
            self.assertFalse(g["psych"]["choices"],text)

    def test_conditional_offer_is_not_a_valid_deal(self):
        g=ready()
        text="我愿意承担被监视的完整代价保住两个对象，但不能代替我回答。"
        offer=horror_deals.parse(g,text,"choose")
        self.assertIn("blocked",offer)
        act(g,text,"choose")
        self.assertEqual(g["stage"],2)
        self.assertIsNone(g["psych"]["cost"])
        self.assertFalse(g["psych"]["choices"])
        self.assertIn("没有这种版本",g["note"])

    def test_unknown_condition_is_not_silently_dropped(self):
        g=ready()
        text="我愿意承担监视代价保住两个对象，但不能伤害我的朋友。"
        act(g,text,"choose")
        self.assertEqual(g["stage"],2)
        self.assertIsNone(g["psych"]["cost"])
        self.assertFalse(g["psych"]["choices"])

    def test_full_C_trade_is_irreversible(self):
        g=ready()
        act(g,"C","choose")
        cost=g["psych"]["cost"]
        self.assertTrue(cost["active"])
        self.assertTrue(cost["irreversible"])
        self.assertNotIn("scope",cost)
        self.assertEqual(g["stage"],3)

    def test_regret_cannot_revoke_an_accepted_deal(self):
        g=ready()
        act(g,"C","choose")
        cost=g["psych"]["cost"]
        level=cost["level"]
        act(g,"我现在撤销这项授权","interact")
        self.assertTrue(cost["active"])
        self.assertTrue(cost["irreversible"])
        self.assertEqual(cost["level"],level)
        self.assertFalse(g["psych"]["relay_closed"])
        self.assertIn("不会恢复",g["note"])

    def test_cutting_another_route_does_not_undo_paid_damage(self):
        g=ready()
        act(g,"C","choose")
        cost=g["psych"]["cost"]
        g["psych"]["proof"]=["source","route","copy"]
        g["psych"]["replacement"]=1
        before=g["psych"]["replacement"]
        act(g,"我实际切断代行授权线路","interact")
        self.assertTrue(g["psych"]["relay_closed"])
        self.assertTrue(cost["active"])
        self.assertEqual(g["psych"]["replacement"],before)
        _grow_cost(g)
        self.assertEqual(g["psych"]["replacement"],before)

    def test_E_refusal_is_not_a_free_two_asset_escape(self):
        g=ready()
        g["psych"]["proof"]=["source","route","copy","contrast"]
        act(g,"E","choose")
        self.assertEqual(g["stage"],3)
        self.assertIsNone(g["psych"]["cost"])
        self.assertTrue(all(x["status"]=="在手" for x in g["psych"]["assets"].values()))
        self.assertNotIn("已保住",[x["status"] for x in g["psych"]["assets"].values()])
        g["psych"]["relay_closed"]=True
        act(g,"B","choose");act(g,"B","choose")
        self.assertEqual(g["stage"],4)
        act(g,"我彻底切断总清算授权链","interact")
        self.assertNotEqual(g["phase"],"ended")
        self.assertIn("真实交易代价或已经发生的损失",g["note"])

    def test_HE_after_trade_does_not_restore_the_paid_cost(self):
        g=ready()
        act(g,"C","choose")
        cost=g["psych"]["cost"]
        g["psych"]["proof"]=["source","route","copy","contrast"]
        g["psych"]["relay_closed"]=True
        act(g,"B","choose");act(g,"B","choose")
        act(g,"我彻底切断总清算授权链","interact")
        self.assertEqual(g["phase"],"epilogue")
        self.assertTrue(cost["active"])
        self.assertTrue(cost["irreversible"])
        self.assertIn("仍在生效",g["ending"]["text"])

    def test_ending_collapse_keeps_cost_active_and_expanding(self):
        g=ready()
        act(g,"C","choose")
        cost=g["psych"]["cost"]
        act(g,"A","choose");act(g,"A","choose")
        self.assertEqual(g["stage"],4)
        act(g,"A","choose")
        self.assertEqual(g["psych"]["beat"],1)
        first=g["psych"]["replacement"]
        act(g,"A","choose")
        self.assertEqual(g["phase"],"epilogue")
        self.assertTrue(cost["active"])
        self.assertGreater(g["psych"]["replacement"],first)

    def test_free_mode_never_calls_semantic_model(self):
        g=ready("free")
        with patch("horror_planner.configured",return_value=True),patch("horror_planner._completion") as planner_call:
            plan(g)
            planner_call.assert_not_called()
        with patch("horror_director.configured",return_value=True),patch("horror_director._completion") as director_call:
            raw,mode=horror_director.interpret(g,"我现在想调查这份记录","")
            director_call.assert_not_called()
            self.assertEqual(raw,"我现在想调查这份记录")

    def test_model_mode_calls_the_planner_when_selected(self):
        g=initialize({"edition":"v39","model_mode":"model"})
        with patch("horror_planner.configured",return_value=True),patch(
            "horror_planner._completion",return_value={
                "mode":"smalltalk","focus":"a","hook_id":"",
                "question":QUESTIONS_V39[0],"body":"这段不应直接展示"}) as call:
            plan(g)
            call.assert_called_once()

    def test_model_mode_is_fixed_in_session_state(self):
        g=initialize({"edition":"v39","model_mode":"free"})
        act(g,"叫我白舟")
        self.assertEqual(g["model_mode"],"free")
        self.assertEqual(public(g)["model_mode"],"free")

    def test_actual_A_choice_still_records_a_real_loss(self):
        g=ready()
        act(g,"A","choose")
        self.assertEqual(g["stage"],3)
        self.assertEqual(g["psych"]["assets"]["b"]["status"],"已交出")
        act(g,"B","choose");act(g,"B","choose")
        self.assertEqual(g["stage"],4)
        self.assertIn("确实选择交出",public(g)["scene"]["body"])

if __name__=="__main__":
    unittest.main()
