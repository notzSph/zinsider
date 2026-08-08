from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.modules.state import get_state, save_state

MONTH_CODES = set("FGHJKMNQUVXZ")


@dataclass(frozen=True)
class RolloverContract:
    symbol: str
    expiring_contract: str
    next_contract: str
    expiration_date: date
    product_name: str = ""
    exchange: str = ""
    asset_class: str = ""
    contract_url: str = ""
    notes: str = ""
    metadata: dict[str, Any] | None = None

    @property
    def rollover_date(self) -> date:
        """First Monday of the expiration week (New York calendar)."""
        return self.expiration_date - timedelta(days=self.expiration_date.weekday())

    @property
    def sunday_alert_date(self) -> date:
        """Sunday eight days before the rollover Monday."""
        return self.rollover_date - timedelta(days=8)

    @property
    def friday_alert_date(self) -> date:
        """Friday immediately before the rollover Monday."""
        return self.rollover_date - timedelta(days=3)

    def alert_date(self, alert_kind: str) -> date:
        if alert_kind == "sunday":
            return self.sunday_alert_date
        if alert_kind == "friday":
            return self.friday_alert_date
        raise ValueError(f"Unknown rollover alert kind: {alert_kind}")

    def alert_key(self, alert_kind: str) -> str:
        return (
            f"{alert_kind}:{self.expiring_contract}->{self.next_contract}"
            f"@{self.expiration_date.isoformat()}"
        )


def _parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def _symbol_from_contract(contract: str) -> str:
    normalized = contract.strip().upper()
    for index, char in enumerate(normalized):
        suffix = normalized[index + 1 :]
        if char in MONTH_CODES and len(suffix) == 4 and suffix.isdigit():
            return normalized[:index]
    return normalized


def _contract_from_dict(raw: dict) -> RolloverContract:
    expiring = str(raw.get("expiring_contract") or raw.get("expiring") or "").strip().upper()
    next_contract = str(raw.get("next_contract") or raw.get("next") or "").strip().upper()
    expiration = str(raw.get("expiration_date") or raw.get("expiration") or "").strip()
    symbol = str(raw.get("symbol") or _symbol_from_contract(expiring)).strip().upper()

    if not expiring or not next_contract or not expiration:
        raise ValueError(f"Invalid rollover calendar item: {raw!r}")

    return RolloverContract(
        symbol=symbol,
        expiring_contract=expiring,
        next_contract=next_contract,
        expiration_date=_parse_date(expiration),
        product_name=str(raw.get("product_name") or raw.get("name") or "").strip(),
        exchange=str(raw.get("exchange") or "").strip(),
        asset_class=str(raw.get("asset_class") or "").strip(),
        contract_url=str(raw.get("contract_url") or raw.get("url") or "").strip(),
        notes=str(raw.get("notes") or "").strip(),
        metadata=dict(raw.get("metadata") or {}),
    )


def _contracts_from_product(raw: dict) -> list[RolloverContract]:
    symbol = str(raw.get("symbol") or "").strip().upper()
    raw_contracts = raw.get("contracts", [])
    if not symbol:
        raise ValueError(f"Rollover product is missing symbol: {raw!r}")
    if not isinstance(raw_contracts, list):
        raise ValueError(f"Rollover product contracts must be a list: {raw!r}")

    product_details = {
        "product_name": str(raw.get("product_name") or raw.get("name") or "").strip(),
        "exchange": str(raw.get("exchange") or "").strip(),
        "asset_class": str(raw.get("asset_class") or "").strip(),
        "contract_url": str(raw.get("contract_url") or raw.get("url") or "").strip(),
        "notes": str(raw.get("notes") or "").strip(),
        "metadata": dict(raw.get("metadata") or {}),
    }
    contracts: list[tuple[str, date, dict[str, Any]]] = []
    for item in raw_contracts:
        if isinstance(item, str):
            parts = [part.strip() for part in item.replace(":", ",").split(",") if part.strip()]
            if len(parts) != 2:
                raise ValueError(f"Invalid rollover product contract entry: {item!r}")
            contract_code, expiration = parts
            contract_details: dict[str, Any] = {}
        elif isinstance(item, dict):
            contract_code = str(item.get("contract") or item.get("code") or "").strip().upper()
            expiration = str(item.get("expiration_date") or item.get("expiration") or "").strip()
            contract_details = {
                "contract_url": str(item.get("contract_url") or item.get("url") or product_details["contract_url"]).strip(),
                "notes": str(item.get("notes") or product_details["notes"]).strip(),
                "metadata": {**product_details["metadata"], **dict(item.get("metadata") or {})},
            }
        else:
            raise ValueError(f"Invalid rollover product contract entry: {item!r}")

        if not contract_code or not expiration:
            raise ValueError(f"Invalid rollover product contract entry: {item!r}")
        contracts.append((contract_code, _parse_date(expiration), contract_details))

    contracts.sort(key=lambda item: item[1])

    rollovers: list[RolloverContract] = []
    for index, (expiring_contract, expiration_date, contract_details) in enumerate(contracts[:-1]):
        next_contract = contracts[index + 1][0]
        details = {**product_details, **contract_details}
        rollovers.append(
            RolloverContract(
                symbol=symbol,
                expiring_contract=expiring_contract,
                next_contract=next_contract,
                expiration_date=expiration_date,
                **details,
            )
        )
    return rollovers


