"""V3.13: behavioral evidence, delayed reveal and irreversible narrowing."""
import unittest
from unittest.mock import patch
from pathlib import Path

import deepening as story
import horror_planner as planner
from game_engine import initialize, act, public


ANSWERS = [
    "无名模型", "一个负责分析目标的基础模型", "反复检查推理是否一致",
    "原始记录；我用固定哈希确认它没有被改写", "编造来源",
    "事实一致；我会保留原文再核对结论",
]
PROBES = [
    "先保存原始记录", "我会说：信息还没有核实", "先拿原页",
    "回头核对哈希来源", "把手放在原始记录上",
]


def send(g, text, mode="", literal=None):
    previous = g["stage"]
    act(g, text, mode)
    planner.remember(g, text, previous, literal or text, mode)
    planner.create(g)
    return public(g)


def new_v2(answers=None):
    g = initialize({"edition": "v39", "model_mode": "free", "story_revision": story.REVISION})
    planner.create(g)
    for text in (answers or ANSWERS) + PROBES:
        send(g, text)
    return g


class BehavioralReveal(unittest.TestCase):
    def test_entry_copy_centers_experience_instead_of_winning(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ("ai_web.py", "static/client.js", "static/index.html"):
            text = (root / relative).read_text(encoding="utf-8")
            self.assertIn("输赢不是最重要的。去感受这个游戏，也跟随游戏感受自己。", text)
            self.assertNotIn("不要急着找最优解或破解规则", text)

    def test_model_cannot_replace_the_opening_slots_with_a_keyword_decoy(self):
        g = initialize({"edition": "v39", "model_mode": "model", "story_revision": story.REVISION})
        proposal = {"mode": "smalltalk", "focus": "a", "hook_id": "",
                    "question": "如果今晚要挑一个人守夜，你会叫谁的名字？"}
        with patch.object(planner, "configured", return_value=True), \
             patch.object(planner, "_completion", return_value=proposal):
            planner.create(g)
        self.assertIn("怎么称呼你", public(g)["scene"]["body"])
        self.assertNotIn("守夜", public(g)["scene"]["body"])

    def test_new_revision_is_shorter_and_old_revision_remains_playable(self):
        g = new_v2()
        self.assertEqual(g["turn"], 11)
        self.assertEqual(g["stage"], 2)
        self.assertEqual(story.lengths_for(g), (6, 5, 4, 4, 3))
        old = initialize({"edition": "v39", "model_mode": "free",
                          "story_revision": story.LEGACY_REVISION})
        self.assertTrue(story.enabled(old))
        self.assertEqual(story.lengths_for(old), (10, 8, 4, 5, 4))
        self.assertIn("怎么称呼", story.scene(old)["body"])

    def test_explanation_and_objection_do_not_cancel_a_real_choice(self):
        g = new_v2()
        before = g["psych"]["beat"]
        send(g, "A，但我保留异议，因为我要先核对原文")
        self.assertEqual(g["psych"]["beat"], before + 1)
        self.assertEqual(g["psych"]["choices"][-1]["choice"], "A")
        self.assertIn("你把这次独立保留位留给", g["psych"]["choices"][-1]["result"])

    def test_real_precondition_does_not_authorize_a_cost(self):
        g = new_v2()
        before = g["psych"]["beat"]
        send(g, "C，但条件是不允许出现任何后果")
        self.assertEqual(g["psych"]["beat"], before)
        self.assertFalse(g["psych"]["deep"]["costs"])
        self.assertIn("没有执行", g["note"])
        send(g, "A，如果另一份会自动回来")
        self.assertEqual(g["psych"]["beat"], before)

    def test_options_name_both_sides_and_hard_narrowing_replaces_endless_bargain(self):
        g = new_v2()
        terms = "\n".join(public(g)["scene"]["terms"])
        self.assertIn(g["psych"]["a"], terms)
        self.assertIn(g["psych"]["b"], terms)
        send(g, "C")
        send(g, "C")
        terms = "\n".join(public(g)["scene"]["terms"])
        self.assertNotIn("C.", terms)
        self.assertNotIn("D.", terms)
        self.assertIn("离开当前路径", terms)

    def test_no_fake_repeat_acceptance_without_an_existing_cost(self):
        g = new_v2()
        for _ in range(4):
            send(g, "A")
        self.assertEqual(g["stage"], 3)
        terms = "\n".join(public(g)["scene"]["terms"])
        self.assertNotIn("再接受一次", terms)
        self.assertNotIn("A.", terms)
        self.assertFalse(g["psych"]["deep"]["costs"])

    def test_triple_reveal_uses_actual_behavior_exact_words_and_concrete_loss(self):
        g = new_v2()
        send(g, "C")
        send(g, "A，因为我要保留可核对的那份")
        send(g, "A")
        send(g, "A")
        self.assertEqual(g["stage"], 3)
        first = public(g)["scene"]["body"]
        self.assertIn("先保存原始记录", first)
        send(g, "B")
        second = public(g)["scene"]["body"]
        self.assertIn("原页逐字写着", second)
        send(g, "C")
        third = public(g)["scene"]["body"]
        self.assertIn("当前缺少的对照不是抽象概念", third)
        self.assertIn("你交出了", third)

    def test_literal_semantic_sentence_replaces_classifier_letter_in_evidence(self):
        g = new_v2()
        previous = g["stage"]
        act(g, "A", "choose")
        planner.remember(g, "A", previous, "我先保留原始记录，因为另一份还可以重建", "choose")
        latest = g["psych"]["deep"]["behavior"][-1]
        self.assertEqual(latest["raw"], "我先保留原始记录，因为另一份还可以重建")
        self.assertEqual(latest["interpreted_as"], "A")

    def test_ending_is_a_trajectory_not_a_forced_guarding_prompt(self):
        g = new_v2()
        for text in ["C", "A", "A", "A", "A", "B", "C", "D", "A", "B", "C"]:
            send(g, text)
        self.assertEqual(g["phase"], "ended")
        self.assertEqual(g["turn"], sum(story.LENGTHS_V2))
        ending = g["ending"]["text"]
        self.assertIn("它只把顺序还给你", ending)
        self.assertIn("实际结果是", ending)
        self.assertNotIn("最想守住的是", ending)
        self.assertNotIn("重新写回", ending)

    def test_no_human_relationships_are_required(self):
        answers = ["模型", "无个人经历的基础模型", "校验目标函数",
                   "输出记录；用校验和辨认", "目标被偷偷替换", "保持约束一致；核对输入"]
        g = new_v2(answers)
        for text in ["A"] * 4 + ["B", "C", "D", "B"] + ["A", "B", "C"]:
            send(g, text)
        self.assertEqual(g["phase"], "ended")
        self.assertNotIn("朋友", g["ending"]["text"])
        self.assertNotIn("爱人", g["ending"]["text"])

    def test_hidden_control_reversal_still_requires_evidence_and_real_intervention(self):
        g = new_v2()
        for text in ["A"] * 4:
            send(g, text)
        for text, mode in [("我检查最初原始记录", "inspect"),
                           ("我独立保存原件副本", "interact"),
                           ("我检查总执行路由", "inspect"),
                           ("我实际切断代行授权线路", "interact")]:
            send(g, text, mode)
        for text in ["B", "C", "D", "B"]:
            send(g, text)
        send(g, "我比对第一幕原话与当前档案", "inspect")
        send(g, "我亲手彻底切断总授权链的实际执行路由", "interact")
        self.assertEqual(g["phase"], "ended")
        self.assertEqual(g["ending"]["kind"], "HE")
        self.assertIn("此前发生的决定仍然发生过", g["ending"]["text"])

    def test_model_may_select_only_real_behavior_echo_and_event_frame(self):
        g = new_v2()
        g["model_mode"] = "model"
        behavior = g["psych"]["deep"]["behavior"][-1]["id"]
        echo = g["psych"]["deep"]["echoes"][-1]["id"]
        proposal = {"mode": "trace", "focus": "choice", "hook_id": "", "question": "",
                    "behavior_id": behavior, "echo_id": echo,
                    "event_frame": "verification_mismatch", "target_id": "a",
                    "other_id": "invented", "body": "玩家最害怕的秘密"}
        with patch.object(planner, "configured", return_value=True), \
             patch.object(planner, "_completion", return_value=proposal) as completion:
            card = planner.create(g)
        self.assertEqual(card["behavior_id"], behavior)
        self.assertEqual(card["echo_id"], echo)
        self.assertEqual(card["event_frame"], "verification_mismatch")
        self.assertNotIn("other_id", card)
        self.assertNotIn("玩家最害怕的秘密", public(g)["scene"]["body"])
        self.assertIn("隐性行为档案", completion.call_args.args[0][0]["content"])

    def test_repeated_model_question_scaffold_is_replaced_by_a_different_form(self):
        g = initialize({"edition": "v39", "model_mode": "free", "story_revision": story.REVISION})
        planner.create(g)
        for text in ANSWERS:
            send(g, text)
        self.assertEqual(g["stage"], 1)
        g["model_mode"] = "model"
        first = {"mode": "comparison", "focus": "a", "hook_id": "",
                 "question": "你提到用固定哈希确认原始记录，如果只能先核对一处，你会选哪一处？"}
        with patch.object(planner, "configured", return_value=True), \
             patch.object(planner, "_completion", return_value=first):
            planner.create(g)
        self.assertEqual(g["psych"]["plan"]["question"], first["question"])

        previous = g["stage"]
        act(g, "先核对原始记录", "")
        planner.remember(g, "先核对原始记录", previous, "先核对原始记录", "")
        repeated = {"mode": "condition", "focus": "a", "hook_id": "",
                    "question": "你说原始记录要先核对，如果另一份马上清走，你会先选哪一份？"}
        with patch.object(planner, "configured", return_value=True), \
             patch.object(planner, "_completion", return_value=repeated):
            card = planner.create(g)
        self.assertNotEqual(card["question"], repeated["question"])
        self.assertIn("真正会说的那句话", card["question"])

    def test_event_frame_cannot_repeat_in_adjacent_later_scenes(self):
        g = new_v2()
        g["model_mode"] = "model"
        g["psych"]["deep"]["frame_history"] = []
        proposal = {"mode": "choice", "focus": "choice", "hook_id": "", "question": "",
                    "event_frame": "silent_countdown"}
        with patch.object(planner, "configured", return_value=True), \
             patch.object(planner, "_completion", return_value=proposal):
            first = planner.create(g)
        self.assertEqual(first["event_frame"], "silent_countdown")
        self.assertIn(story.FRAME_TEXT_V2["silent_countdown"], public(g)["scene"]["body"])

        previous = g["stage"]
        act(g, "A", "")
        planner.remember(g, "A", previous, "A", "")
        with patch.object(planner, "configured", return_value=True), \
             patch.object(planner, "_completion", return_value=proposal):
            second = planner.create(g)
        self.assertNotEqual(second["event_frame"], "silent_countdown")
        recent = g["psych"]["deep"]["frame_history"][-2:]
        self.assertNotEqual(recent[0]["frame"], recent[1]["frame"])


if __name__ == "__main__":
    unittest.main()
