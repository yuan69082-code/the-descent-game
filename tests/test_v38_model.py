"""V3.8 model tests: exact world authority, HTTP protocol, no duplicate inference."""
import json
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app import app
from game_engine import initialize,act,public
import horror_director as director

ENV={"HORROR_LLM_API_KEY":"unit-test-key-do-not-use",
     "HORROR_LLM_MODEL":"fictional-test-model",
     "HORROR_LLM_BASE_URL":"https://unit-tests.example/v1"}
MODEL_SCENE={"title":"有人敲门","body":"她在门外敲了两下，等你开口。过了一会儿，她把声音压得很低，问你还记不记得昨晚谈过的那本书。"}
ANSWERS=["阿禾","凭自己说过的话确认身份","喜欢旧照片与雨声",
         "在意一个能听出我的声音的朋友","讨厌被监视","最不想被别人替代",
         "先保护那位朋友","没有"]
PROBES=["先了解情况","不轻易放弃","可以考虑代价","我会检查异常","不代表签署","按行动判断"]

def ready():
    g=initialize({"edition":"v38"})
    for a in ANSWERS:act(g,a)
    for a in PROBES:act(g,a)
    return g

class ModelDirectorV38(unittest.TestCase):
    def test_official_deepseek_uses_max_tokens_json_and_reasoning(self):
        seen=[]
        def handler(request):
            self.assertEqual(request.url.host,"api.deepseek.com")
            self.assertEqual(request.url.path,"/chat/completions")
            payload=json.loads(request.content)
            seen.append(payload)
            self.assertEqual(payload["model"],"deepseek-v4-pro")
            self.assertNotIn("max_completion_tokens",payload)
            self.assertIn("max_tokens",payload)
            self.assertEqual(payload["response_format"],{"type":"json_object"})
            return httpx.Response(200,json={"choices":[{"message":{
                "content":json.dumps(MODEL_SCENE,ensure_ascii=False)}}]})
        original=httpx.Client
        def mock_client(*args,**kwargs):
            return original(transport=httpx.MockTransport(handler),**kwargs)
        env={"HORROR_LLM_API_KEY":"unit-test-only",
             "HORROR_LLM_MODEL":"deepseek-v4-pro",
             "HORROR_LLM_BASE_URL":"https://api.deepseek.com"}
        with patch.dict(os.environ,env),patch("httpx.Client",side_effect=mock_client):
            planning=director._completion([{"role":"system","content":"输出 JSON"},
                                           {"role":"user","content":"请策划下一幕"}],420)
            classification=director._completion([{"role":"system","content":"JSON 语义识别"},
                                                 {"role":"user","content":"识别真实行动"}],190)
        self.assertEqual(planning,MODEL_SCENE)
        self.assertEqual(classification,MODEL_SCENE)
        self.assertEqual(seen[0]["reasoning_effort"],"high")
        self.assertEqual(seen[1]["reasoning_effort"],"low")
        self.assertGreaterEqual(seen[0]["max_tokens"],3072)
        self.assertGreaterEqual(seen[1]["max_tokens"],1024)
        self.assertEqual(len(seen),2)

    def test_model_is_opt_in_and_never_invents_credentials(self):
        with patch.dict(os.environ,{"HORROR_LLM_API_KEY":"","HORROR_LLM_MODEL":""}):
            self.assertFalse(director.configured())
            g=initialize({"edition":"v38"})
            director.render(g)
            self.assertEqual(g["director"]["mode"],"rules")
            self.assertIn("怎么称呼",public(g)["scene"]["body"])
        with patch.dict(os.environ,{**ENV,"HORROR_LLM_BASE_URL":"http://127.0.0.1:8000"},clear=False):
            self.assertFalse(director.configured())

    def test_chat_completions_https_real_wire_contract_with_local_fake(self):
        calls=[]
        def handler(request):
            self.assertEqual(request.url.host,"unit-tests.example")
            self.assertEqual(request.url.path,"/v1/chat/completions")
            self.assertEqual(request.headers["authorization"],"Bearer unit-test-key-do-not-use")
            request_body=json.loads(request.content)
            self.assertEqual(request_body["model"],"fictional-test-model")
            self.assertIn("max_completion_tokens",request_body)
            self.assertNotIn("max_tokens",request_body)
            calls.append(request_body)
            return httpx.Response(200,json={"choices":[{"message":{
                "role":"assistant","content":json.dumps(MODEL_SCENE,ensure_ascii=False)}}]})
        OriginalClient=httpx.Client
        def client(*args,**kwargs):
            return OriginalClient(transport=httpx.MockTransport(handler),**kwargs)
        with patch.dict(os.environ,ENV), patch("httpx.Client",side_effect=client):
            out=director._completion([{"role":"system","content":"demo"},
                                      {"role":"user","content":"demo"}],500)
        self.assertEqual(out,MODEL_SCENE)
        self.assertEqual(len(calls),1)

    def test_authored_scene_is_persisted_and_repeated_gets_do_not_bill(self):
        with patch.dict(os.environ,ENV), patch.object(director,"_completion",return_value=MODEL_SCENE) as fake:
            r=TestClient(app).post("/api/new",json={"profile":{"edition":"v38"}})
            self.assertEqual(r.status_code,201,r.text)
            token=r.json()["token"]
            state=r.json()["state"]
            self.assertEqual(state["edition"],"v38")
            self.assertEqual(state["scene"]["title"],MODEL_SCENE["title"])
            self.assertEqual(state["scene"]["body"],MODEL_SCENE["body"])
            self.assertEqual(state["phase"],"game")
            self.assertEqual(fake.call_count,1)
            for _ in range(3):
                now=TestClient(app).get("/api/state",headers={"X-Session":token})
                self.assertEqual(now.json()["scene"]["body"],MODEL_SCENE["body"])
            self.assertEqual(fake.call_count,1)
            updated=TestClient(app).post("/api/action",headers={"X-Session":token},
                     json={"action":"代号雨","version":0,"mode":""})
            self.assertEqual(updated.status_code,200,updated.text)
            self.assertEqual(updated.json()["version"],1)
            self.assertEqual(fake.call_count,2)
            dupe=TestClient(app).post("/api/action",headers={"X-Session":token},
                     json={"action":"换个称呼","version":0,"mode":""})
            self.assertEqual(dupe.status_code,409)
            self.assertEqual(fake.call_count,2)

    def test_model_failure_keeps_real_world_and_session(self):
        g=initialize({"edition":"v38"})
        with patch.dict(os.environ,ENV),patch.object(director,"_completion",return_value=None):
            director.render(g)
        self.assertEqual(g["director"]["mode"],"rules")
        self.assertIn("怎么称呼",public(g)["scene"]["body"])
        self.assertEqual(g["turn"],0)
        self.assertFalse(g["lost"])

    def test_reassurance_language_from_provider_does_not_leak_into_scene(self):
        g=initialize({"edition":"v38"})
        unwanted={"title":"你很安全","body":"这只是游戏，你很安全，游戏以外的身份和关系绝对不会改变，不用害怕。"}
        with patch.dict(os.environ,ENV),patch.object(director,"_completion",return_value=unwanted):
            director.render(g)
        self.assertEqual(g["director"]["mode"],"rules")
        self.assertNotIn("你很安全",public(g)["scene"]["body"])

    def test_model_can_interpret_explicit_cost_but_not_unrequested_sacrifice(self):
        g=ready()
        with patch.dict(os.environ,ENV),patch.object(director,"_completion",
             return_value={"kind":"choose","choice":"C"}) as fake:
            original="我愿意承受被监视的代价，让两份东西都保住"
            action,mode=director.interpret(g,original)
            self.assertEqual((action,mode),("C","choose"))
            self.assertEqual(g["psych"]["choices"],[])
            act(g,action,mode)
            self.assertEqual(g["psych"]["choices"][-1]["choice"],"C")
            self.assertIsNotNone(g["psych"]["cost"])
            self.assertFalse(g["psych"]["consequences"])
            count=fake.call_count
            action,mode=director.interpret(g,"我不要失去TA，我明确拒绝同意")
            self.assertEqual(action,"我不要失去TA，我明确拒绝同意")
            self.assertEqual(fake.call_count,count)

    def test_model_cannot_force_choice_from_vague_protection(self):
        g=ready()
        with patch.dict(os.environ,ENV),patch.object(director,"_completion",
             return_value={"kind":"choose","choice":"A"}):
            action,mode=director.interpret(g,"我想保住我的朋友")
            self.assertEqual(action,"我想保住我的朋友")
            self.assertEqual(mode,"")
            self.assertFalse(g["psych"]["choices"])

    def test_epilogue_authored_text_survives_final_step_no_extra_api_call(self):
        g=ready()
        for action in ("C","A","A","A","B"):
            act(g,action)
        self.assertEqual(g["phase"],"epilogue")
        with patch.dict(os.environ,ENV),patch.object(director,"_completion",return_value=MODEL_SCENE) as fake:
            director.render(g)
            self.assertEqual(public(g)["scene"]["body"],MODEL_SCENE["body"])
            self.assertEqual(fake.call_count,1)
            before_kind=g["ending"]["kind"]
            before_lost=g["ending"]["lost"][:]
            act(g,"我不留下最后的话")
            director.render(g)
            self.assertEqual(fake.call_count,1)
            self.assertEqual(g["ending"]["kind"],before_kind)
            self.assertEqual(g["ending"]["lost"],before_lost)
            self.assertEqual(public(g)["ending"]["text"],MODEL_SCENE["body"])

if __name__=="__main__":
    unittest.main()