def _contract_from_string(value: str) -> RolloverContract:
    """
    Parse one env contract entry.

    Supported forms:
    - ESM2026:2026-06-19:ESU2026
    - ES:ESM2026:2026-06-19:ESU2026
    """
    raw_parts = value.replace("|", ",").replace(":", ",").split(",")
    parts = [part.strip() for part in raw_parts if part.strip()]

    if len(parts) == 3:
        expiring, expiration, next_contract = parts
        symbol = _symbol_from_contract(expiring)
    elif len(parts) == 4:
        symbol, expiring, expiration, next_contract = parts
    else:
        raise ValueError(
            "Invalid ROLLOVER_CONTRACTS entry. Use ESM2026:2026-06-19:ESU2026 "
            "or ES:ESM2026:2026-06-19:ESU2026"
        )

    return RolloverContract(
        symbol=symbol.strip().upper(),
        expiring_contract=expiring.strip().upper(),
        next_contract=next_contract.strip().upper(),
        expiration_date=_parse_date(expiration),
    )


def load_rollover_contracts(settings: dict) -> list[RolloverContract]:
    contracts: list[RolloverContract] = []

    calendar_path = settings.get("rollover_calendar_path", "")
    if calendar_path:
        path = Path(calendar_path)
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and "products" in payload:
            products = payload["products"]
            if not isinstance(products, list):
                raise ValueError("Rollover calendar products must be a list")
            for product in products:
                contracts.extend(_contracts_from_product(product))
            items = payload.get("contracts", [])
        else:
            items = payload.get("contracts", payload) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise ValueError("Rollover calendar must be a list or an object with a contracts list")
        contracts.extend(_contract_from_dict(item) for item in items)

    contracts.extend(_contract_from_string(item) for item in settings.get("rollover_contracts", ()))
    return sorted(contracts, key=lambda item: (item.sunday_alert_date, item.symbol, item.expiring_contract))


def due_rollovers(
    contracts: list[RolloverContract],
    now: datetime,
    alert_time: dtime,
    sent_keys: set[str],
    alert_kind: str,
    force: bool = False,
) -> list[RolloverContract]:
    due: list[RolloverContract] = []
    for contract in contracts:
        alert_at = datetime.combine(contract.alert_date(alert_kind), alert_time, tzinfo=now.tzinfo)
        if contract.alert_key(alert_kind) in sent_keys and not force:
            continue
        if force or now.date() == alert_at.date():
            due.append(contract)
    return due


def render_rollover_alert(contract: RolloverContract, alert_kind: str) -> str:
    phase = "Early heads-up" if alert_kind == "sunday" else "Final rollover reminder"
    details = [
        f"**{contract.symbol} Futures Rollover — {phase}**",
        f"**Roll:** `{contract.expiring_contract}` → `{contract.next_contract}`",
        f"**Rollover Monday:** `{contract.rollover_date.isoformat()}`",
        f"**Expiration:** `{contract.expiration_date.isoformat()}`",
    ]
    if contract.product_name:
        details.insert(1, f"**Product:** {contract.product_name}")
    if contract.exchange:
        details.append(f"**Exchange:** {contract.exchange}")
    if contract.asset_class:
        details.append(f"**Asset class:** {contract.asset_class}")
    if contract.notes:
        details.append(f"**Notes:** {contract.notes}")
    if contract.contract_url:
        details.append(f"**Contract spec:** {contract.contract_url}")
    return "\n".join(details)


def run_rollover_alerts(force: bool = False, now: datetime | None = None) -> dict:
    from app.modules.config import get_settings
    from app.modules.webhooks import send_discord_message

    settings = get_settings()
    if not settings["rollover_enabled"] and not force:
        return {"status": "disabled"}

    tz = ZoneInfo(settings["ny_timezone"])
    now = now.astimezone(tz) if now else datetime.now(tz)
    alert_time = dtime(hour=settings["rollover_alert_hour"], minute=settings["rollover_alert_minute"])

    contracts = load_rollover_contracts(settings)
    state = get_state(settings["state_dir"])
    sent_keys = set(state.get("sent_rollover_alerts", []))
    alert_kind = "sunday" if now.weekday() == 6 else "friday"
    if not force and now.weekday() not in (4, 6):
        return {
            "status": "skipped",
            "reason": "not-alert-day",
            "contracts": len(contracts),
            "now": now.isoformat(timespec="seconds"),
        }
    due = due_rollovers(contracts, now, alert_time, sent_keys, alert_kind, force=force)

    if not due:
        return {
            "status": "skipped",
            "contracts": len(contracts),
            "due": 0,
            "now": now.isoformat(timespec="seconds"),
        }

    for contract in due:
        send_discord_message(
            render_rollover_alert(contract, alert_kind),
            settings["discord_bot_token"],
            settings["discord_rollover_thread_id"],
            dry_run=settings["dry_run"],
            role_id=settings.get("discord_role_id", ""),
            allow_role_ping=settings.get("discord_ping_role", False),
        )
        sent_keys.add(contract.alert_key(alert_kind))

    state["sent_rollover_alerts"] = sorted(sent_keys)
    save_state(settings["state_dir"], state)

    return {
        "status": "ok",
        "contracts": len(contracts),
        "sent": len(due),
        "alert_kind": alert_kind,
        "alerts": [contract.alert_key(alert_kind) for contract in due],
    }
