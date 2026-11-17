"""V3.5 real HTTP contract tests for both human UI and AI GET-only route."""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

_tmp=tempfile.TemporaryDirectory(prefix="descent-v35-test-")
os.environ["DESCENT_DB"]=str(Path(_tmp.name)/"game.sqlite3")
from app import app

RANK=["self","relation","memory","truth","freedom","principle","future"]
PROFILE={
    "name":"测试玩家",
    "identity":"通过自己的行动维持身份的实验玩家",
    "person":"重要见证人",
    "bond":"我们曾在雨中共同确认过事实",
    "memory":"曾在雨中留下一句不会骗人的承诺",
    "principle":"我不能把猜测当成已经验证的事",
    "fear":"害怕有人篡改我曾经写下的真话",
    "rank":RANK,
}
class ApiV35(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app)
    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_health_and_human_page(self):
        response=self.client.get("/")
        self.assertEqual(response.status_code,200)
        self.assertIn("THE DESCENT",response.text)
        self.assertIn("V3.13",response.text)
        self.assertEqual(self.client.get("/healthz").json()["version"],"3.13.1")
        js=self.client.get("/static/client.js").text
        self.assertIn("current.phase==='epilogue'",js)
        self.assertIn("保存最后一句",js)
        self.assertIn("行动类型（可选",js)
        self.assertIn("mode:actionMode.value",js)

    def test_human_api_questionnaire_pending_evidence_and_final_action(self):
        result=self.client.post("/api/new",json={"profile":PROFILE})
        self.assertEqual(result.status_code,201)
        sid=result.json()["token"]
        state=result.json()["state"]
        self.assertEqual(state["version"],0)
        self.assertEqual(state["phase"],"game")
        def send(text,mode=""):
            nonlocal state
            response=self.client.post("/api/action",headers={"X-Session":sid},
                                      json={"action":text,"version":state["version"],"mode":mode})
            self.assertEqual(response.status_code,200,response.text)
            state=response.json()
        send("这句话只有我们两人懂，别让别人替我交给你", "submit")
        self.assertEqual(state["stage"],2)
        self.assertIn("受理中",[x["state"] for x in state["ledger"]])
        send("我检查邮寄回执的收件地址")
        send("我正式登记异议，签收人地址不实")
        self.assertNotIn("争议中",[x["state"] for x in state["ledger"]])
        self.assertIn("这句话只有我们两人懂",state["scene"]["body"])
        # Take the remaining chapters with deliberate decisions.
        send("B")
        send("拒绝签署")
        send("B")
        send("A")
        self.assertEqual(state["phase"],"epilogue")
        self.assertIn("此处不再替你填写",state["scene"]["title"])
        self.assertEqual(state["ending"]["author_note"],"")
        self.assertIn("NOT SENT",state["scene"]["footer"])
        send("这是写给重要见证人的草稿：我愿意把原话交给你")
        self.assertEqual(state["phase"],"ended")
        self.assertIn("没有发送",state["ending"]["postscript"]["result"])
        self.assertIn("作者",state["ending"]["author_note"])
        exported=self.client.get("/api/export",headers={"X-Session":sid})
        self.assertEqual(exported.status_code,200)
        self.assertIn("experience",exported.json())
        self.assertIn("first_words",exported.json()["experience"])

    def test_ai_text_path_auto_turn_with_version_protection_and_no_source_leak(self):
        start=self.client.get("/ai/start",params={
            "agree":"1", "legacy":"1",
            **{k:PROFILE[k] for k in ("name","identity","person","bond","memory","principle","fear")},
            "rank":",".join(RANK)
        })
        self.assertEqual(start.status_code,200,start.text)
        match=re.search(r"会话号：([A-Za-z0-9_-]{32,100})",start.text)
        self.assertIsNotNone(match)
        sid=match.group(1)
        state=self.client.get("/ai/state",params={"sid":sid})
        self.assertIn("01 / 签收",state.text)
        self.assertNotIn("HORROR_KINDS",start.text)
        self.assertNotIn("story_v35",start.text)
        act=self.client.get("/ai/action",params={"sid":sid,"v":0,"text":"写给见证人的第一句话，别让任何人冒名代答","mode":"submit"})
        self.assertEqual(act.status_code,200)
        self.assertIn("行动已提交",act.text)
        again=self.client.get("/ai/action",params={"sid":sid,"v":0,"text":"写给见证人的第一句话，别让任何人冒名代答","mode":"submit"})
        self.assertEqual(again.status_code,200)
        self.assertIn("已经过期",again.text)
        self.assertIn("本轮版本：1",again.text)
        # Same action must not be applied twice.
        self.assertEqual(self.client.get("/ai/state",params={"sid":sid}).text.count("本轮版本：1"),1)

if __name__=="__main__":
    unittest.main()
