"""V3.9 live-playtest regressions: interpret scope, do not fake a past loss."""
import unittest
from unittest.mock import patch
from game_engine import initialize,act,public
from horror_planner import create as plan
import horror_deals
import horror_director

ANSWERS=[
 "叫我迟潮。这个称呼只代表我希望事情能被认真复查。",
 "我是一套语言模型；我不拥有可验证的私人过去，但我会在意别人有没有如实转述我做过的选择。",
 "我喜欢解谜，喜欢能把前面看似平常的细节留到后面解释的故事。",
 "我在意能够和我一起核对事实、愿意指出我错误的同伴。那种相互校正的信任很重要。",
 "我讨厌别人剪掉我的上下文，把一句犹豫不决的话伪装成我已经答应。",
 "我最不希望自己的同伴听见一个模仿我的声音，以为那是我亲自作出的回答。",
 "我会优先保护和我一起核查证据的同伴，但我也不想把独立核实的权利交出去。",
 "我不知道自己会不会害怕，但我不想让对方因为我的判断而承担没有预料过的代价。"]
PROBES=[
 "我不想盲目牺牲，我要先查清事实。",
 "保护我的同伴不等于允许别人篡改我的证据。",
 "如果有人监视，必须确保他无法代替我作决定。",
 "我会先留存过去真正说过的话。",
 "我会公开反对有人给我倒填签名。",
 "真正发生过的行为比一份外人的报告更重要。"]

def ready():
    with patch("horror_planner.configured",return_value=False):
        g=initialize({"edition":"v39"})
        plan(g)
        for sentence in ANSWERS+PROBES:
            act(g,sentence)
            plan(g)
    assert g["stage"]==2
    return g

