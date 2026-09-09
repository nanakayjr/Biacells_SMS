"""Coordinator for Baicells SMS integration."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_COMMAND_TIMEOUT,
    CONF_DELETE_AFTER_READ,
    CONF_DEVICE_PATH,
    CONF_POLL_INTERVAL,
    CONF_STRICT_HOST_KEY,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_DELETE_AFTER_READ,
    DEFAULT_DEVICE_PATH,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_STRICT_HOST_KEY,
    DOMAIN,
)

if TYPE_CHECKING:
    import asyncssh

_LOGGER = logging.getLogger(__name__)

_HEADER_RE = re.compile(
    r'^\+CMGL:\s*(?P<index>\d+),"(?P<status>[^"]*)","(?P<sender>[^"]*)",(?:"[^"]*"|),(?:"(?P<date>[^"]*)"|)$'
)
_DEVICE_RE = re.compile(r"^/dev/[A-Za-z0-9._-]+$")


@dataclass(slots=True)
class SmsMessage:
    """Normalized SMS message parsed from modem output."""

    index: int
    status: str
    sender: str
    timestamp: str
    text: str

    @property
    def signature(self) -> str:
        """Stable signature for de-duplication if needed."""
        digest = hashlib.sha256(
            f"{self.sender}|{self.timestamp}|{self.text}".encode("utf-8", errors="ignore")
        )
        return digest.hexdigest()


def _convert_gsm_timestamp(value: str) -> str:
    """Convert GSM timestamp like yy/mm/dd,HH:MM:SS+32 to ISO 8601 when possible."""
    if not value:
        return ""

    match = re.match(
        r"^(?P<date>\d{2}/\d{2}/\d{2}),(?P<time>\d{2}:\d{2}:\d{2})(?P<tz>[+-]\d{2})$",
        value,
    )
    if not match:
        return value

    base = datetime.strptime(
        f"{match.group('date')} {match.group('time')}", "%y/%m/%d %H:%M:%S"
    )
    quarters = int(match.group("tz"))
    suffix = "-" if quarters < 0 else "+"
    hours = abs(quarters) // 4
    minutes = (abs(quarters) % 4) * 15
    return f"{base.strftime('%Y-%m-%d %H:%M:%S')} {suffix}{hours:02d}:{minutes:02d}"


def parse_cmgl_output(raw_text: str) -> list[SmsMessage]:
    """Parse AT+CMGL modem output into structured SMS messages."""
    messages: list[SmsMessage] = []
    current: dict[str, Any] | None = None
    body_lines: list[str] = []

    for line in raw_text.splitlines():
        line = line.strip("\r")
        if not line:
            continue

        header_match = _HEADER_RE.match(line)
        if header_match:
            if current is not None:
                messages.append(
                    SmsMessage(
                        index=int(current["index"]),
                        status=current["status"],
                        sender=current["sender"],
                        timestamp=_convert_gsm_timestamp(current["date"]),
                        text="\n".join(body_lines).strip(),
                    )
                )
            current = header_match.groupdict()
            body_lines = []
            continue

        if line == "OK":
            continue

        if current is not None:
            body_lines.append(line)

    if current is not None:
        messages.append(
            SmsMessage(
                index=int(current["index"]),
                status=current["status"],
                sender=current["sender"],
                timestamp=_convert_gsm_timestamp(current["date"]),
                text="\n".join(body_lines).strip(),
            )
        )

    return messages


class BaicellsSmsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch SMS messages from a Baicells router over SSH."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._history_loaded = False
        self._history: list[dict[str, Any]] = []
        self._seen_signatures: set[str] = set()

        poll_seconds = int(entry.options.get(CONF_POLL_INTERVAL, entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=poll_seconds),
        )

    @property
    def messages_file(self) -> Path:
        """Path used to persist fetched SMS records."""
        folder = Path(self.hass.config.path(DOMAIN))
        return folder / f"{self.entry.entry_id}_messages.txt"

    @property
    def history_file(self) -> Path:
        """Path used to persist full SMS history."""
        folder = Path(self.hass.config.path(DOMAIN))
        return folder / f"{self.entry.entry_id}_messages.json"

    async def _async_update_data(self) -> dict[str, Any]:
        """Read SMS messages and optionally delete them from SIM."""
        merged = {**self.entry.data, **self.entry.options}

        host = merged[CONF_HOST]
        port = int(merged.get(CONF_PORT, 27149))
        username = merged[CONF_USERNAME]
        password = merged[CONF_PASSWORD]
        device_path = merged.get(CONF_DEVICE_PATH, DEFAULT_DEVICE_PATH)
        delete_after_read = bool(merged.get(CONF_DELETE_AFTER_READ, DEFAULT_DELETE_AFTER_READ))
        strict_host_key = bool(merged.get(CONF_STRICT_HOST_KEY, DEFAULT_STRICT_HOST_KEY))
        command_timeout = int(merged.get(CONF_COMMAND_TIMEOUT, DEFAULT_COMMAND_TIMEOUT))

        if not _DEVICE_RE.match(device_path):
            raise UpdateFailed(f"Invalid modem device path: {device_path}")

        script_lines = [
            "set +e",
            "tmp_file=\"/tmp/baicells_sms_$$.log\"",
            f"(cat {device_path} > \"$tmp_file\") &",
            "cat_pid=$!",
            "sleep 0.5",
            f"printf 'AT+CMGF=1\\r\\n' > {device_path}",
            "sleep 1",
            f"printf 'AT+CPMS=\"SM\",\"SM\",\"SM\"\\r\\n' > {device_path}",
            "sleep 1",
            f"printf 'AT+CMGL=\"ALL\"\\r\\n' > {device_path}",
            "sleep 3",
        ]

        if delete_after_read:
            script_lines.extend(
                [
                    f"printf 'AT+CMGD=1,4\\r\\n' > {device_path}",
                    "sleep 1",
                ]
            )

        script_lines.extend(
            [
                "kill \"$cat_pid\" >/dev/null 2>&1 || true",
                "sleep 0.3",
                "cat \"$tmp_file\"",
                "rm -f \"$tmp_file\"",
                "exit 0",
            ]
        )

        command = "\n".join(script_lines)

        if not self._history_loaded:
            try:
                await self.hass.async_add_executor_job(self._load_history)
            except OSError as err:
                _LOGGER.warning("Unable to load SMS history file: %s", err)
            self._history_loaded = True

        try:
            # Import lazily so a missing/incompatible asyncssh installation
            # only fails when a read is actually attempted, instead of
            # breaking the whole integration package (and therefore the
            # config flow) at import time. Home Assistant installs the
            # pinned requirement from manifest.json before this coordinator
            # ever runs, but keeping the import local guards against
            # platforms where the wheel fails to build/install.
            import asyncssh
        except ImportError as err:
            raise UpdateFailed(
                "The 'asyncssh' package is not installed or failed to load; "
                f"reinstall the integration requirements. Details: {err}"
            ) from err

        try:
            known_hosts = None if not strict_host_key else self.hass.config.path("known_hosts")

            async with asyncssh.connect(
                host,
                port=port,
                username=username,
                password=password,
                known_hosts=known_hosts,
                kex_algs=["diffie-hellman-group1-sha1", "diffie-hellman-group14-sha1"],
                server_host_key_algs=["ssh-rsa"],
                encryption_algs=["aes128-cbc", "3des-cbc"],
            ) as conn:
                result = await conn.run(command, timeout=command_timeout, check=False)
        except (OSError, asyncssh.Error, TimeoutError) as err:
            raise UpdateFailed(f"SSH communication failed: {err}") from err

        messages = parse_cmgl_output(result.stdout)

        if messages:
            try:
                await self.hass.async_add_executor_job(self._append_messages_to_file, messages)
            except OSError as err:
                _LOGGER.warning("Unable to persist SMS messages to file: %s", err)

        new_messages = self._add_to_history(messages)
        if new_messages:
            try:
                await self.hass.async_add_executor_job(self._save_history)
            except OSError as err:
                _LOGGER.warning("Unable to persist SMS history to JSON: %s", err)

        return {
            "message_count": len(self._history),
            "last_poll_count": len(messages),
            "new_message_count": new_messages,
            "messages": [
                item for item in reversed(self._history)
            ],
            "last_update": datetime.now().isoformat(),
            "messages_file": str(self.messages_file),
            "history_file": str(self.history_file),
            "delete_after_read": delete_after_read,
            "raw_tail": result.stdout[-1000:],
        }

    def _add_to_history(self, messages: list[SmsMessage]) -> int:
        """Add newly fetched messages to in-memory history."""
        added = 0
        for item in messages:
            if item.signature in self._seen_signatures:
                continue
            entry = {
                "index": item.index,
                "status": item.status,
                "sender": item.sender,
                "timestamp": item.timestamp,
                "text": item.text,
                "signature": item.signature,
            }
            self._history.append(entry)
            self._seen_signatures.add(item.signature)
            added += 1
        return added

    def _load_history(self) -> None:
        """Load persisted message history from JSON file."""
        if not self.history_file.exists():
            return
        try:
            raw = self.history_file.read_text(encoding="utf-8")
            items = json.loads(raw)
        except (OSError, json.JSONDecodeError) as err:
            _LOGGER.warning("Unable to load SMS history file: %s", err)
            return
        if not isinstance(items, list):
            _LOGGER.warning("Ignoring SMS history because it does not contain a list")
            return
        self._history = [item for item in items if isinstance(item, dict)]
        self._seen_signatures = {
            item["signature"]
            for item in self._history
            if isinstance(item.get("signature"), str)
        }

    def _save_history(self) -> None:
        """Persist current message history to JSON file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.write_text(
            json.dumps(self._history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _append_messages_to_file(self, messages: list[SmsMessage]) -> None:
        """Append fetched messages to local text file."""
        self.messages_file.parent.mkdir(parents=True, exist_ok=True)

        now = datetime.now().isoformat()
        with self.messages_file.open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== Retrieval {now} ===\n")
            for message in messages:
                handle.write(f"From: {message.sender}\n")
                handle.write(f"Date: {message.timestamp}\n")
                handle.write(f"Status: {message.status}\n")
                handle.write("Message:\n")
                handle.write(f"{message.text}\n")
                handle.write("---\n")
