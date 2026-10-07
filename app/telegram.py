from __future__ import annotations

import logging
import threading
from typing import Any, Callable

import httpx

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE = 4000


class TelegramBot:
    def __init__(self, token: str, allowed_chat_id: str, on_command: Callable[[str, str], str | None]):
        self.token = token
        self.allowed_chat_id = allowed_chat_id
        self.on_command = on_command
        self._offset = 0

    def _request(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = TELEGRAM_API.format(token=self.token, method=method)
        with httpx.Client(timeout=35) as client:
            response = client.post(url, json=payload or {})
            response.raise_for_status()
            body = response.json()
        if not body.get("ok"):
            raise RuntimeError(body)
        return body

    def send(self, chat_id: str | int, text: str) -> None:
        if not self.token or not chat_id:
            log.warning("Telegram is not configured, skip send")
            return
        chunks = _split_message(text)
        for chunk in chunks:
            self._request(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )

    def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("edited_message") or {}
        text = str(message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        if not text or not chat_id:
            return
        if self.allowed_chat_id and chat_id != self.allowed_chat_id:
            self.send(chat_id, "Нет доступа.")
            return
        reply = self.on_command(chat_id, text)
        if reply:
            self.send(chat_id, reply)

    def poll_forever(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                body = self._request(
                    "getUpdates",
                    {"offset": self._offset, "timeout": 25, "allowed_updates": ["message"]},
                )
                for update in body.get("result") or []:
                    self._offset = int(update["update_id"]) + 1
                    try:
                        self.handle_update(update)
                    except Exception:
                        log.exception("Failed to handle Telegram update")
            except Exception:
                log.exception("Telegram polling error")
                if stop.wait(3):
                    break


def _split_message(text: str) -> list[str]:
    if len(text) <= MAX_MESSAGE:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for block in text.split("\n\n"):
        extra = len(block) + (2 if current else 0)
        if current and size + extra > MAX_MESSAGE:
            chunks.append("\n\n".join(current))
            current = [block]
            size = len(block)
        else:
            current.append(block)
            size += extra
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def start_polling(bot: TelegramBot, stop: threading.Event) -> threading.Thread:
    thread = threading.Thread(target=bot.poll_forever, args=(stop,), daemon=True, name="telegram-poll")
    thread.start()
    return thread
