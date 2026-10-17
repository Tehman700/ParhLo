from app.services.llm import LLMReply, ToolCall, parse_json


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "llm_configured": False}


def test_config_lists_features_and_tools(client):
    data = client.get("/api/config").json()
    assert data["features"] == {"rag": True, "ml": True, "vision": True}
    assert {"calculator", "query_database", "analyze_csv", "search_documents"} <= set(data["tools"])
    assert "api_key" not in str(data).lower()


def test_chat_without_key_returns_503(client):
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 503
    assert "LLM_API_KEY" in r.json()["detail"]


def test_chat_with_fake_llm(client, fake_llm):
    fake = fake_llm(LLMReply(content="Hi there!", model="fake-model"))
    r = client.post("/api/chat", json={"system": "Be brief", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    assert r.json()["reply"] == "Hi there!"
    assert fake.calls[0]["messages"][0] == {"role": "system", "content": "Be brief"}


def test_chat_json_mode(client, fake_llm):
    fake_llm(LLMReply(content='```json\n{"sentiment": "positive"}\n```', model="fake"))
    r = client.post("/api/chat", json={"json_mode": True, "messages": [{"role": "user", "content": "x"}]})
    assert r.json()["data"] == {"sentiment": "positive"}


def test_chat_stream(client, fake_llm):
    fake_llm()
    r = client.post("/api/chat/stream", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    assert '"delta": "Hello"' in r.text and '"done": true' in r.text


def test_parse_json_tolerates_prose():
    assert parse_json('Sure! {"a": 1} hope that helps') == {"a": 1}


def test_agent_runs_tool_then_answers(client, fake_llm):
    fake = fake_llm(
        LLMReply(content=None, tool_calls=[ToolCall("c1", "calculator", '{"expression": "6*7"}')]),
        LLMReply(content="The answer is 42.", model="fake"),
    )
    r = client.post("/api/agent/run", json={"message": "what is 6*7?"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["answer"] == "The answer is 42."
    assert data["steps"][0]["tool"] == "calculator"
    assert data["steps"][0]["result"]["result"] == 42
    assert data["steps"][0]["duration_ms"] >= 0
    # The tool result was fed back to the model.
    tool_msg = fake.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and "42" in tool_msg["content"]


def test_agent_records_tool_errors(client, fake_llm):
    fake_llm(
        LLMReply(content=None, tool_calls=[ToolCall("c1", "query_database", '{"sql": "DROP TABLE orders"}')]),
        LLMReply(content="I can't do that.", model="fake"),
    )
    data = client.post("/api/agent/run", json={"message": "drop orders"}).json()
    assert "Only a single SELECT" in data["steps"][0]["error"]


def test_agent_stops_at_max_iterations(client, fake_llm):
    loop = LLMReply(content=None, tool_calls=[ToolCall("c", "calculator", '{"expression": "1+1"}')])
    fake_llm(loop, loop, LLMReply(content="Final.", model="fake"))
    data = client.post("/api/agent/run", json={"message": "loop", "max_iterations": 2}).json()
    assert data["stopped_reason"] == "max_iterations"
    assert data["answer"] == "Final." and len(data["steps"]) == 2
