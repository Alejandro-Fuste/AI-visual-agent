from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScreenElement:
    element_id: int
    text: str
    type: str
    bbox: List[int]
    center: List[int]
    confidence: float


@dataclass
class PlannedAction:
    tool: str
    coordinates: Optional[List[int]] = None
    element_id: Optional[int] = None
    value: Optional[str] = None
    keys: Optional[List[str]] = None
    explanation: Optional[str] = None
    bbox: Optional[List[int]] = None
    amount: Optional[int] = None
    wait_seconds: Optional[float] = None


@dataclass
class PlannerResponse:
    thinking: str
    actions: List[PlannedAction] = field(default_factory=list)
    should_continue: bool = False
    needs_user_input: bool = False
    user_question: Optional[str] = None


@dataclass
class AgentResult:
    status: str
    final_message: str
    actions: List[Dict[str, Any]]
    screenshots: List[str]
    elements: List[Dict[str, Any]]
    plan: Dict[str, Any]
    log_path: str
    pending_question: Optional[str] = None

