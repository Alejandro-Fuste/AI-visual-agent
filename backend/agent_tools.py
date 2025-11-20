from __future__ import annotations

"""Utilities for desktop automation with visual explanations."""

import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pyautogui
from PIL import Image
from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QScreen
from PyQt6.QtWidgets import QApplication, QMainWindow

pyautogui.FAILSAFE = False

Coordinate = Tuple[int, int]
BBox = Tuple[int, int, int, int]


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


@dataclass
class ActionRecord:
    action: str
    message: str
    coords: Optional[Coordinate] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    created_at: str = field(default_factory=_timestamp)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


class OverlayWindow(QMainWindow):
    """Transparent overlay used to draw action explanations."""

    def __init__(self):
        super().__init__()
        self.boxes: List[Tuple[QRect, QColor, int]] = []
        self.texts: List[Tuple[QPoint, str, QColor, int]] = []
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        screen_geometry = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen_geometry)

    def paintEvent(self, event):  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for rect, color, width in self.boxes:
            painter.setPen(QPen(color, width))
            painter.drawRect(rect)
        for point, text, color, font_size in self.texts:
            painter.setPen(QPen(color))
            font = QFont("Arial", font_size)
            painter.setFont(font)
            painter.drawText(point, text)

    def draw_box(self, x: int, y: int, width: int, height: int, color: QColor, line_width: int) -> None:
        self.boxes.append((QRect(x, y, width, height), color, line_width))
        self.update()

    def draw_text(self, x: int, y: int, text: str, color: QColor, font_size: int) -> None:
        self.texts.append((QPoint(x, y), text, color, font_size))
        self.update()

    def clear_visuals(self) -> None:
        self.boxes.clear()
        self.texts.clear()
        self.update()


def _overlay_worker(command_queue: "Queue[dict]") -> None:
    app = QApplication(sys.argv)
    overlay = OverlayWindow()
    overlay.show()

    def process_commands():
        while not command_queue.empty():
            command = command_queue.get()
            op = command.get("op")
            if op == "box":
                rect = command.get("rect", [0, 0, 0, 0])
                color = QColor(*command.get("color", (255, 0, 0, 200)))
                overlay.draw_box(rect[0], rect[1], rect[2], rect[3], color, command.get("width", 2))
            elif op == "text":
                point = command.get("point", [0, 0])
                color = QColor(*command.get("color", (0, 120, 255, 220)))
                overlay.draw_text(point[0], point[1], command.get("text", ""), color, command.get("size", 14))
            elif op == "clear":
                overlay.clear_visuals()
            elif op == "shutdown":
                overlay.close()
                app.quit()
                return

    timer = QTimer()
    timer.timeout.connect(process_commands)  # type: ignore[arg-type]
    timer.start(32)

    sys.exit(app.exec())


class OverlayController:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.process: Optional[Process] = None
        self.queue: Optional[Queue] = None
        if self.enabled:
            self.queue = Queue()
            self.process = Process(target=_overlay_worker, args=(self.queue,), daemon=True)
            self.process.start()

    def draw_box(self, rect: Sequence[int], color: Tuple[int, int, int, int] = (255, 0, 0, 200), width: int = 2) -> None:
        if not self.enabled or not self.queue:
            return
        self.queue.put({"op": "box", "rect": list(rect), "color": color, "width": width})

    def draw_text(self, point: Sequence[int], text: str, color: Tuple[int, int, int, int] = (0, 120, 255, 220), size: int = 14) -> None:
        if not self.enabled or not self.queue:
            return
        self.queue.put({"op": "text", "point": list(point), "text": text, "color": color, "size": size})

    def clear(self) -> None:
        if not self.enabled or not self.queue:
            return
        self.queue.put({"op": "clear"})

    def shutdown(self) -> None:
        if not self.enabled or not self.queue:
            return
        self.queue.put({"op": "shutdown"})
        if self.process:
            self.process.join(timeout=2)
        self.queue = None
        self.process = None


class ActionLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text("--- Agent Action Log ---\n", encoding="utf-8")

    def append(self, record: ActionRecord) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{record.created_at}] {record.action.upper()} - {record.message}\n")

    def read(self) -> str:
        return self.log_path.read_text(encoding="utf-8")


