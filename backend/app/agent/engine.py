from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_tools import ActionRecord, AgentToolbox
from omniparser_tool import OmniParserClient, OmniParserError

from app.agent.models import AgentResult, PlannedAction
from app.agent.qwen_client import QwenPlanner, QwenPlannerError


class VisualAgentEngine:
    def __init__(
        self,
        run_id: str,
        *,
        screenshot_dir: Path,
        log_dir: Path,
        max_iterations: int,
        enable_overlay: bool,
        dry_run: bool,
        omniparser_url: str,
        omniparser_token: str,
        openai_api_key: str,
        openai_api_base: str,
        openai_model: str,
        openai_temperature: float,
        action_pause: float = 0.35,
    ) -> None:
        self.run_id = run_id
        self.max_iterations = max_iterations
        self.action_pause = max(action_pause, 0.0)
        log_dir.mkdir(parents=True, exist_ok=True)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "actions.log"
        self.toolbox = AgentToolbox(
            log_file=log_file,
            screenshot_dir=screenshot_dir,
            enable_overlay=enable_overlay,
            dry_run=dry_run,
        )
        self.plan_log_dir = (log_dir / "plans").resolve()
        self.plan_log_dir.mkdir(parents=True, exist_ok=True)
        self.omniparser = OmniParserClient(api_url=omniparser_url, api_token=omniparser_token)
        self.planner = QwenPlanner(
            api_key=openai_api_key,
            api_base=openai_api_base,
            model=openai_model,
            temperature=openai_temperature,
        )
        self.log_file = log_file

    def run(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        clarifications: Optional[List[str]] = None,
    ) -> AgentResult:
        clarifications = clarifications or []
        screenshots: List[str] = []
        action_history: List[Dict[str, Any]] = []
        latest_elements: List[Dict[str, Any]] = []
        plan_payload: Dict[str, Any] = {}

        start_record = ActionRecord(
            action="info",
            message="User clicked Go on the Visual Agent panel. Ignore that panel and perform the requested task directly.",
            success=True,
        )
        logged_start = self.toolbox.log_action(start_record)
        action_history.append(logged_start.to_dict())

        instruction = self._compose_instruction(prompt, clarifications)
        screenshot_path = Path(file_path) if file_path else None
        if screenshot_path is None:
            shot = self.toolbox.take_screenshot(f"run_{self.run_id}_start")
            screenshot_path = Path(shot.metadata.get("path"))
            screenshots.append(screenshot_path.as_posix())
        else:
            screenshots.append(screenshot_path.as_posix())

        try:
            for iteration in range(self.max_iterations):
                try:
                    perception = self.omniparser.analyze(screenshot_path)
                except (OmniParserError, FileNotFoundError) as exc:
                    raise RuntimeError(f"Perception stage failed: {exc}") from exc
                latest_elements = perception.get("elements", [])

                try:
                    planner_response = self.planner.plan_actions(
                        instruction,
                        screenshot_path,
                        latest_elements,
                        action_history,
                        omniparser_payload=perception,
                    )
                except QwenPlannerError as exc:
                    raise RuntimeError(f"Planner failed: {exc}") from exc
                plan_payload = {
                    "thinking": planner_response.thinking,
                    "should_continue": planner_response.should_continue,
                    "needs_user_input": planner_response.needs_user_input,
                    "actions": [action.__dict__ for action in planner_response.actions],
                }
                self._write_plan_log(iteration, plan_payload)

                if planner_response.needs_user_input:
                    return AgentResult(
                        status="needs_input",
                        final_message=planner_response.thinking,
                        actions=action_history,
                        screenshots=screenshots,
                        elements=latest_elements,
                        plan=plan_payload,
                        log_path=str(self.log_file),
                        pending_question=planner_response.user_question,
                    )

                executed = self._execute_actions(planner_response.actions, latest_elements)
                action_history.extend(executed)
                if self.action_pause:
                    time.sleep(self.action_pause)

                if not planner_response.should_continue:
                    break

                shot = self.toolbox.take_screenshot(f"run_{self.run_id}_{iteration}")
                next_path = shot.metadata.get("path")
                if next_path:
                    screenshot_path = Path(next_path)
                    screenshots.append(screenshot_path.as_posix())
                else:
                    break

            final_message = plan_payload.get("thinking", "Action plan completed")
            return AgentResult(
                status="success",
                final_message=final_message,
                actions=action_history,
                screenshots=screenshots,
                elements=latest_elements,
                plan=plan_payload,
                log_path=str(self.log_file),
            )
        finally:
            self.toolbox.shutdown()

    def _execute_actions(self, actions: List[PlannedAction], elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        executed: List[Dict[str, Any]] = []
        element_lookup = {elem.get("element_id"): elem for elem in elements}
        for action in actions:
            record: Optional[ActionRecord] = None
            try:
                if action.tool == "click":
                    x = y = None
                    if action.coordinates:
                        x, y = action.coordinates[0], action.coordinates[1]
                    elif action.element_id and action.element_id in element_lookup:
                        bbox = element_lookup[action.element_id].get("bbox") or []
                        if len(bbox) == 4:
                            x = int((bbox[0] + bbox[2]) / 2)
                            y = int((bbox[1] + bbox[3]) / 2)
                    if x is None or y is None:
                        raise ValueError("Click action missing coordinates and resolvable element_id")
                    record = self.toolbox.click(
                        x,
                        y,
                        explanation=action.explanation,
                        bbox=tuple(action.bbox) if action.bbox else None,
                    )
                elif action.tool == "type" and action.value is not None:
                    x = action.coordinates[0] if action.coordinates else None
                    y = action.coordinates[1] if action.coordinates else None
                    record = self.toolbox.type_text(
                        x,
                        y,
                        text=str(action.value),
                        explanation=action.explanation,
                    )
                elif action.tool == "scroll" and action.amount:
                    record = self.toolbox.scroll(action.amount, explanation=action.explanation)
                elif action.tool == "wait" and action.wait_seconds:
                    record = self.toolbox.wait(action.wait_seconds, explanation=action.explanation)
                elif action.tool == "annotate" and action.bbox and action.explanation:
                    record = self.toolbox.annotate(tuple(action.bbox), action.explanation)
                elif action.tool in {"shortcut", "hotkey"}:
                    key_sequence: List[str] = action.keys or ([] if action.value is None else [part.strip() for part in str(action.value).split("+")])
                    record = self.toolbox.shortcut(key_sequence, explanation=action.explanation)
                elif action.tool == "screenshot":
                    record = self.toolbox.take_screenshot(f"run_{self.run_id}_step")
                else:
                    record = ActionRecord(action=action.tool, message=action.explanation or "No-op requested", success=True)
                    self.toolbox.log_action(record)
            except Exception as exc:
                record = ActionRecord(
                    action=action.tool,
                    message=action.explanation or "Action failed",
                    success=False,
                    error=str(exc),
                )
                self.toolbox.log_action(record)
            executed.append(record.to_dict())
            if self.action_pause:
                time.sleep(self.action_pause)
        return executed

    def _compose_instruction(self, prompt: str, clarifications: List[str]) -> str:
        prompt = prompt.strip()
        if not clarifications:
            return prompt
        clar_text = "\n".join(f"- {item}" for item in clarifications)
        return f"{prompt}\n\nAdditional details from user:\n{clar_text}"

    def _write_plan_log(self, iteration: int, plan_payload: Dict[str, Any]) -> None:
        try:
            plan_path = self.plan_log_dir / f"plan_iter_{iteration + 1}.json"
            with plan_path.open("w", encoding="utf-8") as handle:
                json.dump(plan_payload, handle, indent=2)
        except Exception:
            pass

