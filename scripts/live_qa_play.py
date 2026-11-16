# MODEL-SMOKE-CHECK-2
"""Short live model smoke. Only calls publicly exposed game routes; no secrets."""
import json,urllib.request,urllib.error,sys,time
ROOT="https://the-descent-game.onrender.com"

def call(path,method="GET",data=None,token=None):
    headers={"Accept":"application/json","User-Agent":"descent-live-smoke-qa/2"}
    payload=json.dumps(data,ensure_ascii=False).encode() if data is not None else None
    if payload is not None:headers["Content-Type"]="application/json"
    if token:headers["X-Session"]=token
    req=urllib.request.Request(ROOT+path,headers=headers,data=payload,method=method)
    with urllib.request.urlopen(req,timeout=120) as res:
        return json.loads(res.read().decode())

def run():
    health=call("/healthz")
    print("HEALTH",json.dumps(health,ensure_ascii=False),flush=True)
    session=call("/api/new","POST",{"profile":{"edition":"v39"}})
    token=session["token"]
    try:
        state=session["state"]
        for step,text in enumerate([None]):
            if step:
                state=call("/api/action","POST",{"action":text,"version":state["version"],"mode":""},token)
            detail=call("/api/export",token=token).get("narrative",{}).get("plan",{})
            print("CHECK",json.dumps({"step":step,"chapter":state["stage"],
              "question":(state["scene"]["body"] or "")[:160],
              "model_plan_accepted":detail.get("from_model"),
              "mode":detail.get("mode"),
              "replay_version":state["version"]},ensure_ascii=False),flush=True)
    finally:
        try:
            with urllib.request.urlopen(urllib.request.Request(ROOT+"/api/session",
                method="DELETE",headers={"X-Session":token}),timeout=25) as response:
                print("SESSION_REMOVED",response.status,flush=True)
        except Exception as exc:
            print("DELETE_FAILED",type(exc).__name__,flush=True)
if __name__=="__main__":run()
