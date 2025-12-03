from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_tools import ActionRecord, AgentToolbox
from omniparser_tool import OmniParserClient, OmniParserError, draw_omniparser_boxes

from app.agent.models import AgentResult, PlannedAction
from app.agent.qwen_client import QwenPlanner, QwenPlannerError
from app.config import settings


# Developed by Rodrigo Vena - Architecture and Flow Control
# Central controller that manages the data pipeline between perception (OmniParser) and reasoning (LLM/VLM).
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
        self.omniparser_debug_dir = (log_dir / "omniparser").resolve()
        self.omniparser_debug_dir.mkdir(parents=True, exist_ok=True)
        self.nav_hint_file = settings.NAV_HINT_FILE
        self.omniparser = OmniParserClient(api_url=omniparser_url, api_token=omniparser_token)
        self.planner = QwenPlanner(
            api_key=openai_api_key,
            api_base=openai_api_base,
            model=openai_model,
            temperature=openai_temperature,
        )
        self.log_file = log_file
        self.nav_hint_info = self._parse_nav_hint()

    def run(
        self,
        prompt: str,
        *,
        clarifications: Optional[List[str]] = None,
    ) -> AgentResult:
        clarifications = clarifications or []
        screenshots: List[str] = []
        action_history: List[Dict[str, Any]] = []
        latest_elements: List[Dict[str, Any]] = []
        plan_payload: Dict[str, Any] = {}
        pending_perception: Optional[Dict[str, Any]] = None

        start_record = ActionRecord(
            action="info",
            message="User clicked Go on the Visual Agent panel. Ignore that panel and perform the requested task directly.",
            success=True,
        )
        logged_start = self.toolbox.log_action(start_record)
        action_history.append(logged_start.to_dict())

        nav_hint = self._nav_hint_text()
        instruction = self._compose_instruction(prompt, clarifications, nav_hint)
        shot = self.toolbox.take_screenshot(f"run_{self.run_id}_start")
        screenshot_path = Path(shot.metadata.get("path"))
        screenshots.append(screenshot_path.as_posix())

        try:
            for iteration in range(self.max_iterations):
                # Clear overlays at the beginning of each iteration to avoid cluttering screenshots
                self.toolbox.clear_overlay()
                try:
                    if pending_perception is not None:
                        perception = pending_perception
                        pending_perception = None
                    else:
                        perception = self.omniparser.analyze(screenshot_path)
                except (OmniParserError, FileNotFoundError) as exc:
                    raise RuntimeError(f"Perception stage failed: {exc}") from exc
                latest_elements = perception.get("elements", [])
                self._write_omniparser_debug(screenshot_path, latest_elements, iteration, prefix="pre")
                before_elements = latest_elements.copy()

                try:
                    planner_response = self.planner.plan_actions(
                        instruction,
                        screenshot_path,
                        latest_elements,
                        action_history,
                        omniparser_payload=perception,
                        navigation_hint=nav_hint,
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

                # Clear any visual annotations before capturing verification screenshots
                self.toolbox.clear_overlay()
                post_shot = self.toolbox.take_screenshot(f"run_{self.run_id}_{iteration}_post")
                post_path = post_shot.metadata.get("path")
                if not post_path:
                    raise RuntimeError("Failed to capture verification screenshot")
                screenshot_path = Path(post_path)
                screenshots.append(screenshot_path.as_posix())

                try:
                    post_perception = self.omniparser.analyze(screenshot_path)
                except (OmniParserError, FileNotFoundError) as exc:
                    raise RuntimeError(f"Perception verification failed: {exc}") from exc

                pending_perception = post_perception
                after_elements = post_perception.get("elements", [])
                self._write_omniparser_debug(screenshot_path, after_elements, iteration, prefix="post")
                latest_elements = after_elements

                significant_actions = any(a.tool not in {"wait", "screenshot", "annotate"} for a in planner_response.actions)
                state_changed = self._state_changed(before_elements, after_elements)
                if significant_actions and not state_changed:
                    info_record = self.toolbox.log_action(
                        ActionRecord(
                            action="info",
                            message="Previous plan produced no visible change; retrying with a different approach.",
                        )
                    )
                    action_history.append(info_record.to_dict())
                    planner_response.should_continue = True
                    plan_payload["state_change_detected"] = False
                else:
                    plan_payload["state_change_detected"] = True

                if not planner_response.should_continue:
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
            if settings.AGENT_RETURN_TO_FRONTEND:
                self._return_to_frontend()
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

    def _compose_instruction(self, prompt: str, clarifications: List[str], nav_hint: str) -> str:
        prompt = prompt.strip()
        parts = [prompt]
        if nav_hint:
            parts.append(f"Navigation hint: {nav_hint}")
        if clarifications:
            clar_text = "\n".join(f"- {item}" for item in clarifications)
            parts.append(f"Additional details from user:\n{clar_text}")
        return "\n\n".join(parts)

    def _write_plan_log(self, iteration: int, plan_payload: Dict[str, Any]) -> None:
        try:
            plan_path = self.plan_log_dir / f"plan_iter_{iteration + 1}.json"
            with plan_path.open("w", encoding="utf-8") as handle:
                json.dump(plan_payload, handle, indent=2)
        except Exception:
            pass

    def _state_changed(self, before: List[Dict[str, Any]], after: List[Dict[str, Any]]) -> bool:
        def summarize(elements: List[Dict[str, Any]]) -> set[tuple[str, tuple[int, ...]]]:
            summary = set()
            for elem in elements[:80]:
                text = (elem.get("text") or "").strip()
                bbox = elem.get("bbox") or []
                bbox_tuple = tuple(int(x) for x in bbox[:4])
                summary.add((text, bbox_tuple))
            return summary

        before_summary = summarize(before)
        after_summary = summarize(after)
        return before_summary != after_summary

    def _write_omniparser_debug(self, screenshot_path: Path, elements: List[Dict[str, Any]], iteration: int, prefix: str) -> None:
        try:
            out_path = self.omniparser_debug_dir / f"{prefix}_iter_{iteration + 1}.png"
            draw_omniparser_boxes(screenshot_path, elements, out_path)
        except Exception:
            pass

    def _nav_hint_text(self) -> str:
        parts = []
        for key, val in self.nav_hint_info.items():
            parts.append(f"{key}={val}")
        return "; ".join(parts)

    def _parse_nav_hint(self) -> Dict[str, str]:
        data: Dict[str, str] = {}
        try:
            if self.nav_hint_file.exists():
                for line in self.nav_hint_file.read_text(encoding="utf-8").splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        data[k.strip()] = v.strip()
        except Exception:
            pass
        if settings.AGENT_FRONTEND_URL and not data.get("frontend_url"):
            data["frontend_url"] = settings.AGENT_FRONTEND_URL
        if not data:
            data["browser_tab_title"] = "frontend"
        return data

    def _return_to_frontend(self) -> None:
        url = self.nav_hint_info.get("frontend_url") or settings.AGENT_FRONTEND_URL
        if not url:
            # Fall back to ctrl+tab to cycle; low-risk attempt to reach the frontend tab
            self.toolbox.shortcut(["ctrl", "tab"], "Cycle tabs to reach frontend UI")  # best-effort
            return
        # Use address bar focus and type the URL
        self.toolbox.shortcut(["ctrl", "l"], "Focus address bar to return to frontend UI")
        self.toolbox.type_text(None, None, url, "Navigate back to Visual Agent frontend")
        self.toolbox.shortcut(["enter"], "Open Visual Agent frontend")
        if self.action_pause:
            time.sleep(self.action_pause)
