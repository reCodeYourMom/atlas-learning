"""Emails transactionnels (Phase H) — adapter injectable, comme le rostering.

`EmailSender` (Protocol) → `FakeEmailSender` (tests), `SmtpEmailSender` (prod, OCI Email
Delivery / tout SMTP STARTTLS), `PostmarkSender` (API HTTP, alternatif), `NoopEmailSender`
(repli si non configuré). Autres providers = même Protocol.
"""
from __future__ import annotations

import os
import re
import smtplib
import ssl
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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


class SmtpEmailSender:
    """Envoi via SMTP STARTTLS — OCI Email Delivery (UAE) en prod, ou tout serveur SMTP.

    Port 587, STARTTLS obligatoire, TLS 1.2 minimum (exigence OCI). Le mot de passe est un
    identifiant SMTP OCI (portée : soumission SMTP uniquement), jamais versionné.
    """
    def __init__(self, host: str, port: int, username: str, password: str,
                 from_addr: str, *, timeout: float = 15.0):
        self._host, self._port = host, port
        self._user, self._pass = username, password
        self._from, self._timeout = from_addr, timeout

    def send(self, *, to: str, subject: str, html: str, text: str = "") -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"], msg["From"], msg["To"] = subject, self._from, to
        # Partie texte d'abord (fallback), puis HTML : le client affiche la dernière lisible.
        msg.attach(MIMEText(text or _strip_html(html), "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2   # exigence OCI Email Delivery
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as server:
            server.starttls(context=context)
            server.login(self._user, self._pass)
            server.send_message(msg)


class PostmarkSender:
    """Provider transactionnel (API HTTP, alternatif). Autres providers = même Protocol."""
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
    """Construit le sender depuis l'env. Priorité : SMTP (OCI Email Delivery) > Postmark > Noop.

    SMTP (prod ATLAS) : SMTP_HOST + SMTP_USERNAME + SMTP_PASSWORD + EMAIL_FROM.
    Postmark (alternatif) : POSTMARK_TOKEN + EMAIL_FROM.
    Sinon Noop (dev / non configuré) — n'envoie rien, ne casse rien.
    """
    from_addr = os.environ.get("EMAIL_FROM")
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    if host and user and password and from_addr:
        port = int(os.environ.get("SMTP_PORT", "587"))
        return SmtpEmailSender(host, port, user, password, from_addr)
    token = os.environ.get("POSTMARK_TOKEN")
    if token and from_addr:
        return PostmarkSender(token, from_addr)
    return NoopEmailSender()
