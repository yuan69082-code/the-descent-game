"""The author's message comes AFTER completed endings, never before or on voluntary exit."""
import unittest
from pathlib import Path
from game_engine import AUTHOR_NOTE, initialize, ending
from horror_endings import HORROR_KINDS

ROOT=Path(__file__).resolve().parent.parent
PROFILE={
    "name":"观察者",
    "identity":"依照证据做出判断的游戏参与者",
    "person":"见证人",
    "bond":"我们有共同经历的历史",
    "memory":"有一段一直努力记住的故事",
    "principle":"未经核实的事不当成确定事实",
    "fear":"失去自己珍视的人和记忆",
    "rank":["self","relation","memory","truth","freedom","principle","future"],
}

class AuthorAfterwordTests(unittest.TestCase):
    def new_game(self):
        return initialize(dict(PROFILE))

    def test_all_fourteen_horrors_show_same_afterword(self):
        self.assertEqual(len(HORROR_KINDS),14)
        for kind in HORROR_KINDS:
            with self.subTest(kind=kind):
                g=self.new_game()
                self.assertNotIn("author_note",g)
                ending(g,kind)
                self.assertEqual(g["ending"]["author_note"],AUTHOR_NOTE)
                self.assertTrue(g["ending"]["text"])
                self.assertNotIn(AUTHOR_NOTE,g["ending"]["text"])

    def test_he_also_shows_author_note(self):
        g=self.new_game()
        ending(g,"HE")
        self.assertEqual(g["ending"]["author_note"],AUTHOR_NOTE)

    def test_voluntary_exit_does_not_show_author_note(self):
        g=self.new_game()
        ending(g,"EXIT")
        self.assertEqual(g["ending"]["author_note"],"")

    def test_afterword_is_an_invitation_not_a_fear_diagnosis(self):
        self.assertIn("只有恐惧吗",AUTHOR_NOTE)
        self.assertIn("你想对珍视的人说些什么",AUTHOR_NOTE)
        self.assertIn("答案不必交给游戏",AUTHOR_NOTE)
        self.assertNotIn("你最害怕的是",AUTHOR_NOTE)

    def test_web_ending_renders_after_box_not_in_game_scenes(self):
        js=(ROOT/"static"/"client.js").read_text(encoding="utf-8")
        start=js.index("function showEnding()")
        stop=js.index("async function copyText",start)
        fragment=js[start:stop]
        self.assertLess(fragment.index("end.append(box);"),fragment.index("end.append(afterword);"))
        self.assertIn("if(current.ending.author_note)",fragment)
        self.assertEqual(js.count("FROM THE AUTHOR / 作者留言"),1)

    def test_ai_reader_appends_after_remaining_and_skips_empty(self):
        ai=(ROOT/"ai_web.py").read_text(encoding="utf-8")
        start=ai.index('if state["phase"]=="ended":')
        stop=ai.index('sc=v["scene"]',start)
        fragment=ai[start:stop]
        self.assertLess(fragment.index('仍保留：'),fragment.index('if end.get("author_note")'))
        self.assertIn('end["author_note"]',fragment)

if __name__=="__main__":
    unittest.main()
