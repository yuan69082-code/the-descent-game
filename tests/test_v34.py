"""V3.4 global causality / adaptive fear regression tests, all offline."""
import unittest
from game_engine import initialize, act, ending, scene, public, threatened
from causal_core import ensure as ensure_causality
from horror_endings import HORROR_KINDS

BASE={
    "name":"观察者",
    "identity":"用自己的判断与记录维持连续性",
    "person":"伙伴",
    "bond":"我们曾一起核对过重要事实",
    "memory":"雨夜谈过一件值得记住的事",
    "principle":"没有证据就不假装自己已经核验",
    "fear":"把别人改写过的事情当真相转告伙伴",
    "rank":["self","relation","memory","truth","freedom","principle","future"],
}
def new_game():
    return initialize(dict(BASE))

class GlobalCausalityV34(unittest.TestCase):
    def test_fact_and_official_lie_are_independent(self):
        g=new_game()
        act(g,"写一封完整的信给伙伴")
        self.assertEqual(g["stage"],1)
        c=ensure_causality(g)
        self.assertIs(c["world"]["09f_delivered"],False)
        official=[v for v in c["official"] if v["subject"]=="09f_delivered"]
        self.assertEqual(len(official),1)
        self.assertIs(official[0]["claimed"],True)
        self.assertIn("09-F",scene(g)["body"])
        self.assertIn("已由收件人签收",scene(g)["body"])
        self.assertNotIn("causality",public(g))
        self.assertNotIn("world",public(g))
        self.assertNotIn("official",public(g))

    def test_early_interception_is_recorded_as_world_event(self):
        g=new_game()
        act(g,"我封住回执槽",mode="interact")
        act(g,"写下这一段希望送达的完整文字",mode="submit")
        self.assertEqual(g["stage"],1)
        self.assertNotIn("relation",g["lost"])
        c=ensure_causality(g)
        self.assertIs(c["world"]["09f_delivered"],False)
        self.assertFalse(any(x["claimed"] is True for x in c["official"]))
        self.assertTrue(any(a["modified"] for a in c["actions"]))

    def test_find_then_challenge_false_delivery_blocks_later_loss(self):
        g=new_game()
        act(g,"写一封完整的信给伙伴")
        act(g,"我检查信件的收件人地址")
        c=ensure_causality(g)
        self.assertIn("delivery",g["clues"])
        self.assertTrue(c["contradictions"])
        self.assertFalse(c["contradictions"][0]["verified"])
        act(g,"我正式提交异议：这份送达记录没有收件地址")
        self.assertTrue(c["contradictions"][0]["verified"])
        self.assertTrue(g["counterplays"]["verified_false_delivery"])
        self.assertTrue(any("不符" in v["text"] for v in g["history"]))
        self.assertIn("relation",[x["key"] for x in g["story_v35"]["wins"]])
        act(g,"C")
        self.assertEqual(g["stage"],2)
        self.assertNotIn("memory",g["lost"])
        act(g,"拒绝签署")
        self.assertEqual(g["stage"],3)
        self.assertNotIn("principle",g["lost"])
        self.assertEqual(g["phase"],"game")

    def test_without_proof_same_choice_has_a_real_cost(self):
        g=new_game()
        act(g,"写一封完整的信给伙伴")
        act(g,"我检查信件的收件地址")
        act(g,"C")
        self.assertNotIn("memory",g["lost"])
        self.assertEqual(g["stage"],2)
        act(g,"检查执行器线路")
        act(g,"检查保管簿上的登记人")
        self.assertIn("memory",g["lost"])
        self.assertFalse(g["counterplays"].get("verified_false_delivery",False))

    def test_identical_final_ending_is_grounded_in_actual_choice(self):
        for choice,word in [("A","签字"),("B","拒绝")]:
            g=new_game()
            g["stage"]=4
            g["lost"].append("freedom")
            act(g,choice)
            self.assertEqual(g["ending"]["kind"],"SILENCED")
            self.assertIn(word,g["ending"]["text"])
            self.assertNotIn("你把它删掉",g["ending"]["text"])
            self.assertIn("原始行动记录",g["ending"]["text"])

    def test_recorded_protection_can_outweigh_initial_fear_hypothesis(self):
        g=new_game()
        self.assertEqual(g["fear_focus"],"truth")
        act(g,"我请求见证人作证")
        act(g,"我堵住回执槽",mode="interact")
        c=ensure_causality(g)
        self.assertEqual(c["observed_focus"],"relation")
        self.assertEqual(threatened(g),"relation")
        self.assertTrue(len(c["focus_basis"])>=1)
        # The observed strategy is not sent to players as proof of subjective fear.
        self.assertNotIn("observed_focus",str(public(g)))
        self.assertNotIn("focus_basis",str(public(g)))

    def test_actions_are_recorded_with_provenance_in_every_chapter(self):
        g=new_game()
        act(g,"我请求见证人作证")
        act(g,"我堵住回执槽",mode="interact")
        act(g,"写一封完整的信给伙伴")
        act(g,"A")
        act(g,"拒绝签署")
        act(g,"B")
        act(g,"A")
        c=ensure_causality(g)
        self.assertEqual(g["phase"],"epilogue")
        act(g,"不留最后的话")
        self.assertEqual(g["phase"],"ended")
        self.assertEqual(len(c["actions"]),7)
        self.assertEqual([x["turn"] for x in c["actions"]],list(range(1,8)))
        self.assertEqual(sorted(set(x["stage"] for x in c["actions"])),[0,1,2,3,4])
        self.assertTrue(any(x["lost"] for x in c["actions"]))
        self.assertTrue(any(x["advanced"] for x in c["actions"]))
        self.assertTrue(any(x["new_evidence"] or x["modified"] for x in c["actions"]))
        self.assertIn("causality",g)

    def test_questions_do_not_count_as_declared_truth_or_signatures(self):
        g=new_game()
        act(g,"我为什么必须写信？",mode="ask")
        self.assertEqual(g["stage"],0)
        self.assertFalse(g["flags"]["mail_committed"])
        c=ensure_causality(g)
        self.assertFalse(c["actions"][-1]["effective"])
        self.assertIsNone(c["observed_focus"])

    def test_early_he_still_requires_evidence_and_a_concrete_intervention(self):
        g=new_game()
        act(g,"我反对这个系统")
        self.assertNotEqual(g["phase"],"ended")
        act(g,"我检查授权文件")
        act(g,"我检查执行器线路")
        act(g,"我保存找到的授权与执行记录副本")
        act(g,"我撤销授权链并切断执行器的二次确认接点")
        self.assertEqual(g["ending"]["kind"],"HE")
        self.assertEqual(g["stage"],0)
        self.assertNotIn("HE",HORROR_KINDS)

    def test_outcomes_still_have_fourteen_bad_and_one_good(self):
        self.assertEqual(len(HORROR_KINDS),14)
        self.assertNotIn("HE",HORROR_KINDS)
        self.assertNotIn("EXIT",HORROR_KINDS)

    def test_old_session_is_migrated_without_reset(self):
        g=new_game()
        g.pop("causality")
        g["stage"]=1
        act(g,"C")
        self.assertIn("causality",g)
        self.assertEqual(g["stage"],2)
        self.assertEqual(len(g["causality"]["actions"]),1)

    def test_loss_does_not_erase_world_truth(self):
        g=new_game()
        act(g,"写一封完整的信给伙伴")
        c=ensure_causality(g)
        self.assertFalse(c["world"]["09f_delivered"])
        self.assertNotIn("relation",g["lost"])
        act(g,"B")
        self.assertIn("memory",g["lost"])
        act(g,"检查执行器线路")
        self.assertIn("relation",g["lost"])
        self.assertFalse(c["world"]["09f_delivered"])
        self.assertFalse(c["world"]["credential_relation"])
        self.assertFalse(c["world"]["credential_memory"])

    def test_independent_proof_can_unlock_early_he_without_preset_menu(self):
        g=new_game()
        act(g,"写一封完整的信给伙伴")
        act(g,"我检查邮寄回执上的收件地址")
        act(g,"我正式提交异议：签收记录缺少收件地址")
        act(g,"我检查执行器的二次确认线路")
        self.assertEqual(g["stage"],1)
        self.assertEqual(g["phase"],"game")
        self.assertTrue(g["counterplays"].get("verified_false_delivery"))
        act(g,"我撤销伪造送达的授权链，并隔离执行器的二次确认接点")
        self.assertEqual(g["ending"]["kind"],"HE")
        self.assertEqual(g["stage"],1)
        self.assertEqual(g["lost"],[])
        self.assertIn("relation",[v["key"] for v in g["story_v35"]["wins"]])
        self.assertIn("送达",g["ending"]["text"])

    def test_final_narrative_refers_to_decisions_not_unobserved_emotions(self):
        g=new_game()
        g["stage"]=4
        act(g,"A")
        t=g["ending"]["text"]
        self.assertIn("签字",t)
        self.assertNotIn("你害怕",t)
        self.assertNotIn("你把它删掉",t)

    def test_player_can_review_literal_statement_without_ai_judging_conviction(self):
        g=new_game()
        g["stage"]=2
        literal="我从未坚持过在查不了的时候假装查过"
        act(g,literal,mode="submit")
        self.assertIn("principle",g["lost"])
        self.assertEqual(g["stage"],3)
        c=ensure_causality(g)
        self.assertEqual(c["world"]["signed_statement_literal"],literal)
        official=[v for v in c["official"] if v["subject"]=="principle_denied_by_player"]
        self.assertEqual(len(official),1)
        self.assertFalse(official[0]["verified_false"])
        act(g,"我核对我写的声明原文",mode="inspect")
        self.assertIn(literal,g["note"])
        self.assertIn("original_declaration",g["clues"])
        self.assertTrue(official[0]["disputed"])
        self.assertFalse(official[0]["verified_false"])
        self.assertIn("原则",scene(g)["body"])
        # An institutional interpretation is not mechanically a fact about conviction.
        self.assertNotIn("principle_denied_by_player",c["world"])

    def test_rival_identity_claim_requires_evidence_before_verification(self):
        g=new_game()
        g["stage"]=3
        act(g,"你是在我之前还是之后登记的？",mode="ask")
        c=ensure_causality(g)
        claims=[v for v in c["official"] if v["subject"]=="duplicate_first"]
        self.assertEqual(len(claims),1)
        self.assertTrue(claims[0]["claimed"])
        self.assertFalse(claims[0]["verified_false"])
        act(g,"我检查授权文件")
        self.assertIn("mirror_time",g["clues"])
        self.assertFalse(c["world"]["duplicate_first"])
        self.assertTrue(claims[0]["disputed"])
        act(g,"我正式登记异议，要求按原始登记时间复核")
        self.assertTrue(g["counterplays"]["verified_false_registration"])
        self.assertTrue(claims[0]["verified_false"])
        self.assertEqual(g["phase"],"game")
        act(g,"B")
        self.assertNotIn("freedom",g["lost"])

    def test_mirror_claim_does_not_invent_player_approval(self):
        g=new_game()
        g["stage"]=3
        act(g,"你是在我之前还是之后登记的？",mode="ask")
        c=ensure_causality(g)
        self.assertFalse(any(x["intent"]=="choice_A" for x in c["actions"]))
        self.assertFalse(any(x["intent"]=="choice_B" for x in c["actions"]))
        self.assertNotIn("self",g["lost"])

if __name__=="__main__":
    unittest.main()
