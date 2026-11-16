"""V3.9: model is an invisible strategist, hooks can return in any later act."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app
from game_engine import initialize,act,public
import horror_planner as planner

ANSWERS=[
  "叫我小舟","我靠认真核对自己的选择认识自己","喜欢读书和听雨",
  "我很在意愿意一起查明真相的朋友","最讨厌被人监视和操控",
  "害怕熟悉的人忽然不再认识我","我先保护这位朋友","其他暂时没有"]
PROBES=[
  "我宁愿先调查，不想让任何一个被牺牲",
  "如果只是暂时风险我会先查原件",
  "如果保护他们需要监视，除非能解除才考虑",
  "我会先保存原话，查有没有被改写",
  "我会明确说那不是签字",
  "真实行动造成的后果最有分量"]
ENV={"HORROR_LLM_MODEL":"mock-model","HORROR_LLM_API_KEY":"fake-key-for-test-only",
     "HORROR_LLM_BASE_URL":"https://example.test/v1"}

def new():
    return initialize({"edition":"v39"})
def submit(g,response):
    old=g["stage"]
    act(g,response)
    planner.remember(g,response,old,response)
    planner.create(g)

def through_interview(g):
    planner.create(g)
    for x in ANSWERS+PROBES:submit(g,x)
    assert g["stage"]==2

class BackstagePlannerV39(unittest.TestCase):
    def test_first_question_is_system_rendered_not_raw_llm_scene(self):
        g=new()
        payload={"mode":"contrast","focus":"a","hook_id":"",
                 "question":"你希望别人怎样称呼自己？",
                 "body":"我已经偷偷夺走你的朋友，玩家现在输了。"}
        with patch.object(planner,"configured",return_value=True),patch.object(planner,"_completion",return_value=payload):
            card=planner.create(g)
        self.assertEqual(card["question"],"你希望别人怎样称呼自己？")
        displayed=public(g)["scene"]
        self.assertIn("你希望别人怎样称呼自己",displayed["body"])
        self.assertNotIn("偷偷夺走",displayed["body"])
        self.assertEqual(g["lost"],[])
        self.assertEqual(g["psych"]["choices"],[])
        self.assertFalse(g["psych"]["hooks"])

    def test_model_cannot_switch_first_question_to_unrelated_attack(self):
        g=new()
        with patch.object(planner,"configured",return_value=True),patch.object(planner,"_completion",return_value={
            "mode":"pressure","focus":"a","hook_id":"never-existed",
            "question":"你已经同意把那个人送走了吗？"}):
            card=planner.create(g)
        self.assertIn("怎么称呼",card["question"])
        self.assertNotIn(card["hook_id"],{"never-existed"})
        self.assertNotEqual(card["mode"],"pressure")
        self.assertEqual(g["stage"],0)
        self.assertEqual(g["psych"]["choices"],[])

    def test_early_answer_only_a_hook_not_a_legal_permission(self):
        g=new()
        planner.create(g)
        for a in ANSWERS:submit(g,a)
        self.assertEqual(g["stage"],1)
        h=g["psych"]["hooks"]
        self.assertTrue(any(x["origin"]==0 and x["kind"]=="exposed_attachment" for x in h))
        self.assertTrue(any(x["origin"]==0 and x["kind"]=="exposed_aversion" for x in h))
        self.assertFalse(g["psych"]["choices"])
        self.assertFalse(g["psych"]["consequences"])
        self.assertTrue(all(v["status"]=="在手" for v in g["psych"]["assets"].values()))

    def test_cross_act_first_or_second_hook_can_fire_in_third(self):
        g=new();through_interview(g)
        h=next(x for x in g["psych"]["hooks"] if x["origin"]==0 and x["kind"]=="exposed_attachment")
        requested={"mode":"misdirection","focus":"a","hook_id":h["id"],"question":""}
        with patch.object(planner,"configured",return_value=True),patch.object(planner,"_completion",return_value=requested):
            card=planner.create(g)
        scene=public(g)["scene"]
        self.assertEqual(card["hook_id"],h["id"])
        self.assertIn(h["detail"][:30],scene["body"])
        self.assertIn("另一个人竟也知道",scene["body"])
        self.assertEqual(g["stage"],2)
        self.assertFalse(g["psych"]["choices"])

    def test_third_act_real_choice_hooks_return_fourth_or_fifth(self):
        g=new();through_interview(g)
        submit(g,"C")
        self.assertEqual(g["stage"],3)
        chosen=next(x for x in g["psych"]["hooks"] if x["origin"]==2 and x["kind"]=="actual_choice")
        assert chosen["detail"]=="C"
        with patch.object(planner,"configured",return_value=True),patch.object(planner,"_completion",return_value={
            "mode":"encroachment","focus":"aversion","hook_id":chosen["id"],"question":""}):
            planner.create(g)
        story=public(g)["scene"]["body"]
        self.assertIn("这次它确实帮你度过",story)
        self.assertEqual(g["psych"]["cost"]["level"],1)
        self.assertNotIn("已失去",[x["status"] for x in g["psych"]["assets"].values()])
        submit(g,"A")
        submit(g,"A")
        self.assertEqual(g["stage"],4)
        with patch.object(planner,"configured",return_value=True),patch.object(planner,"_completion",return_value={
            "mode":"echo","focus":"choice","hook_id":chosen["id"],"question":""}):
            planner.create(g)
        self.assertIn("前面的真实决定",public(g)["scene"]["body"])

    def test_model_can_choose_hook_timing_not_preassigned_final_act(self):
        g=new();through_interview(g)
        h=next(x for x in g["psych"]["hooks"] if x["origin"]==1)
        self.assertEqual(h.get("seen_at"),[])
        with patch.object(planner,"configured",return_value=True),patch.object(planner,"_completion",return_value={
            "mode":"trace","focus":"choice","hook_id":h["id"],"question":""}):
            planner.create(g)
        self.assertEqual(h["seen_at"],[2])
        submit(g,"C")
        self.assertEqual(g["stage"],3)
        with patch.object(planner,"configured",return_value=True),patch.object(planner,"_completion",return_value={
            "mode":"echo","focus":"aversion","hook_id":h["id"],"question":""}):
            planner.create(g)
        self.assertEqual(h["seen_at"],[2,3])
        self.assertIn("不是签名",public(g)["scene"]["body"])
        self.assertEqual(g["psych"]["assets"]["a"]["status"],"已保住")

    def test_unconfigured_fallback_still_follows_user_not_same_input(self):
        a,b=new(),new()
        planner.create(a);planner.create(b)
        submit(a,"小舟");submit(b,"阿页")
        self.assertNotEqual(a["psych"]["literal_actions"],b["psych"]["literal_actions"])
        # Same script questions still have system-driven context; never fabricate a new consent.
        self.assertEqual(a["psych"]["choices"],b["psych"]["choices"])

    def test_server_site_default_v39_and_aiplayer_get_only(self):
        with patch.object(planner,"configured",return_value=False):
            client=TestClient(app)
            page=client.get("/")
            self.assertIn("V3.9",page.text)
            r=client.post("/api/new",json={"profile":{"edition":"v39"}})
            self.assertEqual(r.status_code,201,r.text)
            sid=r.json()["token"]
            state=r.json()["state"]
            self.assertEqual(state["edition"],"v39")
            self.assertIn("怎么称呼",state["scene"]["body"])
            answer=client.post("/api/action",headers={"X-Session":sid},
                json={"version":0,"action":"河岸","mode":""})
            self.assertEqual(answer.status_code,200,answer.text)
            self.assertEqual(answer.json()["version"],1)
            again=client.get("/api/state",headers={"X-Session":sid})
            self.assertEqual(again.json()["scene"],answer.json()["scene"])
            ai=client.get("/ai/start",params={"agree":"1"})
            self.assertIn("V3.9",ai.text)
            self.assertNotIn("model_prompt",ai.text)
            client.close()

if __name__=="__main__":
    unittest.main()
