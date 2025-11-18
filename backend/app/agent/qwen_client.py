from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .models import PlannedAction, PlannerResponse


class QwenPlannerError(RuntimeError):
    pass


class QwenPlanner:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.15,
        timeout: int = 90,
    ) -> None:
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        self.api_base = api_base or os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model or os.getenv("QWEN_MODEL", "qwen2.5-vl-7b-instruct")
        if not self.api_key:
            raise QwenPlannerError("QWEN_API_KEY is not configured")
        self.temperature = temperature
        self.timeout = timeout
        self.session = requests.Session()

    def plan_actions(
        self,
        instruction: str,
        screenshot_path: str | Path,
        elements: List[Dict[str, Any]],
        action_history: List[Dict[str, Any]],
    ) -> PlannerResponse:
        image_b64 = self._encode_image(screenshot_path)
        history_text = self._history_to_text(action_history)
        elements_json = json.dumps(elements[:60])

        user_prompt = (
            f"User request:\n{instruction}\n\n"
            f"Action history:\n{history_text or 'None yet.'}\n\n"
            "Parsed UI elements (trimmed to 60):\n"
            f"{elements_json}\n"
        )

        system_prompt = (
            "You are Vision Form Agent, a careful desktop task planner.\n"
            "1. Inputs: latest screenshot (base64 image), parsed OmniParser elements array, "
            "user request, and up to 10 recent action logs.\n"
            "2. Goal: finish the user’s task exactly (form filling, text entry, navigation). "
            "Only propose actions that can be executed by the available toolbox.\n\n"
            "Plan-format requirements:\n"
            "- Return JSON with keys: thinking (short reasoning), needs_user_input (bool), "
            "user_question (string|null), should_continue (bool), actions (array).\n"
            "- Each action object: tool (\"click\"|\"type\"|\"scroll\"|\"wait\"|"
            "\"annotate\"|\"screenshot\"|\"read_log\"|\"write_log\"), coordinates [x, y] "
            "when clicking/typing, bbox [x1,y1,x2,y2] for annotate, amount for scroll, "
            "value for text entry, explanation (1 sentence why this step is needed), "
            "element_id if referencing parsed elements.\n\n"
            "Guidelines:\n"
            "- Ground every coordinate, element_id, and field name in the provided elements JSON. "
            "Never invent values.\n"
            "- For form filling, type exactly the requested text and confirm caret placement before typing.\n"
            "- Use annotate to explain visual evidence when helpful.\n"
            "- Log important state transitions with write_log; consult prior context with read_log if you need to backtrack.\n"
            "- Ask for clarification (set needs_user_input=true and include user_question) when required data is missing.\n"
            "- Stop when the task is complete: set should_continue=false and leave remaining actions empty.\n\n"
            "Respond only with valid JSON matching this schema."
        )


        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            },
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        url = self._chat_url
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
        if response.status_code >= 400:
            raise QwenPlannerError(f"Qwen call failed: {response.status_code} {response.text}")

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            text_content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
        else:
            text_content = content

        return self._parse_response(text_content)

    @property
    def _chat_url(self) -> str:
        base = self.api_base.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def _encode_image(self, path: str | Path) -> str:
        with open(path, "rb") as handle:
            return base64.b64encode(handle.read()).decode("utf-8")

    def _history_to_text(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return ""
        lines = []
        for item in history[-10:]:
            action = item.get("action")
            message = item.get("message")
            success = item.get("success", True)
            lines.append(f"- {action}: {message} ({'ok' if success else 'failed'})")
        return "\n".join(lines)

    def _parse_response(self, text: str) -> PlannerResponse:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise QwenPlannerError(f"Planner did not return JSON: {text}") from exc

        actions_raw = parsed.get("actions", []) or []
        actions: List[PlannedAction] = []
        for item in actions_raw:
            if not isinstance(item, dict):
                continue
            actions.append(
                PlannedAction(
                    tool=item.get("tool", "log"),
                    coordinates=item.get("coordinates"),
                    element_id=item.get("element_id"),
                    value=item.get("value"),
                    explanation=item.get("explanation"),
                    bbox=item.get("bbox"),
                    amount=item.get("amount"),
                    wait_seconds=item.get("wait_seconds"),
                )
            )

        return PlannerResponse(
            thinking=parsed.get("thinking", ""),
            actions=actions,
            should_continue=bool(parsed.get("should_continue")),
            needs_user_input=bool(parsed.get("needs_user_input")),
            user_question=parsed.get("user_question"),
        )

