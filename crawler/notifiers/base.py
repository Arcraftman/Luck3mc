"""Notification primitives shared by all backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NotifyMessage:
    """A single new-item alert delivered to an operator."""

    title: str
    url: str
    pub_date: str = ""
    source_site: str = ""
    summary: str = ""

    def render_text(self) -> str:
        lines = [f"【新政策】{self.title}"]
        if self.source_site:
            lines.append(f"来源：{self.source_site}")
        if self.pub_date:
            lines.append(f"发布日期：{self.pub_date}")
        lines.append(f"链接：{self.url}")
        if self.summary:
            lines.append("")
            lines.append(self.summary[:200])
        return "\n".join(lines)


class Notifier(ABC):
    """Something that can deliver a :class:`NotifyMessage`."""

    @abstractmethod
    def send(self, message: NotifyMessage) -> bool:
        """Deliver ``message``.

        Return ``True`` on success, ``False`` on failure. Implementations MUST
        never raise — a flaky notification must not crash the crawl.
        """

    def send_batch(self, messages) -> bool:
        ok = True
        for m in messages:
            ok = self.send(m) and ok
        return ok
