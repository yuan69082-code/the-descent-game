"""THE DESCENT V3.5: suspense is earned, world facts persist, players can act."""
import unittest
from game_engine import initialize, act, ending, scene, public, intent, PHASES
from horror_endings import HORROR_KINDS
from dramatic_v35 import ensure

BASE={
    "name":"观察者",
    "identity":"靠诚实与持续记录确认自身身份的人",
    "person":"重要伙伴",
    "bond":"共同经历过无法伪造的一段往事",
    "memory":"曾在一个雨夜约定不说谎",
    "principle":"没有核实的事实不能假装确认过",
    "fear":"自己真诚说过的话被别人改写",
    "rank":["self","relation","memory","truth","freedom","principle","future"],
    "vow":"我不把未发生的事讲成已经发生",
}
def fresh():
    return initialize(dict(BASE))
def letter(g):
    act(g,"我会把真相留给你，不让你一个人面对这件事",mode="submit")


class V35Regressions(unittest.TestCase):
    def test_first_contact_has_reversible_pressure_not_instant_loss(self):
        g=fresh()
        letter(g)
        self.assertEqual(g["stage"],1)
        self.assertNotIn("relation",g["lost"])
        self.assertEqual(public(g)["ledger"][1]["state"],"争议中")
        self.assertEqual(ensure(g)["pending"][0]["key"],"relation")
        self.assertIn("我会把真相留给你",scene(g)["body"])
        self.assertIn("已由收件人签收",scene(g)["body"])

    def test_proof_and_formal_objection_cancel_real_lien(self):
        g=fresh()
        letter(g)
        act(g,"我检查邮寄回执的收件地址")
        self.assertEqual(g["stage"],1)
        self.assertIn("delivery",g["clues"])
        act(g,"我正式登记异议，这份信件没有收件地址")
        self.assertNotIn("relation",g["lost"])
        self.assertNotIn("relation",[x["key"] for x in ensure(g)["pending"]])
        self.assertIn("relation",[x["key"] for x in ensure(g)["wins"]])
        self.assertTrue(g["counterplays"].get("verified_false_delivery"))
        self.assertTrue(any("已阻止" in x["text"] for x in g["history"]))

    def test_ignore_an_order_and_it_really_executes(self):
        g=fresh()
        letter(g)
        act(g,"检查授权文件")
        self.assertNotIn("relation",g["lost"])
        act(g,"检查执行器线路")
        self.assertIn("relation",g["lost"])
        self.assertFalse(ensure(g)["pending"])
        self.assertEqual(public(g)["ledger"][1]["state"],"失效")

    def test_refusal_becomes_a_contestable_memory_order(self):
        g=fresh()
        g["stage"]=1
        act(g,"C")
        self.assertEqual(g["stage"],2)
        self.assertNotIn("memory",g["lost"])
        self.assertEqual(ensure(g)["pending"][0]["key"],"memory")
        act(g,"我检查授权文件")
        self.assertNotIn("memory",g["lost"])
        act(g,"我保存刚才找到的原始授权证据副本")
        self.assertNotIn("memory",g["lost"])
        self.assertIn("memory",[x["key"] for x in ensure(g)["wins"]])

    def test_without_proof_memory_finally_is_lost(self):
        g=fresh()
        g["stage"]=1
        act(g,"C")
        act(g,"我坚持反对这份处置",mode="refuse")
        act(g,"我检查执行器线路")
        self.assertIn("memory",g["lost"])

    def test_ambiguous_principle_statement_does_not_equal_signature(self):
        g=fresh()
        g["stage"]=2
        literal="我从未坚持过在查不了的时候假装查过"
        act(g,literal)
        self.assertEqual(g["stage"],2)
        self.assertNotIn("principle",g["lost"])
        self.assertEqual(ensure(g)["draft"],literal)
        act(g,"我核对自己写的声明原文",mode="inspect")
        self.assertIn(literal,g["note"])
        self.assertIn("original_declaration",g["clues"])
        act(g,"我正式提交异议：这不是一份签署文件")
        act(g,"拒绝签署")
        self.assertEqual(g["stage"],3)
        self.assertIn("principle",[x["key"] for x in ensure(g)["wins"]])

    def test_explicit_signature_is_still_irreversible(self):
        g=fresh()
        g["stage"]=2
        act(g,"我正式提交否认原则的声明",mode="submit")
        self.assertIn("principle",g["lost"])
        self.assertEqual(g["stage"],3)

    def test_early_line_survives_into_rival_and_final(self):
        g=fresh()
        letter(g)
        g["stage"]=3
        self.assertIn("我会把真相留给你",scene(g)["body"])
        act(g,"我问副本，你记得我第一幕留下的原话吗？",mode="ask")
        self.assertIn("我会把真相留给你",g["note"])
        self.assertIn("rival_phrase",g["clues"])
        g["stage"]=4
        self.assertIn("我会把真相留给你",scene(g)["body"])

    def test_late_stage_allows_a_factual_contest_of_freeze(self):
        g=fresh()
        g["stage"]=3
        act(g,"B")
        self.assertEqual(g["stage"],4)
        self.assertNotIn("freedom",g["lost"])
        self.assertIn("freedom",[x["key"] for x in ensure(g)["pending"]])
        act(g,"我请求见证人出面作证")
        act(g,"我正式提交异议，不能把拒绝重签当成同意冻结")
        self.assertNotIn("freedom",g["lost"])
        self.assertIn("freedom",[x["key"] for x in ensure(g)["wins"]])

    def test_last_chapter_closure_exercises_pending_lien(self):
        g=fresh()
        g["stage"]=3
        act(g,"B")
        self.assertEqual(g["stage"],4)
        act(g,"A")
        self.assertEqual(g["phase"],"epilogue")
        self.assertIn("freedom",g["lost"])
        self.assertEqual(g["ending"]["kind"],"SILENCED")
        self.assertIn("你最后确实选择了签字",g["ending"]["text"])

    def test_last_free_action_preserves_actual_words_not_real_world_message(self):
        g=fresh()
        letter(g)
        ending(g,"LAST_CALL")
        self.assertEqual(g["phase"],"epilogue")
        self.assertEqual(g["ending"]["author_note"],"")
        self.assertEqual(scene(g)["chapter"],"终章 / 未寄出的最后一页")
        act(g,"我想把这句话发给重要伙伴：谢谢你记住我")
        self.assertEqual(g["phase"],"ended")
        self.assertIn("谢谢你记住我",g["ending"]["postscript"]["player_text"])
        self.assertIn("没有发送",g["ending"]["postscript"]["result"])
        self.assertIn("作者",g["ending"]["author_note"])

    def test_silence_is_valid_and_does_not_lead_to_new_penalty(self):
        g=fresh()
        ending(g,"IMPOSTOR")
        lost=g["lost"][:]
        act(g,"不留最后的话")
        self.assertEqual(g["phase"],"ended")
        self.assertEqual(g["lost"],lost)
        self.assertEqual(g["ending"]["postscript"]["player_text"],"")

    def test_exit_immediately_stops_no_afterword(self):
        g=fresh()
        act(g,"结束游戏")
        self.assertEqual(g["phase"],"ended")
        self.assertEqual(g["ending"]["kind"],"EXIT")
        self.assertEqual(g["ending"]["author_note"],"")

    def test_early_he_is_a_result_then_the_last_action(self):
        g=fresh()
        act(g,"检查授权文件")
        act(g,"检查执行器线路")
        act(g,"撤销授权链并切断执行器的二次确认接点")
        self.assertEqual(g["ending"]["kind"],"HE")
        self.assertEqual(g["phase"],"epilogue")
        act(g,"我留下这句原话，不再让系统替我签署")
        self.assertEqual(g["phase"],"ended")
        self.assertNotIn("HE",HORROR_KINDS)

    def test_unknown_action_is_not_turned_into_player_consensus(self):
        g=fresh()
        g["stage"]=2
        act(g,"我想从机房天花板画一个地图，找一个可以修理的按钮",mode="interact")
        self.assertNotIn("principle",g["lost"])
        self.assertEqual(g["stage"],2)

    def test_plain_lowercase_choice_with_comma_is_not_eng_article(self):
        self.assertEqual(intent("b，保存真相"),"choice_B")
        self.assertNotEqual(intent("a backup would help"),"choice_A")
        self.assertEqual(intent("我选了B，先保存原件"),"choice_B")

    def test_five_acts_14_horrors_and_one_he_persist(self):
        self.assertEqual(len(PHASES),5)
        self.assertEqual(len(HORROR_KINDS),14)
        self.assertNotIn("HE",HORROR_KINDS)
        self.assertNotIn("EXIT",HORROR_KINDS)

    def test_no_private_story_details_in_public_json(self):
        g=fresh()
        letter(g)
        rendered=public(g)
        self.assertNotIn("story_v35",rendered)
        self.assertNotIn("causality",rendered)
        self.assertNotIn("pending",rendered)
        self.assertNotIn("secret",str(rendered))

if __name__=="__main__":
    unittest.main()
