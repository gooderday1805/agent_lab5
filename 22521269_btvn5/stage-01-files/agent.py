"""LangChain agent của stage 01: list_files, read_file, write_file."""

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI

from config import MODEL_CALL_LIMIT, TOOL_CALL_LIMIT, Settings
from observer import ObserverMiddleware
from prompts import build_system_prompt
from tools import list_files, read_file, write_file

TOOLS = [list_files, read_file, write_file]

EXTRA_CONTENT_KEY = "tool_call_extra_content"


class ToolCallExtrasChatOpenAI(ChatOpenAI):
    """ChatOpenAI giữ lại tool_calls[].extra_content qua các lượt gọi model.

    Gemini 3.x (endpoint OpenAI-compatible) trả thought_signature trong extra_content của mỗi tool call
    và bắt buộc gửi lại ở request sau; ChatOpenAI mặc định bỏ trường này nên lượt thứ hai lỗi 400.
    Endpoint không trả extra_content thì class này không thay đổi gì.
    """

    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        response_dict = response if isinstance(response, dict) else response.model_dump(warnings=False)
        for generation, choice in zip(result.generations, response_dict.get("choices") or []):
            tool_calls = (choice.get("message") or {}).get("tool_calls") or []
            extras = {tc["id"]: tc["extra_content"] for tc in tool_calls if tc.get("extra_content")}
            if extras:
                generation.message.additional_kwargs[EXTRA_CONTENT_KEY] = extras
        return result

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        extras = {}
        for message in self._convert_input(input_).to_messages():
            extras.update(message.additional_kwargs.get(EXTRA_CONTENT_KEY) or {})
        if extras:
            for message in payload.get("messages", []):
                for tool_call in message.get("tool_calls") or []:
                    if tool_call.get("id") in extras:
                        tool_call["extra_content"] = extras[tool_call["id"]]
        return payload


def build_model(settings: Settings) -> ChatOpenAI:
    kwargs = {"model": settings.model_name, "api_key": settings.api_key}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return ToolCallExtrasChatOpenAI(**kwargs)


def system_prompt() -> str:
    return build_system_prompt()


def capabilities() -> dict:
    return {"tools": [t.name for t in TOOLS], "skills": [], "skill_diagnostics": []}


def build_agent(model):
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=system_prompt(),
        middleware=[
            ModelCallLimitMiddleware(run_limit=MODEL_CALL_LIMIT, exit_behavior="end"),
            ToolCallLimitMiddleware(run_limit=TOOL_CALL_LIMIT),
            ObserverMiddleware(),  # cuối danh sách = sát model/tool invocation nhất
        ],
    )
