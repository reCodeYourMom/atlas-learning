"""Emails transactionnels (Phase H) — adapter injectable, comme le rostering.

`EmailSender` (Protocol) → `FakeEmailSender` (tests), `PostmarkSender` (prod, httpx),
`NoopEmailSender` (repli si non configuré). SES/SendGrid se branchent derrière le Protocol.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Protocol

_TAG = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    return _TAG.sub("", html).strip()


class EmailSender(Protocol):
    def send(self, *, to: str, subject: str, html: str, text: str = "") -> None: ...


@dataclass
class FakeEmailSender:
    """Enregistre les envois (tests)."""
    sent: List[dict] = field(default_factory=list)

    def send(self, *, to: str, subject: str, html: str, text: str = "") -> None:
        self.sent.append({"to": to, "subject": subject, "html": html, "text": text})


class NoopEmailSender:
    """Repli si l'email n'est pas configuré (dev) — ne casse rien, n'envoie rien."""
    def send(self, *, to: str, subject: str, html: str, text: str = "") -> None:
        return None


class PostmarkSender:
    """Provider transactionnel (référence). Autres providers = même Protocol."""
    def __init__(self, token: str, from_addr: str, *, timeout: float = 15.0):
        self._token, self._from, self._timeout = token, from_addr, timeout

    def send(self, *, to: str, subject: str, html: str, text: str = "") -> None:
        import httpx
        r = httpx.post(
            "https://api.postmarkapp.com/email",
            headers={"X-Postmark-Server-Token": self._token, "Accept": "application/json"},
            json={"From": self._from, "To": to, "Subject": subject,
                  "HtmlBody": html, "TextBody": text or _strip_html(html)},
            timeout=self._timeout,
        )
        r.raise_for_status()


def build_email_sender() -> EmailSender:
    """Construit le sender depuis l'env (POSTMARK_TOKEN + EMAIL_FROM) ; sinon Noop."""
    token = os.environ.get("POSTMARK_TOKEN")
    from_addr = os.environ.get("EMAIL_FROM")
    if token and from_addr:
        return PostmarkSender(token, from_addr)
    return NoopEmailSender()
