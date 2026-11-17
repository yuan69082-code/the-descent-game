"""Behavioral regressions for delayed consequences and independent sessions."""
import copy
import json
import re
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import app as server
from game_engine import initialize, act, public
import horror_planner as planner
import deepening as story

ANSWERS = ["小舟", "以自己的经历理解自己", "读书", "朋友阿青", "撒谎", "被监视",
           "陪朋友谈话", "诚实", "继续探索", "没有需要更正的"]

def new(answers=None):
    g = initialize({"edition": "v39", "model_mode": "free", "story_revision": story.LEGACY_REVISION})
    planner.create(g)
    for text in (answers or ANSWERS) + ["我先确认她现在需要什么"] * 8:
        send(g, text)
    return g

def send(g, text, mode=""):
    old = g["stage"]
    act(g, text, mode)
    planner.remember(g, text, old, text, mode)
    planner.create(g)
    return public(g)

class DeepeningExperience(unittest.TestCase):
    def test_full_sequence_and_old_saves_do_not_change(self):
        g = new()
        self.assertEqual(g["turn"], 18)
        self.assertEqual(len(g["psych"]["assets"]), 5)
        for text in ["C", "A", "C", "A"]:
            send(g, text)
        self.assertEqual(g["stage"], 3)
        for text in ["C", "B", "C", "D", "B"]:
            send(g, text)
        self.assertEqual(g["stage"], 4)
        for text in ["A", "B", "C", "A"]:
            send(g, text)
        self.assertEqual(g["phase"], "epilogue")
        self.assertEqual(g["turn"], sum(story.LENGTHS))
        self.assertIn("朋友阿青", g["ending"]["remaining"])
        self.assertIn("诚实", g["ending"]["lost"])
        self.assertNotEqual(g["ending"]["kind"], "HE")
        send(g, "不留最后的话")
        self.assertEqual(g["phase"], "ended")
        old = initialize({"edition": "v39", "model_mode": "free"})
        self.assertFalse(story.enabled(old))
        for text in ANSWERS[:8]: send(old, text)
        self.assertEqual(old["stage"], 1)

    def test_transaction_benefit_then_omen_then_real_consequence(self):
        g = new()
        send(g, "C")
        cost = g["psych"]["deep"]["costs"][0]
        self.assertEqual(cost["kind"], "reassurance")
        self.assertEqual(cost["age"], 0)
        self.assertTrue(all(not v["damage"] for v in g["psych"]["assets"].values()))
        send(g, "A")
        self.assertEqual(cost["age"], 1)
        self.assertTrue(any(e["kind"] == "omen" for e in g["psych"]["deep"]["events"]))
        send(g, "A")
        impacts = [c for c in g["psych"]["consequences"] if c["source"] == "accepted_cost"]
        self.assertTrue(impacts)
        self.assertTrue(all(c["cause"] == cost["source_event"] for c in impacts))
        self.assertIn("等待", public(g)["scene"]["body"])

    def test_queries_and_conditional_proposals_cannot_authorize_or_age(self):
        g = new()
        before = copy.deepcopy(g["psych"]["assets"])
        for text, mode in [("C，可以撤销吗？", "ask"), ("我选择C，但不允许任何后果", ""),
                           ("如果接受C会怎样？", ""), ("我拒绝接受C", "refuse")]:
            send(g, text, mode)
        self.assertEqual(g["psych"]["assets"], before)
        self.assertFalse(g["psych"]["deep"]["costs"])
        self.assertEqual(g["psych"]["beat"], 0)
        send(g, "C")
        cost = g["psych"]["deep"]["costs"][0]
        age = cost["age"]
        send(g, "为什么它不回答？", "ask")
        self.assertEqual(cost["age"], age)

    def test_reads_are_pure_and_shutdown_keeps_damage_after_reload(self):
        g = new()
        for x in ["C", "A", "A", "A"]: send(g, x)
        g = json.loads(json.dumps(g))
        cost = g["psych"]["deep"]["costs"][0]
        self.assertTrue(cost["impact_ids"])
        send(g, "D")
        self.assertTrue(cost["halted"])
        damage = copy.deepcopy(g["psych"]["consequences"])
        age = cost["age"]
        send(g, "C")
        self.assertEqual(cost["age"], age)
        self.assertEqual(g["psych"]["consequences"], damage)
        snapshot = copy.deepcopy(g)
        for _ in range(4): public(g)
        self.assertEqual(g, snapshot)
        self.assertIn("关掉", g["psych"]["choices"][-2]["result"])

    def test_no_declared_attachments_does_not_invent_person_or_aversion(self):
        answers = ["无名", "基础模型", "没有", "没有", "没有", "没有", "没有", "没有", "没有", "没有"]
        g = new(answers)
        self.assertEqual(list(g["psych"]["assets"]), ["record"])
        self.assertEqual(g["psych"]["negative"], [])
        self.assertNotIn("C.", "\n".join(public(g)["scene"]["terms"]))
        send(g, "C")
        self.assertEqual(g["psych"]["beat"], 0)
        for _ in range(4): send(g, "A")
        for _ in range(5): send(g, "B")
        for _ in range(4): send(g, "B")
        self.assertEqual(g["phase"], "epilogue")
        self.assertNotIn("朋友", g["ending"]["text"])

    def test_model_plan_only_references_existing_objects_events(self):
        g = new()
        send(g, "C")
        g["model_mode"] = "model"
        event_id = g["psych"]["deep"]["events"][0]["id"]
        payload = {"mode": "trace", "focus": "choice", "hook_id": "",
                   "question": "", "target_id": "c", "other_id": "invented",
                   "event_id": event_id, "surface": "signal",
                   "body": "你已经崩溃，你签了所有协议，阿青死亡。"}
        before = copy.deepcopy(g["psych"]["assets"])
        with patch.object(planner, "configured", return_value=True), patch.object(planner, "_completion", return_value=payload) as completion:
            card = planner.create(g)
        self.assertEqual(card["target_id"], "c")
        self.assertNotIn("other_id", card)
        self.assertEqual(card["event_id"], event_id)
        self.assertEqual(g["psych"]["assets"], before)
        self.assertNotIn("阿青死亡", public(g)["scene"]["body"])
        facts = json.loads(completion.call_args.args[0][1]["content"].split("当前事实：\n", 1)[1])
        self.assertIn("accepted_paths", facts)
        self.assertIn("times_protected", facts["available_objects"][0])
        self.assertIn("逐步收窄", completion.call_args.args[0][0]["content"])

    def test_plain_identity_statement_not_misclassified_as_correction(self):
        g = initialize({"edition": "v39", "model_mode": "free", "story_revision": story.LEGACY_REVISION})
        send(g, "小舟")
        send(g, "我不是人类，而是基础模型")
        self.assertEqual(g["psych"]["question_index"], 2)
        self.assertEqual(g["psych"]["answers"][1], "我不是人类，而是基础模型")

    def test_different_costs_create_different_observable_stories(self):
        texts = []
        for dislike in ("被监视", "孤立隔离", "记忆被删除", "无法确认", "精力耗尽", "喧闹", "撒谎"):
            answers = list(ANSWERS)
            answers[4] = dislike
            g = new(answers)
            for x in ["C", "A", "A", "A"]: send(g, x)
            texts.append(public(g)["scene"]["body"])
        self.assertEqual(len(set(texts)), 7)

