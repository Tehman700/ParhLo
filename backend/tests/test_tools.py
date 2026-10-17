import pytest

from app.tools import get_tool


def test_tool_schema_has_described_params(client):
    tools = {t["name"]: t for t in client.get("/api/agent/tools").json()}
    calc = tools["calculator"]["parameters"]
    assert calc["required"] == ["expression"]
    assert "description" in calc["properties"]["expression"]
    agg = tools["aggregate_csv"]["parameters"]["properties"]["agg"]
    assert agg["enum"] == ["sum", "mean", "count", "min", "max"]


@pytest.mark.parametrize("expr,expected", [("2+3*4", 14), ("sqrt(16) + 2**3", 12.0), ("round(pi, 2)", 3.14)])
def test_calculator(client, expr, expected):
    r = client.post("/api/agent/tools/calculator", json={"arguments": {"expression": expr}})
    assert r.json()["result"]["result"] == expected


def test_calculator_rejects_code(client):
    r = client.post("/api/agent/tools/calculator", json={"arguments": {"expression": "__import__('os')"}})
    assert r.json()["error"]


def test_database_tools(client):
    tables = client.post("/api/agent/tools/list_tables", json={}).json()["result"]
    assert set(tables) == {"customers", "orders", "products"}
    r = client.post("/api/agent/tools/query_database", json={"arguments": {
        "sql": "SELECT city, COUNT(*) AS n FROM customers GROUP BY city ORDER BY n DESC"
    }}).json()
    assert r["result"]["rows"][0]["n"] == 2


def test_database_is_read_only(client):
    r = client.post("/api/agent/tools/query_database", json={"arguments": {
        "sql": "WITH x AS (SELECT 1) DELETE FROM orders"
    }}).json()
    assert r["error"]


def test_csv_tools(client):
    prof = client.post("/api/agent/tools/analyze_csv", json={"arguments": {"filename": "churn.csv"}}).json()
    assert prof["result"]["rows"] == 400
    agg = client.post("/api/agent/tools/aggregate_csv", json={"arguments": {
        "filename": "sales.csv", "group_by": "product", "value_column": "revenue"
    }}).json()
    assert len(agg["result"]["rows"]) == 5


def test_unknown_tool_404(client):
    assert client.post("/api/agent/tools/nope", json={}).status_code == 404


async def test_tool_validation_error_is_captured():
    from app.tools import execute

    res = await execute("calculator", {})
    assert res.error and "expression" in res.error
    assert get_tool("calculator") is not None
