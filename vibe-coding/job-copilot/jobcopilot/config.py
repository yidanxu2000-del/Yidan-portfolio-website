"""Configuration loading: config.toml plus environment overrides."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config.toml"


@dataclass
class SendConfig:
    # "review" never sends anything. "approve" sends only what you click Approve on.
    # There is deliberately no fully-autonomous mode; see README.
    mode: str = "review"
    daily_cap: int = 10
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_name: str = ""
    from_email: str = ""
    bcc_self: bool = True


@dataclass
class LinkedInConfig:
    # Reads LinkedIn job-alert emails out of your own mailbox. This is the
    # supported path: you create the alerts, LinkedIn emails you, we parse them.
    alerts_enabled: bool = False
    imap_host: str = "outlook.office365.com"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    lookback_days: int = 7
    # Playwright-driven read of search results in your own logged-in browser.
    # Off by default: automated access is against LinkedIn's terms and can get
    # an account restricted. Opt in knowingly.
    assisted_enabled: bool = False
    assisted_searches: list[str] = field(default_factory=list)
    assisted_max_results: int = 25
    browser_profile_dir: str = ""


@dataclass
class SourcesConfig:
    greenhouse: list[str] = field(default_factory=list)
    lever: list[str] = field(default_factory=list)
    ashby: list[str] = field(default_factory=list)
    workable: list[str] = field(default_factory=list)
    smartrecruiters: list[str] = field(default_factory=list)
    recruitee: list[str] = field(default_factory=list)
    remotive_queries: list[str] = field(default_factory=list)
    arbeitnow: bool = False
    jobicy_queries: list[str] = field(default_factory=list)
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "gb"
    adzuna_queries: list[str] = field(default_factory=list)


@dataclass
class Config:
    api_key: str = ""
    model: str = "claude-opus-5"
    max_tokens: int = 16000
    host: str = "127.0.0.1"
    port: int = 8765
    min_score_to_draft: int = 65
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    linkedin: LinkedInConfig = field(default_factory=LinkedInConfig)
    send: SendConfig = field(default_factory=SendConfig)

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def _fill(cls, raw: dict):
    """Build a dataclass from a dict, ignoring unknown keys."""
    known = {f.name for f in cls.__dataclass_fields__.values()}
    return cls(**{k: v for k, v in raw.items() if k in known})


def load_config(path: Path | None = None) -> Config:
    path = path or CONFIG_PATH
    raw: dict = {}
    if path.exists():
        with path.open("rb") as fh:
            raw = tomllib.load(fh)

    cfg = _fill(Config, {k: v for k, v in raw.items() if not isinstance(v, dict)})
    cfg.sources = _fill(SourcesConfig, raw.get("sources", {}))
    cfg.linkedin = _fill(LinkedInConfig, raw.get("linkedin", {}))
    cfg.send = _fill(SendConfig, raw.get("send", {}))

    # Secrets belong in the environment, not in a file you might commit.
    cfg.api_key = os.environ.get("ANTHROPIC_API_KEY", cfg.api_key)
    cfg.linkedin.imap_password = os.environ.get(
        "JOBCOPILOT_IMAP_PASSWORD", cfg.linkedin.imap_password
    )
    cfg.send.smtp_password = os.environ.get(
        "JOBCOPILOT_SMTP_PASSWORD", cfg.send.smtp_password
    )
    cfg.sources.adzuna_app_key = os.environ.get(
        "JOBCOPILOT_ADZUNA_KEY", cfg.sources.adzuna_app_key
    )

    if cfg.send.mode not in ("review", "approve"):
        raise ValueError(
            f"send.mode must be 'review' or 'approve', got {cfg.send.mode!r}"
        )
    return cfg
