"""Agent thật (create_agent + middleware) với mock model: tool trace và request snapshot."""

from langchain_core.messages import AIMessage, HumanMessage

import paths
from agent import TOOLS, ToolCallExtrasChatOpenAI, build_agent, system_prompt
from tests.conftest import ScriptedChatModel


def stream_events(agent, messages):
    events, new_messages = [], []
    for mode, chunk in agent.stream({"messages": messages}, stream_mode=["updates", "custom"]):
        if mode == "custom" and chunk.get("observer"):
            events.append(chunk)
        elif mode == "updates":
            for update in chunk.values():
                if isinstance(update, dict) and update.get("messages"):
                    new_messages.extend(update["messages"])
    return events, new_messages


def test_registered_tools():
    assert [t.name for t in TOOLS] == ["list_files", "read_file", "write_file"]


def test_read_then_write_with_parallel_calls_and_missing_file(lab_dirs):
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "read_file", "args": {"path": "data/weekly_notes.md"}, "id": "r1"},
                    {"name": "read_file", "args": {"path": "data/khong-co.md"}, "id": "r2"},
                ],
            ),
            AIMessage(content="", tool_calls=[{"name": "write_file", "args": {"path": "output/summary.md", "content": "# Tóm tắt"}, "id": "w1"}]),
            AIMessage(content="Đã ghi output/summary.md"),
        ]
    )
    events, new_messages = stream_events(build_agent(model), [HumanMessage(content="Đọc data/weekly_notes.md và ghi tóm tắt vào output/summary.md.")])

    kinds = [e["event"] for e in events]
    assert kinds.count("model_request") == 3
    assert kinds.count("tool_started") == 3 and kinds.count("tool_finished") == 3
    finished = {e["data"]["tool_call_id"]: e["data"] for e in events if e["event"] == "tool_finished"}
    assert finished["r1"]["result"]["ok"] is True and "Endpoint đăng nhập" in finished["r1"]["result"]["content"]
    assert finished["r2"]["result"]["error"]["code"] == "FILE_NOT_FOUND"
    assert finished["w1"]["result"] == {"ok": True, "path": "output/summary.md", "bytes": len("# Tóm tắt".encode()), "status": "created"}
    assert (paths.WORKSPACE_DIR / "output" / "summary.md").read_text(encoding="utf-8") == "# Tóm tắt"

    requests = [e["data"] for e in events if e["event"] == "model_request"]
    assert requests[0]["system_prompt"] == system_prompt()
    assert [t["name"] for t in requests[0]["tools"]] == ["list_files", "read_file", "write_file"]
    assert requests[0]["tools"][2]["parameters"]["required"] == ["path", "content"]
    second_roles = [m["role"] for m in requests[1]["messages"]]
    assert second_roles == ["user", "assistant", "tool", "tool"]
    assert {m["tool_call_id"] for m in requests[1]["messages"] if m["role"] == "tool"} == {"r1", "r2"}
    assert new_messages[-1].content == "Đã ghi output/summary.md"


def test_tool_call_extra_content_round_trip():
    # Gemini 3.x trả thought_signature trong extra_content và yêu cầu gửi lại ở request sau
    model = ToolCallExtrasChatOpenAI(model="m", api_key="k")
    extra = {"google": {"thought_signature": "sig"}}
    response = {
        "choices": [{
            "index": 0,
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "c1", "type": "function", "extra_content": extra,
                                "function": {"name": "list_files", "arguments": '{"path": "data"}'}}],
            },
        }],
    }
    ai = model._create_chat_result(response).generations[0].message
    payload = model._get_request_payload([HumanMessage(content="hi"), ai])
    assert payload["messages"][1]["tool_calls"][0]["extra_content"] == extra
    plain = model._get_request_payload([HumanMessage(content="hi"), AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "c2"}])])
    assert "extra_content" not in plain["messages"][1]["tool_calls"][0]
