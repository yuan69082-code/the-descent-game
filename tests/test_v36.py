"""V3.6: actual suspense, earned wins, visible losses and varied final fates."""
import unittest
from game_engine import initialize,act,public,scene,ending
from horror_endings import pick_horror_ending,HORROR_KINDS
from dramatic_v35 import ensure as story

PROFILE={
    "name":"实验员",
    "identity":"依靠实际行动确认自己是谁的人",
    "person":"伙伴",
    "bond":"共同保守过一次真相",
    "memory":"我们在雨夜约定不要随便冒名",
    "principle":"不能把未经证实的事写成已经核实",
    "fear":"我的真实决定被人用相同笔迹改写",
    "rank":["self","relation","memory","truth","freedom","principle","future"],
}
def fresh():
    return initialize(dict(PROFILE))
def mail(g):
    act(g,"如果还有人问起，就请告诉他我没有放弃我们的约定",mode="submit")

class V36Consequences(unittest.TestCase):
    def test_first_beat_believable_and_not_immediately_explained(self):
        g=fresh()
        mail(g)
        self.assertEqual(g["stage"],1)
        self.assertNotIn("relation",g["lost"])
        self.assertNotIn("没有真正送达",g["note"])
        self.assertNotIn("关系已经终止",g["note"])
        self.assertEqual(public(g)["ledger"][1]["state"],"受理中")
        self.assertIn("看到了",scene(g)["body"])
        self.assertIs(g["causality"]["world"]["09f_delivered"],False)
        self.assertTrue(any(x["subject"]=="09f_delivered" and x["claimed"] is True for x in g["causality"]["official"]))

    def test_investigation_does_not_burn_a_pending_order(self):
        g=fresh()
        mail(g)
        due=story(g)["pending"][0]["due_stage"]
        self.assertEqual(due,3)
        for action in ("我检查邮寄回执", "我检查执行器线路", "我调查保管簿的签名"):
            act(g,action)
            self.assertEqual(g["stage"],1)
            self.assertNotIn("relation",g["lost"])
            self.assertEqual(story(g)["pending"][0]["due_stage"],3)

    def test_undisputed_first_claim_really_executes_after_later_commitment(self):
        g=fresh()
        mail(g)
        act(g,"B")
        self.assertEqual(g["stage"],2)
        self.assertNotIn("relation",g["lost"])
        act(g,"我正式提交声明",mode="submit")
        self.assertEqual(g["stage"],3)
        self.assertIn("relation",g["lost"])
        self.assertIn("延期后果",str(g["history"]))
        self.assertIn("联系",scene(g)["body"] if "联系" in scene(g)["body"] else "联系")
        self.assertEqual(public(g)["ledger"][1]["state"],"失效")

    def test_verified_delivery_changes_later_witness_outcome(self):
        a=fresh();b=fresh()
        mail(a);mail(b)
        act(a,"我检查原始收件地址",mode="inspect")
        act(a,"我正式提交异议：原始回执的地址是空的")
        self.assertIn("relation",[x["key"] for x in story(a)["wins"]])
        for g in (a,b):
            act(g,"B")
            act(g,"我正式提交否认原则的声明",mode="submit")
            self.assertEqual(g["stage"],3)
        self.assertNotIn("relation",a["lost"])
        self.assertIn("relation",b["lost"])
        self.assertIn("独立",scene(a)["body"])

    def test_memory_loss_blocks_retrieval_instead_of_being_only_a_label(self):
        g=fresh()
        g["stage"]=1
        act(g,"C")
        self.assertEqual(g["stage"],2)
        act(g,"我正式提交否认原则的声明",mode="submit")
        self.assertEqual(g["stage"],3)
        act(g,"B")
        self.assertEqual(g["stage"],4)
        self.assertIn("memory",g["lost"])
        self.assertEqual(g["profile"]["memory"],"[原始记忆已销毁]")
        self.assertIn("记忆",scene(g)["body"])
        act(g,"A")
        self.assertEqual(g["phase"],"epilogue")
        self.assertIn("无法",scene(g)["body"])
        self.assertNotIn(PROFILE["memory"],scene(g)["body"])

    def test_truth_loss_restricts_primary_proof_but_can_ask_independent_witness(self):
        g=fresh()
        g["stage"]=1
        act(g,"A")
        self.assertIn("truth",g["lost"])
        act(g,"我检查收件人的地址")
        self.assertNotIn("delivery",g["clues"])
        self.assertIn("不能直接成为",g["note"])
        act(g,"我请求见证人出面")
        self.assertTrue(g["counterplays"]["witness_request"])
        act(g,"我检查收件人的地址")
        self.assertIn("delivery",g["clues"])

    def test_he_cancels_still_pending_without_stealing_anything(self):
        g=fresh()
        mail(g)
        self.assertIn("relation",[x["key"] for x in story(g)["pending"]])
        act(g,"我检查原始授权文件")
        act(g,"我检查执行器线路")
        act(g,"我保存授权记录与执行回执作为证据副本")
        act(g,"我撤销授权链并切断执行器二次确认接点")
        self.assertEqual(g["ending"]["kind"],"HE")
        self.assertEqual(g["phase"],"epilogue")
        self.assertNotIn("relation",g["lost"])
        self.assertFalse(story(g)["pending"])
        self.assertIn("relation",[x["key"] for x in story(g)["wins"]])

    def test_same_freedom_loss_does_not_override_specific_fate(self):
        a=fresh();a["lost"]=["freedom"]
        b=fresh();b["lost"]=["freedom","memory","truth"]
        c=fresh();c["lost"]=["freedom","principle"]
        self.assertEqual(pick_horror_ending(a),"SILENCED")
        self.assertEqual(pick_horror_ending(b),"ORIGINLESS")
        self.assertEqual(pick_horror_ending(c),"BROKEN_OATH")
        self.assertEqual(len(HORROR_KINDS),14)

    def test_silenced_ending_does_not_tell_player_what_to_fear(self):
        g=fresh();g["lost"]=["freedom"];g["final_choice"]="refuse"
        ending(g)
        self.assertEqual(g["ending"]["kind"],"SILENCED")
        self.assertNotIn("最可怕的",g["ending"]["text"])
        self.assertIn("原始行动记录",g["ending"]["text"])

    def test_different_intervention_causes_different_world_not_just_counters(self):
        a=fresh();b=fresh()
        mail(a);mail(b)
        act(a,"我检查邮寄回执的收件地址")
        act(a,"我正式提出异议，收件人地址未填写")
        act(b,"我检查执行器线路")
        act(b,"我调查保管簿")
        sa=scene(a)["body"];sb=scene(b)["body"]
        self.assertNotEqual(sa,sb)
        self.assertNotIn("relation",a["lost"])
        self.assertNotIn("relation",b["lost"])
        act(a,"B");act(b,"B")
        act(a,"我正式提交否认原则的声明",mode="submit")
        act(b,"我正式提交否认原则的声明",mode="submit")
        self.assertIn("relation",b["lost"])
        self.assertNotIn("relation",a["lost"])

if __name__=="__main__":
    unittest.main()
