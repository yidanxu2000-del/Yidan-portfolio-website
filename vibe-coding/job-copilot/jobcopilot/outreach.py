"""Sending. Every path through here requires an explicit per-application approval.

There is no autonomous send mode, and adding one would be a mistake. Mass-sent
applications get filtered, and a bad one sent under your name to a company you
wanted is not recoverable. So the model prepares; you press send.

Attachments must live under data/ — put a PDF resume in data/attachments/ and the
rendered documents land in data/out/.
"""

from __future__ import annotations

import mimetypes
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from .config import DATA_DIR, Config
from .render import markdown_to_paragraphs

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
ATTACHMENTS_DIR = DATA_DIR / "attachments"


class SendBlocked(RuntimeError):
    """Refused before anything left the machine."""


def resolve_attachment(path_str: str) -> Path:
    """Confine attachments to data/ so a bad path can't read arbitrary files."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = DATA_DIR / path
    path = path.resolve()
    root = DATA_DIR.resolve()
    if not path.is_relative_to(root):
        raise SendBlocked(
            f"Attachments must be under {root}. Put files in data/attachments/."
        )
    if not path.is_file():
        raise SendBlocked(f"No such file: {path}")
    return path


def preflight(cfg: Config, to_email: str, sent_today: int) -> list[str]:
    """Everything that would stop a send, gathered up so the UI can show it."""
    problems: list[str] = []
    if cfg.send.mode != "approve":
        problems.append(
            "send.mode is 'review' — nothing will be sent. Set it to 'approve' in "
            "config.toml when you're ready to send."
        )
    if not EMAIL_RE.match((to_email or "").strip()):
        problems.append("A valid recipient address is required.")
    if not (cfg.send.smtp_host and cfg.send.smtp_user):
        problems.append("send.smtp_host and send.smtp_user are not configured.")
    if not cfg.send.smtp_password:
        problems.append("JOBCOPILOT_SMTP_PASSWORD is not set in the environment.")
    if not cfg.send.from_email:
        problems.append("send.from_email is not configured.")
    if sent_today >= cfg.send.daily_cap:
        problems.append(
            f"Daily cap reached ({sent_today}/{cfg.send.daily_cap}). "
            "Raise send.daily_cap if that's deliberate."
        )
    return problems


def build_message(
    cfg: Config,
    *,
    to_email: str,
    to_name: str,
    subject: str,
    body_markdown: str,
    attachments: list[str],
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = (
        f"{cfg.send.from_name} <{cfg.send.from_email}>"
        if cfg.send.from_name
        else cfg.send.from_email
    )
    msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
    msg["Subject"] = subject
    if cfg.send.bcc_self:
        msg["Bcc"] = cfg.send.from_email
    msg["Reply-To"] = cfg.send.from_email

    msg.set_content(body_markdown)
    msg.add_alternative(
        "<!doctype html><html><body style=\"font-family:-apple-system,"
        "BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:15px;"
        f'line-height:1.5;color:#1d1d1f">{markdown_to_paragraphs(body_markdown)}'
        "</body></html>",
        subtype="html",
    )

    for raw in attachments:
        path = resolve_attachment(raw)
        ctype, _ = mimetypes.guess_type(path.name)
        maintype, _, subtype = (ctype or "application/octet-stream").partition("/")
        msg.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype or "octet-stream",
            filename=path.name,
        )
    return msg


def send(
    cfg: Config,
    *,
    to_email: str,
    to_name: str,
    subject: str,
    body_markdown: str,
    attachments: list[str],
    sent_today: int,
    approved: bool,
) -> dict:
    """Send one application. `approved` must be True — the gate is not optional."""
    if not approved:
        raise SendBlocked("Not approved. Nothing was sent.")

    problems = preflight(cfg, to_email, sent_today)
    if problems:
        raise SendBlocked("; ".join(problems))

    msg = build_message(
        cfg,
        to_email=to_email.strip(),
        to_name=to_name.strip(),
        subject=subject,
        body_markdown=body_markdown,
        attachments=attachments,
    )

    context = ssl.create_default_context()
    if cfg.send.smtp_port == 465:
        with smtplib.SMTP_SSL(
            cfg.send.smtp_host, cfg.send.smtp_port, context=context, timeout=45
        ) as server:
            server.login(cfg.send.smtp_user, cfg.send.smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(cfg.send.smtp_host, cfg.send.smtp_port, timeout=45) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(cfg.send.smtp_user, cfg.send.smtp_password)
            server.send_message(msg)

    return {
        "to": to_email,
        "subject": subject,
        "attachments": [Path(a).name for a in attachments],
    }