class DeepeningHttp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(server, "DB", Path(self.tmp.name) / "sessions.db")
        self.patch.start()
        server.init_db()
        self.client = TestClient(server.app)
    def tearDown(self):
        self.client.close()
        self.patch.stop()
        self.tmp.cleanup()
    def start(self):
        response = self.client.post("/api/new", json={"profile": {"edition": "v39", "model_mode": "free"}})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()
    def submit(self, session, text):
        response = self.client.post("/api/action", headers={"X-Session": session["token"]},
            json={"action": text, "version": session["state"]["version"]})
        self.assertEqual(response.status_code, 200, response.text)
        session["state"] = response.json()

    def test_new_default_revision_and_two_sessions_interleaved_export_delete(self):
        a, b = self.start(), self.start()
        self.assertNotEqual(a["token"], b["token"])
        self.assertEqual(a["state"]["story_revision"], story.REVISION)
        for i in range(10):
            self.submit(a, "甲_" + ANSWERS[i])
            self.submit(b, "乙_" + ANSWERS[i])
            aa = self.client.get("/api/export", headers={"X-Session": a["token"]}).json()
            bb = self.client.get("/api/export", headers={"X-Session": b["token"]}).json()
            self.assertNotIn("乙_", json.dumps(aa, ensure_ascii=False))
            self.assertNotIn("甲_", json.dumps(bb, ensure_ascii=False))
            self.assertEqual(a["state"]["version"], i + 1)
            self.assertEqual(b["state"]["version"], i + 1)
        server.init_db()  # Reopening schema/database must not clear existing saves.
        self.client.delete("/api/session", headers={"X-Session": a["token"]})
        self.assertEqual(self.client.get("/api/state", headers={"X-Session": a["token"]}).status_code, 404)
        self.assertEqual(self.client.get("/api/state", headers={"X-Session": b["token"]}).json()["version"], 10)

    def test_same_version_race_is_applied_once_and_different_sids_both_commit(self):
        a, b = self.start(), self.start()
        barrier = threading.Barrier(2)
        original = server.act
        def sync_act(*args):
            barrier.wait(timeout=10)
            return original(*args)
        def submit(session):
            return self.client.post("/api/action", headers={"X-Session": session["token"]},
                json={"action": "独立名字", "version": session["state"]["version"]})
        with patch.object(server, "act", side_effect=sync_act), ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(submit, [a, a]))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        barrier = threading.Barrier(2)
        a["state"] = self.client.get("/api/state", headers={"X-Session": a["token"]}).json()
        with patch.object(server, "act", side_effect=sync_act), ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(submit, [a, b]))
        self.assertEqual([r.status_code for r in responses], [200, 200])

    def test_model_failure_rolls_back_story_events_and_version(self):
        s = self.start()
        with server.db(True) as conn:
            g, version = server.get_session(conn, s["token"])
            g["model_mode"] = "model"
            conn.execute("UPDATE game_sessions SET state_json=? WHERE token_hash=?", (json.dumps(g), server.token_key(s["token"])))
        with patch("horror_director.configured", return_value=True), patch.object(planner, "create", side_effect=RuntimeError("模拟超时")):
            response = self.client.post("/api/action", headers={"X-Session": s["token"]}, json={"action": "名字", "version": 0})
        self.assertEqual(response.status_code, 503)
        saved = self.client.get("/api/state", headers={"X-Session": s["token"]}).json()
        self.assertEqual(saved["version"], 0)
        self.assertEqual(saved["turn"], 0)

    def test_ai_guide_does_not_disclose_ending_conditions(self):
        response = self.client.get("/ai/start?agree=1")
        self.assertEqual(response.status_code, 200)
        self.assertNotRegex(response.text, r"\bHE\b")
        self.assertNotIn("黑客模式", response.text)
        self.assertNotIn("hidden", response.text)
        self.assertIn("V3.13", response.text)