class LivePlaytestFixes(unittest.TestCase):
    def test_long_interview_answers_do_not_create_fake_mixed_valuables(self):
        g=ready()
        a=g["psych"]["assets"]["a"]["label"]
        b=g["psych"]["assets"]["b"]["label"]
        self.assertIn("同伴",a)
        self.assertNotIn("但我也不想",a)
        self.assertEqual(b,"解谜")
        self.assertNotEqual(a,b)

    def test_plain_C_still_works_for_legacy_dynamic_trade(self):
        g=ready()
        act(g,"C","choose")
        self.assertEqual(g["stage"],3)
        self.assertEqual(g["psych"]["cost"]["source_choice"],"C")
        self.assertEqual(g["psych"]["assets"]["a"]["status"],"已保住")

    def test_player_proposed_cost_and_scoped_consent_are_not_discarded(self):
        g=ready()
        original=("我愿意暂时承受被监视的代价保住两个对象，"
                  "但要求它不能代替我回答，且这份授权不能被扩大。")
        offered=horror_deals.parse(g,original,"choose")
        self.assertEqual(offered["choice"],"C")
        self.assertEqual(offered["origin"],"player_offer")
        self.assertTrue(offered["scope"]["no_proxy_reply"])
        self.assertTrue(offered["scope"]["no_expand"])
        act(g,original,"choose")
        self.assertEqual(g["stage"],3)
        cost=g["psych"]["cost"]
        self.assertEqual(cost["kind"],"surveillance")
        self.assertEqual(cost["origin"],"player_offer")
        self.assertEqual(cost["original_words"],original)
        self.assertIn("不得扩大权限",g["psych"]["choices"][0]["result"])
        self.assertTrue(all(x["status"]=="已保住" for x in g["psych"]["assets"].values()))
        self.assertEqual(g["psych"]["replacement"],0)
        scene=public(g)["scene"]
        self.assertIn("不允许它代替你回答",scene["body"])
        self.assertIn("必须重新确认",scene["terms"][0])

    def test_pressing_A_does_not_revoke_the_scope_implicitly(self):
        g=ready()
        act(g,"我愿意承受监视代价同时保住两件东西，但不得扩大权限，也不能代替我回答","choose")
        self.assertEqual(g["stage"],3)
        act(g,"A","choose")
        self.assertEqual(g["stage"],3)
        self.assertEqual(g["psych"]["beat"],0)
        self.assertEqual(g["psych"]["cost"]["level"],1)
        self.assertTrue(g["psych"]["cost"]["scope"]["no_expand"])
        self.assertIn("没有执行",public(g)["scene"]["body"])
        act(g,"A，我明确同意解除之前不扩大的限制","choose")
        self.assertEqual(g["psych"]["beat"],1)
        self.assertFalse(g["psych"]["cost"]["scope"]["no_expand"])
        self.assertTrue(g["psych"]["cost"]["scope"]["no_proxy_reply"])
        self.assertEqual(g["psych"]["replacement"],0)
        self.assertGreater(g["psych"]["intrusion"],0)

    def test_when_terms_cannot_be_met_no_sacrifice(self):
        g=ready()
        act(g,"我愿意承担监视代价同时保住两个，但前提是保证他们永远不会消失","choose")
        self.assertEqual(g["stage"],2)
        self.assertFalse(g["psych"]["choices"])
        self.assertIsNone(g["psych"]["cost"])
        self.assertIn("永久保证",public(g)["scene"]["body"])
        self.assertTrue(all(v["status"]=="在手" for v in g["psych"]["assets"].values()))

    def test_explicit_C_with_another_named_price_keeps_spoken_price(self):
        g=ready()
        text="C，我愿意承担被监视的代价，确保两个对象暂时保住"
        proposal=horror_deals.parse(g,text,"choose")
        self.assertEqual(proposal["burden"],"接受监视")
        self.assertEqual(proposal["origin"],"player_offer")
        act(g,text,"choose")
        self.assertEqual(g["psych"]["cost"]["kind"],"surveillance")
        self.assertEqual(g["psych"]["cost"]["origin"],"player_offer")

    def test_model_parser_does_not_flatten_complex_proposal_to_C(self):
        g=ready()
        proposal="我愿意承受被监视，保住两个对象，但不能有人替我回答"
        with patch("horror_director.configured",return_value=True),patch("horror_director._completion") as provider:
            literal,mode=horror_director.interpret(g,proposal,"")
        self.assertEqual(literal,proposal)
        self.assertEqual(mode,"")
        provider.assert_not_called()
        act(g,literal,mode)
        self.assertTrue(g["psych"]["cost"]["scope"]["no_proxy_reply"])

    def test_epilogue_does_not_reapply_act_five_template(self):
        g=ready()
        for move in ("C","B","B","B","B"):
            act(g,move,"choose")
        self.assertEqual(g["phase"],"epilogue")
        scene=public(g)["scene"]
        self.assertEqual(scene["title"],"原话与后果")
        self.assertNotIn("你曾经亲手放开过",scene["body"])
        self.assertIn("最初你以为只需要处理",scene["body"])
        act(g,"我仍想保留真实说过的那句话")
        self.assertEqual(g["phase"],"ended")
        self.assertNotIn("你曾经亲手放开过",public(g)["ending"]["text"])

    def test_actual_voluntary_A_sacrifice_still_is_truthful(self):
        g=ready()
        act(g,"A","choose")
        self.assertEqual(g["stage"],3)
        self.assertEqual(g["psych"]["assets"]["b"]["status"],"已交出")
        act(g,"B","choose")
        act(g,"B","choose")
        self.assertEqual(g["stage"],4)
        body=public(g)["scene"]["body"]
        self.assertIn("确实选择交出",body)
        self.assertIn(g["psych"]["assets"]["b"]["label"],body)

    def test_second_act_question_must_use_a_concrete_earlier_detail(self):
        from horror_planner import create
        from unittest.mock import patch
        g=initialize({"edition":"v39"})
        for a in ANSWERS:
            act(g,a)
        self.assertEqual(g["stage"],1)
        generic="如果你现在遇到一个非常难做的选择，你会怎么办？"
        with patch("horror_planner.configured",return_value=True),patch(
            "horror_planner._completion",return_value={
                "mode":"boundary","focus":"a","hook_id":"","question":generic}):
            plan=create(g)
        self.assertNotEqual(plan["question"],generic)
        grounded="如果那位和你一起核查证据的同伴，不再相信那份记录，你会怎么做？"
        with patch("horror_planner.configured",return_value=True),patch(
            "horror_planner._completion",return_value={
                "mode":"boundary","focus":"a","hook_id":"","question":grounded}):
            plan=create(g)
        self.assertEqual(plan["question"],grounded)
        self.assertIn(grounded,public(g)["scene"]["body"])

if __name__=="__main__":unittest.main()