class AgentToolbox:
    """High-level helper used by the visual agent to act on the desktop."""

    def __init__(
        self,
        log_file: str | Path = "logs/actions.log",
        screenshot_dir: str | Path = "screenshots",
        enable_overlay: bool = True,
        dry_run: bool = False,
    ):
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.logger = ActionLogger(Path(log_file))
        self.overlay = OverlayController(enabled=enable_overlay)
        self.dry_run = dry_run
        self.history: List[ActionRecord] = []
        self._active_annotations = 0

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def log_action(self, record: ActionRecord) -> ActionRecord:
        self.logger.append(record)
        self.history.append(record)
        return record

    def click(self, x: int, y: int, explanation: Optional[str] = None, bbox: Optional[BBox] = None) -> ActionRecord:
        record = ActionRecord(action="click", message=explanation or f"Click at ({x}, {y})", coords=(x, y), metadata={"bbox": bbox})
        try:
            if bbox:
                rect = (bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
                self.overlay.draw_box(rect)
            if explanation:
                self.overlay.draw_text((x + 10, y + 10), explanation)
            if not self.dry_run:
                pyautogui.click(x, y)
        except Exception as exc:
            record.success = False
            record.error = str(exc)
        return self.log_action(record)

    def type_text(self, x: Optional[int], y: Optional[int], text: str, explanation: Optional[str] = None) -> ActionRecord:
        coords = (x, y) if x is not None and y is not None else None
        record = ActionRecord(action="type", message=explanation or f"Type '{text}'", coords=coords, metadata={"text": text})
        try:
            if not self.dry_run:
                if x is not None and y is not None:
                    pyautogui.click(x, y)
                    time.sleep(0.1)
                pyautogui.write(text, interval=0.05)
        except Exception as exc:
            record.success = False
            record.error = str(exc)
        return self.log_action(record)

    def scroll(self, amount: int, explanation: Optional[str] = None) -> ActionRecord:
        direction = "up" if amount > 0 else "down"
        record = ActionRecord(action="scroll", message=explanation or f"Scroll {direction} by {abs(amount)}", metadata={"amount": amount})
        try:
            if not self.dry_run:
                pyautogui.scroll(amount)
        except Exception as exc:
            record.success = False
            record.error = str(exc)
        return self.log_action(record)

    def wait(self, duration: float, explanation: Optional[str] = None) -> ActionRecord:
        record = ActionRecord(action="wait", message=explanation or f"Wait {duration:.2f}s", metadata={"duration": duration})
        try:
            if not self.dry_run:
                time.sleep(duration)
        except Exception as exc:
            record.success = False
            record.error = str(exc)
        return self.log_action(record)

    def shortcut(self, keys: Sequence[str], explanation: Optional[str] = None) -> ActionRecord:
        normalized = [str(key).strip() for key in keys if str(key).strip()]
        combo = " + ".join(normalized) if normalized else "shortcut"
        record = ActionRecord(action="shortcut", message=explanation or f"Press {combo}", metadata={"keys": normalized})
        try:
            if not self.dry_run and normalized:
                pyautogui.hotkey(*normalized)
        except Exception as exc:
            record.success = False
            record.error = str(exc)
        return self.log_action(record)

    def annotate(self, bbox: BBox, text: str, color: Tuple[int, int, int, int] = (0, 255, 0, 180)) -> ActionRecord:
        if self._active_annotations >= 3:
            self.clear_overlay()
        rect = (bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
        self.overlay.draw_box(rect, color)
        self.overlay.draw_text((bbox[0], max(bbox[1] - 20, 0)), text, color)
        record = ActionRecord(action="annotate", message=text, metadata={"bbox": bbox})
        self._active_annotations += 1
        return self.log_action(record)

    def clear_overlay(self) -> None:
        self.overlay.clear()
        self._active_annotations = 0

    def take_screenshot(self, label: str = "capture") -> ActionRecord:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = self.screenshot_dir / f"{label}_{timestamp}.png"
        record = ActionRecord(action="screenshot", message=f"Saved screenshot to {filename}")
        try:
            if not self.dry_run:
                image = pyautogui.screenshot()
                image.save(filename)
            else:
                Image.new("RGB", (200, 100), "gray").save(filename)
            record.metadata["path"] = str(filename)
        except Exception as exc:
            record.success = False
            record.error = str(exc)
        return self.log_action(record)

    def read_log(self) -> str:
        return self.logger.read()

    def to_json(self) -> str:
        return json.dumps([record.to_dict() for record in self.history], indent=2)

    def shutdown(self) -> None:
        self.overlay.shutdown()


if __name__ == "__main__":
    toolbox = AgentToolbox()
    toolbox.take_screenshot()
    toolbox.click(900, 500, "Focus username")
    toolbox.type_text(900, 500, "Jane Doe")
    toolbox.scroll(-400, "Look for submit button")
    toolbox.take_screenshot("after_scroll")
    toolbox.shutdown()