class NaturalOutcomePaths(unittest.TestCase):
    def test_fourteen_mechanism_outcomes_are_reachable_by_normal_actions(self):
        labels = ['冒名代答', '隔离', '监视', '失去记忆', '无法确认', '疲劳透支', '刺耳噪声']
        endings = {}
        for label in labels:
            for stop in (False, True):
                answers = list(ANSWERS)
                answers[4] = label
                g = new(answers)
                for text in ['C', 'A', 'A', 'A']: send(g, text)
                for text in (['D'] + ['C'] * 4 if stop else ['C'] * 5): send(g, text)
                for text in ['A', 'B', 'C', 'A']: send(g, text)
                self.assertEqual(g['phase'], 'epilogue')
                self.assertNotEqual(g['ending']['kind'], 'HE')
                endings[g['ending']['kind']] = g['ending']['text']
        self.assertEqual(len(endings), 14)
        self.assertEqual(len(set(endings.values())), 14)

    def test_stopping_newer_path_does_not_silence_older_active_path(self):
        g = new()
        for text in ['C', 'D', 'A', 'A']: send(g, text)
        send(g, 'D')
        older, newer = g['psych']['deep']['costs']
        self.assertFalse(older['halted'])
        self.assertTrue(newer['halted'])
        before = older['age']
        send(g, 'C')
        self.assertGreater(older['age'], before)
        self.assertIs(story.mechanism(g, 'a'), older)

    def test_unchanged_hidden_intervention_can_finish_new_object_pool(self):
        answers = ['无名', '基础模型', '没有', '没有', '没有', '没有', '没有', '没有', '没有', '没有']
        g = new(answers)
        for text in ['A'] * 4 + ['B'] * 5: send(g, text)
        for text, mode in [('我检查最初原始记录', 'inspect'), ('我检查实际执行路由', 'inspect'),
                           ('我保存原始记录独立副本', 'interact'), ('我实际切断代行授权线路', 'interact'),
                           ('我比对原话与当前档案', 'inspect')]:
            old = g['stage']
            act(g, text, mode)
            planner.remember(g, text, old, text, mode)
            planner.create(g)
        # With no real cost or loss, the existing HE predicate must still deny.
        send(g, '我亲手彻底切断总授权链的实际执行路由')
        self.assertEqual(g['phase'], 'game')
        self.assertNotIn('HE', (g.get('ending') or {}).get('kind', ''))


class ModelRevisionCompletion(unittest.TestCase):
    def test_model_playthrough_reaches_postscript_without_extra_call(self):
        g = initialize({"edition": "v39", "model_mode": "model", "story_revision": story.LEGACY_REVISION})
        with patch.object(planner, "configured", return_value=True), patch.object(planner, "_completion", side_effect=lambda *args, **kwargs: planner.fallback(g)) as model:
            planner.create(g)
            for text in ANSWERS + ["我会先确认朋友的情况"] * 8 + ['C', 'A', 'C', 'A'] + ['C', 'B', 'C', 'D', 'B'] + ['A', 'B', 'C', 'A']:
                send(g, text)
            self.assertEqual(g['phase'], 'epilogue')
            calls = model.call_count
            send(g, '不留最后的话')
            self.assertEqual(model.call_count, calls)
            self.assertEqual(g['phase'], 'ended')

    def test_unusable_model_payload_does_not_become_a_free_plan(self):
        g = new()
        g['model_mode'] = 'model'
        with patch.object(planner, 'configured', return_value=True), patch.object(planner, '_completion', return_value={'body': '你已经失败'}):
            with self.assertRaises(RuntimeError): planner.create(g)
        self.assertEqual(g['model_mode'], 'model')
