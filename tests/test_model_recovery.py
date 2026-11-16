"""Regression tests for DeepSeek latency and resumable AI-player actions."""
import json
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

import horror_director
from app import app


PLAN={
    "mode":"smalltalk",
    "focus":"a",
    "hook_id":"",
    "question":"在开始之前，怎么称呼你比较合适？"
}


class _Response:
    def __init__(self,content=None,finish_reason="stop",status=200):
        self.status_code=status
        self.headers={}
        self._content=content
        self._finish_reason=finish_reason

    def raise_for_status(self):
        if self.status_code>=400:
            request=httpx.Request("POST","https://api.deepseek.com/chat/completions")
            response=httpx.Response(self.status_code,request=request)
            raise httpx.HTTPStatusError("provider status",request=request,response=response)

    def json(self):
        if self._content=="body_error":
            return {"error":{"type":"server_error","message":"redacted"}}
        if self._content=="malformed_response":
            raise json.JSONDecodeError("invalid response","",0)
        return {"choices":[{
            "finish_reason":self._finish_reason,
            "message":{"content":self._content}
        }]}


class _FakeClient:
    responses=[]
    payloads=[]
    timeouts=[]
    calls=0

    def __init__(self,*args,**kwargs):
        self.__class__.timeouts.append(kwargs.get("timeout"))

    def __enter__(self):
        return self

    def __exit__(self,*args):
        return False

    def post(self,url,headers,json):
        self.__class__.calls+=1
        self.__class__.payloads.append(json)
        item=self.__class__.responses.pop(0)
        if isinstance(item,BaseException):
            raise item
        return item

    @classmethod
    def reset(cls,responses):
        cls.responses=list(responses)
        cls.payloads=[]
        cls.timeouts=[]
        cls.calls=0


class DeepSeekTransportTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{
            "HORROR_LLM_API_KEY":"test-secret-never-log",
            "HORROR_LLM_MODEL":"deepseek-v4-pro",
            "HORROR_LLM_BASE_URL":"https://api.deepseek.com"
        })
        self.env.start()
        self.configured=patch.object(horror_director,"configured",return_value=True)
        self.endpoint=patch.object(horror_director,"_endpoint",
                                   return_value="https://api.deepseek.com/chat/completions")
        self.client=patch("httpx.Client",_FakeClient)
        self.sleep=patch.object(horror_director.time,"sleep")
        self.configured.start()
        self.endpoint.start()
        self.client.start()
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.client.stop()
        self.endpoint.stop()
        self.configured.stop()
        self.env.stop()

    def valid(self):
        return _Response(json.dumps(PLAN,ensure_ascii=False))

    def test_planning_uses_low_reasoning_and_retries_one_read_timeout(self):
        _FakeClient.reset([httpx.ReadTimeout("read timed out"),self.valid()])
        result=horror_director._completion([{"role":"system","content":"plan"}],420,fast=True)
        self.assertEqual(result,PLAN)
        self.assertEqual(_FakeClient.calls,2)
        self.assertEqual(_FakeClient.payloads[0]["reasoning_effort"],"low")
        self.assertEqual(_FakeClient.payloads[0]["max_tokens"],2048)
        self.assertEqual(_FakeClient.timeouts[0].read,38)

    def test_small_classifier_uses_nonthinking_mode_and_short_timeout(self):
        _FakeClient.reset([self.valid()])
        result=horror_director._completion([{"role":"system","content":"classify"}],190,fast=True)
        self.assertEqual(result,PLAN)
        self.assertEqual(_FakeClient.calls,1)
        self.assertEqual(_FakeClient.payloads[0]["reasoning_effort"],"none")
        self.assertEqual(_FakeClient.payloads[0]["max_tokens"],768)
        self.assertEqual(_FakeClient.timeouts[0].read,18)

    def test_blank_json_output_is_retried_once(self):
        _FakeClient.reset([_Response("   "),self.valid()])
        result=horror_director._completion([{"role":"system","content":"plan"}],420,fast=True)
        self.assertEqual(result,PLAN)
        self.assertEqual(_FakeClient.calls,2)

    def test_http_401_is_not_retried_and_secret_is_not_logged(self):
        _FakeClient.reset([_Response(status=401)])
        with self.assertLogs("the_descent.model",level="WARNING") as captured:
            result=horror_director._completion([{"role":"user","content":"private player text"}],420,fast=True)
        self.assertIsNone(result)
        self.assertEqual(_FakeClient.calls,1)
        joined="\n".join(captured.output)
        self.assertNotIn("test-secret-never-log",joined)
        self.assertNotIn("private player text",joined)

    def test_http_200_provider_error_body_is_retried_once(self):
        _FakeClient.reset([_Response("body_error"),self.valid()])
        result=horror_director._completion([{"role":"system","content":"plan"}],420,fast=True)
        self.assertEqual(result,PLAN)
        self.assertEqual(_FakeClient.calls,2)

    def test_malformed_http_json_is_retried_once(self):
        _FakeClient.reset([_Response("malformed_response"),self.valid()])
        result=horror_director._completion([{"role":"system","content":"plan"}],420,fast=True)
        self.assertEqual(result,PLAN)
        self.assertEqual(_FakeClient.calls,2)

    def test_length_truncation_is_classified_without_repeating_same_request(self):
        _FakeClient.reset([_Response("{}",finish_reason="length")])
        with self.assertLogs("the_descent.model",level="WARNING") as captured:
            result=horror_director._completion([{"role":"system","content":"plan"}],420,fast=True)
        self.assertIsNone(result)
        self.assertEqual(_FakeClient.calls,1)
        self.assertIn("category=truncated","\n".join(captured.output))


class AIActionRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_failed_planning_does_not_advance_version_and_same_action_can_retry(self):
        from unittest.mock import patch as local_patch
        with local_patch("horror_director.configured",return_value=True), \
             local_patch("horror_planner.create",side_effect=[
                 PLAN,
                 RuntimeError("temporary planner timeout"),
                 PLAN
             ]) as create:
            started=self.client.get("/ai/start",params={"agree":"1","model":"1"})
            self.assertEqual(started.status_code,200,started.text)
            import re
            sid=re.search(r"会话号：([A-Za-z0-9_-]{32,100})",started.text).group(1)

            failed=self.client.get("/ai/action",params={
                "sid":sid,"v":0,"text":"叫我恢复测试玩家"
            })
            self.assertEqual(failed.status_code,503)
            self.assertIn("本轮没有提交",failed.text)
            self.assertIn("本轮版本：0",failed.text)

            retried=self.client.get("/ai/action",params={
                "sid":sid,"v":0,"text":"叫我恢复测试玩家"
            })
            self.assertEqual(retried.status_code,200,retried.text)
            self.assertIn("本轮版本：1",retried.text)
            self.assertEqual(create.call_count,3)

            duplicate=self.client.get("/ai/action",params={
                "sid":sid,"v":0,"text":"叫我恢复测试玩家"
            })
            self.assertEqual(duplicate.status_code,200)
            self.assertIn("已经过期",duplicate.text)
            self.assertIn("本轮版本：1",duplicate.text)


if __name__=="__main__":
    unittest.main()
