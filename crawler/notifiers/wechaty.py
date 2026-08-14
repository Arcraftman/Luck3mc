"""Wechaty-backed notifier for *real* personal-WeChat group messages.

WARNING — read before enabling
--------------------------------
Personal WeChat has **no official bot API**. This backend drives a real
personal WeChat account as a "bot" through Wechaty (https://wechaty.js.org),
which requires:

  1. ``pip install wechaty``  (Python binding; still experimental)
  2. A Wechaty **puppet** service token, e.g. ``padlocal``
     (``WECHATY_PUPPET_SERVICE_TOKEN=...``) — usually paid.
  3. Logging that account in once; automating a personal account carries
     **ban / compliance risk**. Treat as best-effort only.

Because of (3) this backend is NOT enabled by default. The recommended,
low-risk path for personal-WeChat alerts is the ``webhook`` backend with
Server酱 / pushplus (delivers to your personal WeChat as a service message).

This module is a scaffold: it imports lazily and degrades to a logged no-op
when ``wechaty`` is unavailable, so it never breaks the crawl. Wire the bot
connection (see the marked extension point) once a puppet service is set up.
"""

from __future__ import annotations

import logging

from .base import Notifier, NotifyMessage

logger = logging.getLogger(__name__)


class WechatyNotifier(Notifier):
    def __init__(self, token: str = "", room: str = "", timeout: float = 30.0):
        self.token = token
        self.room = room
        self.timeout = timeout
        self._warned = False

    def _ensure_ready(self) -> bool:
        """Return True only when a usable Wechaty client is available."""
        if self._warned:
            return False
        try:
            import wechaty  # noqa: F401  (import for side-effect / availability)
        except Exception:  # noqa: BLE001
            logger.error(
                "WechatyNotifier: `wechaty` package not installed. "
                "Personal-WeChat group send is unavailable. Recommended "
                "alternative: NOTIFY_BACKEND=webhook with Server酱/pushplus "
                "for personal-WeChat push."
            )
            self._warned = True
            return False
        logger.error(
            "WechatyNotifier: real group send requires a configured puppet "
            "service (WECHATY_PUPPET_SERVICE_TOKEN) and a logged-in account. "
            "See crawler/notifiers/wechaty.py for the extension point."
        )
        self._warned = True
        return False

    def send(self, message: NotifyMessage) -> bool:
        if not self._ensure_ready():
            return False
        # Extension point — once a puppet service + logged-in account exist:
        #     bot.room().say(message.render_text(), self.room)
        # The persistent bot client should be created lazily in _ensure_ready.
        return False
