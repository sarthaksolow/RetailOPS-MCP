import threading
from datetime import datetime
from typing import List, Dict, Any
from dashboard.services.llm_service import LLMService, CopilotResponse


class ChatService:
    """
    Manages conversational session history and live streaming between the user and RetailOps AI Copilot.
    """

    def __init__(self):
        self._llm = LLMService()
        self._history: List[Dict[str, Any]] = [
            {
                "role": "assistant",
                "text": "Hello! I am your RetailOps Operations Copilot. I communicate with our MCP service cluster to answer questions about live inventory, demand forecasts, supplier lead times, and replenishment decisions. Select an operational demo scenario below or ask a custom question.",
                "model_name": "RetailOps Initializer",
                "tools_used": ["Discovery: list_mcp_services"],
                "tool_traces": [],
                "is_streaming": False,
                "timestamp": datetime.now().strftime("%H:%M"),
            }
        ]
        self._streaming_active = False
        self._lock = threading.Lock()

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def is_streaming(self) -> bool:
        with self._lock:
            return self._streaming_active

    def start_streaming_query(self, user_text: str):
        """Immediately record user message and begin streaming assistant response in a background worker."""
        now_str = datetime.now().strftime("%H:%M")
        with self._lock:
            self._history.append({
                "role": "user",
                "text": user_text,
                "model_name": "Operator",
                "tools_used": [],
                "tool_traces": [],
                "is_streaming": False,
                "timestamp": now_str,
            })
            self._history.append({
                "role": "assistant",
                "text": "",
                "model_name": "Connecting to MCP...",
                "tools_used": [],
                "tool_traces": [],
                "is_streaming": True,
                "timestamp": now_str,
            })
            self._streaming_active = True

        worker = threading.Thread(target=self._stream_runner, args=(user_text,))
        worker.daemon = True
        worker.start()

    def _stream_runner(self, user_text: str):
        """Worker executing MCP tools and streaming tokens into the active message."""
        try:
            for event in self._llm.stream_query(user_text):
                with self._lock:
                    if not self._history:
                        break
                    target = self._history[-1]
                    if event["type"] == "telemetry":
                        target["tools_used"] = event["tools_used"]
                        target["tool_traces"] = event["tool_traces"]
                        target["model_name"] = "Synthesizing briefing..."
                    elif event["type"] == "token":
                        target["text"] += event["token"]
                        target["model_name"] = event.get("model_name", "OpenRouter Live Stream")
                    elif event["type"] == "done":
                        target["is_streaming"] = False
                        target["model_name"] = event.get("model_name", "OpenRouter")
        except Exception as e:
            with self._lock:
                if self._history:
                    self._history[-1]["text"] += f"\n\n[Notice: {e}]"
                    self._history[-1]["is_streaming"] = False
        finally:
            with self._lock:
                self._streaming_active = False
                if self._history:
                    self._history[-1]["is_streaming"] = False

    def send_message(self, user_text: str) -> CopilotResponse:
        """Synchronous message execution for testing or non-streaming workflows."""
        now_str = datetime.now().strftime("%H:%M")
        with self._lock:
            self._history.append({
                "role": "user",
                "text": user_text,
                "model_name": "Operator",
                "tools_used": [],
                "tool_traces": [],
                "is_streaming": False,
                "timestamp": now_str,
            })

        response = self._llm.process_query(user_text)

        with self._lock:
            self._history.append({
                "role": "assistant",
                "text": response.text,
                "model_name": response.model_name,
                "tools_used": response.tools_used,
                "tool_traces": response.tool_traces,
                "is_streaming": False,
                "timestamp": now_str,
            })

        return response

    def clear_history(self):
        with self._lock:
            self._streaming_active = False
            self._history = [self._history[0]]


