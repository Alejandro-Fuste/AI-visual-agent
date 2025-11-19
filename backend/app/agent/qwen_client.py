from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI, OpenAIError

from .models import PlannedAction, PlannerResponse

RUN_ACTIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "run_desktop_actions",
        "description": "Plan the exact desktop actions to execute next. Always include at least one action.",
        "parameters": {
            "type": "object",
            "properties": {
                "thinking": {"type": "string", "description": "Concise reasoning for the next steps."},
                "should_continue": {"type": "boolean", "description": "True when another perception cycle is required."},
                "needs_user_input": {
                    "type": "boolean",
                    "description": "Only true when progress is impossible without clarification.",
                },
                "user_question": {
                    "type": ["string", "null"],
                    "description": "Question to show the user when needs_user_input is true.",
                },
                "actions": {
                    "type": "array",
                    "description": "Sequential actions to execute immediately.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "enum": ["click", "type", "scroll", "wait", "annotate", "screenshot", "shortcut"],
                            },
                            "explanation": {
                                "type": "string",
                                "description": "Why this action is required (shown in the UI log).",
                            },
                            "coordinates": {
                                "type": "array",
                                "description": "Pixel coordinates [x, y] for click/type actions.",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                            "element_id": {"type": ["integer", "null"], "description": "OmniParser element id if referenced."},
                            "value": {"type": ["string", "null"], "description": "Text to type or paste."},
                            "keys": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Keyboard combo for shortcut actions (e.g., [\"ctrl\", \"t\"]).",
                            },
                            "amount": {"type": ["integer", "null"], "description": "Scroll delta (positive=up, negative=down)."},
                            "wait_seconds": {"type": ["number", "null"], "description": "Duration for wait actions."},
                            "bbox": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 4,
                                "maxItems": 4,
                                "description": "Bounding box [x1,y1,x2,y2] for annotate actions.",
                            },
                        },
                        "required": ["tool", "explanation"],
                    },
                    "minItems": 1,
                },
            },
            "required": ["thinking", "should_continue", "needs_user_input", "actions"],
        },
    },
}


class GPTPlannerError(RuntimeError):
    pass


class GPTPlanner:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("QWEN_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_BASE_URL") or os.getenv("QWEN_API_BASE", "https://api.openai.com/v1")
        self.model = model or os.getenv("OPENAI_MODEL") or os.getenv("QWEN_MODEL", "gpt-4o-mini")
        if not self.api_key:
            raise GPTPlannerError("OPENAI_API_KEY is not configured")
        self.temperature = temperature
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)

    def plan_actions(
        self,
        instruction: str,
        screenshot_path: str | Path,
        elements: List[Dict[str, Any]],
        action_history: List[Dict[str, Any]],
        omniparser_payload: Optional[Dict[str, Any]] = None,
    ) -> PlannerResponse:
        image_b64 = self._encode_image(screenshot_path)
        history_text = self._history_to_text(action_history)
        elements_json = json.dumps(elements, ensure_ascii=False)

        element_chunks = self._chunk_text(elements_json)
        user_segments: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": "User request (include follow-up clarifications if provided):\n"
                f"{instruction}\n",
            },
            {
                "type": "text",
                "text": f"Recent action history (most recent last):\n{history_text or 'None yet.'}\n",
            },
            {
                "type": "text",
                "text": "Reminder: The Visual Agent launcher panel or modal in the screenshot is not part of the task. "
                "It simply shows status; never type into it, wait for it, or ask it for instructions. "
                "Ignore it completely and focus on the desktop/browser content behind it.",
            },
        ]

        for idx, chunk in enumerate(element_chunks, start=1):
            user_segments.append(
                {
                    "type": "text",
                    "text": f"OmniParser elements chunk {idx}/{len(element_chunks)}:\n{chunk}",
                }
            )

        system_prompt = (
            "You are Vision Form Agent, a careful desktop task planner.\n"
            "1. Inputs: latest screenshot (base64 image), parsed OmniParser elements array, "
            "user request, and up to 10 recent action logs.\n"
            "2. Goal: finish the user’s task exactly (form filling, text entry, navigation). "
            "Only propose actions that can be executed by the available toolbox.\n\n"
            "Tool usage:\n"
            "- Always call the run_desktop_actions tool. Every response must include at least one executable action. "
            "Insert a wait action if you need to pause.\n"
            "- Use keyboard shortcuts when faster (Ctrl+T, Ctrl+L, Ctrl+C/V, Alt+Tab, etc.).\n"
            "- Treat prior log entries like \"User clicked Go\" as confirmation that the Visual Agent panel has already been launched.\n"
            "- After every critical action (navigation, submit, open document), inspect the updated OmniParser context. "
            "If the screen still looks the same or the expected element is missing, try an alternative approach instead of declaring success.\n"
            "- Handle broad user requests independently—choose an appropriate search result or workflow without asking for preferences "
            "unless the user explicitly required a choice.\n"
            "- Prefer interacting with actual buttons/inputs rather than surrounding text labels; if text isn’t clickable, locate the nearest actionable element.\n"
            "- When a required form field (username, DOB, etc.) needs information the user has not provided, do not invent data—set needs_user_input=true and ask for it explicitly.\n"
            "- Ask for clarification only when the user’s request truly cannot be completed from the current UI.\n"
            "- Only set should_continue=false when the latest screenshot/analysis clearly shows the user’s goal is complete "
            "(e.g., logged-in dashboard visible, blank document loaded, item added to cart). If unsure, keep should_continue=true.\n"
        )

        user_message = {
            "role": "user",
            "content": [
                *user_segments,
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ],
        }

        messages = [
            {"role": "system", "content": system_prompt},
            user_message,
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=messages,
                tools=[RUN_ACTIONS_TOOL],
                tool_choice={"type": "function", "function": {"name": "run_desktop_actions"}},
            )
        except OpenAIError as exc:
            raise GPTPlannerError(f"OpenAI call failed: {exc}") from exc

        choice = completion.choices[0].message
        tool_calls = choice.tool_calls or []
        if not tool_calls:
            raise GPTPlannerError("Model response did not include the required run_desktop_actions tool call.")

        tool_call = tool_calls[0]
        try:
            function_args = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            raise GPTPlannerError(f"Tool arguments were not valid JSON: {tool_call.function.arguments}") from exc

        actions_data = function_args.get("actions", [])
        if not isinstance(actions_data, list) or not actions_data:
            raise GPTPlannerError("Tool call did not provide any actions.")

        actions: List[PlannedAction] = []
        for item in actions_data:
            if not isinstance(item, dict):
                continue
            actions.append(
                PlannedAction(
                    tool=item.get("tool", "log"),
                    coordinates=item.get("coordinates"),
                    element_id=item.get("element_id"),
                    value=item.get("value"),
                    keys=item.get("keys"),
                    explanation=item.get("explanation"),
                    bbox=item.get("bbox"),
                    amount=item.get("amount"),
                    wait_seconds=item.get("wait_seconds"),
                )
            )

        return PlannerResponse(
            thinking=function_args.get("thinking", choice.content or ""),
            actions=actions,
            should_continue=bool(function_args.get("should_continue")),
            needs_user_input=bool(function_args.get("needs_user_input")),
            user_question=function_args.get("user_question"),
        )

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

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 3500) -> List[str]:
        if not text:
            return []
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


# Backwards-compatible aliases
QwenPlannerError = GPTPlannerError
QwenPlanner = GPTPlanner
