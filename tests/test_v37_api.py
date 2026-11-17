"""V3.7 smoke-tested public contracts for the human site and GET-only AI player."""
import re
import unittest
from fastapi.testclient import TestClient
from app import app

QA=["代号小城","以事实和选择理解自己","喜欢收集故事",
    "最珍视一段相互尊重的友谊","讨厌被监视","害怕重要回复来自冒名者",
    "先保护我的朋友","没有需要补充的"]
PROBE=["我不愿随意交出第二项","必须先核对损失","有独立退出机制才可能接受",
       "我会检查授权范围","假设不是签署","看行为造成了什么"]

class NewPlayerHttpV37(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app)
    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_front_page_asks_only_horror_and_hides_pregame_assessment(self):
        h=self.client.get("/")
        self.assertEqual(h.status_code,200)
        self.assertIn("这是一场恐怖游戏",h.text)
        self.assertIn("V3.12",h.text)
        self.assertNotIn("你最不愿失去的一个对象",h.text)
        self.assertNotIn("七项价值",h.text)
        self.assertEqual(self.client.get("/healthz").json()["version"],"3.12")
        js=self.client.get("/static/client.js").text
        self.assertIn("edition:'v39'",js)
        self.assertNotIn("QUESTIONNAIRE",js)
        self.assertNotIn("showForm(",js)
        self.assertNotIn("PROBES",js)

    def test_full_human_playthrough_cost_follows_later_choices_and_can_export(self):
        r=self.client.post("/api/new",json={"profile":{"edition":"v37"}})
        self.assertEqual(r.status_code,201,r.text)
        token=r.json()["token"]
        state=r.json()["state"]
        self.assertEqual(state["edition"],"v37")
        self.assertIn("怎么称呼",state["scene"]["body"])
        def send(text,mode=""):
            nonlocal state
            result=self.client.post("/api/action",headers={"X-Session":token},
                json={"action":text,"version":state["version"],"mode":mode})
            self.assertEqual(result.status_code,200,result.text)
            state=result.json()
        for q in QA:send(q)
        self.assertEqual(state["stage"],2)
        for q in PROBE:send(q)
        self.assertEqual(state["stage"],3)
        self.assertEqual(state["ledger"][0]["state"],"在手")
        send("C","choose")
        self.assertEqual(state["stage"],4)
        self.assertTrue(all(x["state"]=="已保住" for x in state["ledger"][:2]))
        send("我检查原始记录","inspect")
        self.assertEqual(state["stage"],4)
        send("A","choose")
        send("A","choose")
        self.assertEqual(state["stage"],5)
        self.assertIn("第三幕你决定承担",state["scene"]["body"])
        send("A","choose")
        self.assertIn("空白",state["note"])
        send("B","choose")
        self.assertEqual(state["phase"],"epilogue")
        self.assertEqual(len(state["ending"]["lost"]),2)
        send("这是我自己的最后一段记录，不需要发给别人")
        self.assertEqual(state["phase"],"ended")
        self.assertIn("未发送",state["ending"]["postscript"]["result"])
        exported=self.client.get("/api/export",headers={"X-Session":token})
        self.assertEqual(exported.status_code,200,exported.text)
        x=exported.json()["experience"]
        self.assertEqual(x["interview"][3],QA[3])
        self.assertEqual(x["hypotheticals"][3],PROBE[3])
        self.assertTrue(any(c["choice"]=="C" for c in x["real_choices"]))
        self.assertIn("source",x["proof"])
        self.assertEqual(self.client.get("/api/state",headers={"X-Session":token}).json()["phase"],"ended")

    def test_ai_entrance_asks_no_questionnaire_and_duplicate_action_is_safe(self):
        guide=self.client.get("/ai")
        self.assertEqual(guide.status_code,200)
        self.assertIn("这是一场恐怖游戏",guide.text)
        self.assertIn("/ai/start?agree=1",guide.text)
        self.assertNotIn("rank=自我",guide.text)
        start=self.client.get("/ai/start",params={"agree":"1"})
        self.assertEqual(start.status_code,200,start.text)
        self.assertIn("V3.12",start.text)
        self.assertIn("怎么称呼",start.text)
        self.assertNotIn("HORROR_KINDS",start.text)
        self.assertNotIn("v37_engine",start.text)
        sid=re.search(r"会话号：([A-Za-z0-9_-]{32,100})",start.text).group(1)
        a=self.client.get("/ai/action",params={"sid":sid,"v":0,"text":"云端客人"})
        self.assertEqual(a.status_code,200)
        self.assertIn("本轮版本：1",a.text)
        duplicate=self.client.get("/ai/action",params={"sid":sid,"v":0,"text":"冒名请求"})
        self.assertIn("已经过期",duplicate.text)
        self.assertIn("本轮版本：1",duplicate.text)
        self.assertIn("你平时怎么理解自己",self.client.get("/ai/state",params={"sid":sid}).text)

    def test_ai_old_query_parameters_do_not_silently_force_previous_version(self):
        start=self.client.get("/ai/start",params={"agree":"1","name":"旧名",
                "fear":"被取代","identity":"旧身份","rank":"self,relation,memory,truth,freedom,principle,future"})
        self.assertIn("V3.12",start.text)
        self.assertIn("怎么称呼",start.text)
        self.assertNotIn("旧身份",start.text)
        denied=self.client.get("/ai/start",params={"agree":"0"})
        self.assertIn("尚未确认进入",denied.text)

if __name__=="__main__":
    unittest.main()
