from __future__ import annotations

import unittest
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from app.modules.rollovers import (
    RolloverContract,
    _contracts_from_product,
    due_rollovers,
    load_rollover_contracts,
    render_rollover_alert,
)


NY = ZoneInfo("America/New_York")


class RolloverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = RolloverContract(
            symbol="ES",
            expiring_contract="ESM2026",
            next_contract="ESU2026",
            expiration_date=datetime(2026, 6, 19).date(),
        )

    def test_rollover_is_monday_of_expiration_week(self) -> None:
        self.assertEqual(self.contract.rollover_date.isoformat(), "2026-06-15")

    def test_alerts_are_sunday_then_friday_before_rollover(self) -> None:
        self.assertEqual(self.contract.sunday_alert_date.isoformat(), "2026-06-07")
        self.assertEqual(self.contract.friday_alert_date.isoformat(), "2026-06-12")

    def test_each_warning_is_sent_once_and_only_on_its_date(self) -> None:
        sunday = datetime(2026, 6, 7, 18, 0, tzinfo=NY)
        friday = datetime(2026, 6, 12, 18, 0, tzinfo=NY)
        sent = {self.contract.alert_key("sunday")}

        self.assertEqual(due_rollovers([self.contract], sunday, time(18), sent, "sunday"), [])
        self.assertEqual(due_rollovers([self.contract], friday, time(18), sent, "friday"), [self.contract])
        self.assertEqual(
            due_rollovers([self.contract], datetime(2026, 6, 19, 18, tzinfo=NY), time(18), set(), "friday"),
            [],
        )

    def test_calendar_keeps_product_metadata_and_renders_it(self) -> None:
        contracts = _contracts_from_product(
            {
                "symbol": "ES",
                "product_name": "E-mini S&P 500",
                "exchange": "CME Globex",
                "asset_class": "Equity index futures",
                "notes": "Verify the exchange calendar.",
                "metadata": {"currency": "USD"},
                "contracts": [
                    {"contract": "ESM2026", "expiration_date": "2026-06-19"},
                    {"contract": "ESU2026", "expiration_date": "2026-09-18"},
                ],
            }
        )

        self.assertEqual(len(contracts), 1)
        self.assertEqual(contracts[0].product_name, "E-mini S&P 500")
        self.assertEqual(contracts[0].metadata, {"currency": "USD"})
        rendered = render_rollover_alert(contracts[0], "sunday")
        self.assertIn("Early heads-up", rendered)
        self.assertIn("Exchange:** CME Globex", rendered)
        self.assertIn("Notes:** Verify the exchange calendar.", rendered)

    def test_live_calendar_covers_the_enabled_futures_universe(self) -> None:
        calendar_path = str(Path(__file__).resolve().parents[1] / "config" / "rollovers.json")
        contracts = load_rollover_contracts(
            {"rollover_calendar_path": calendar_path, "rollover_contracts": ()}
        )
        symbols = {contract.symbol for contract in contracts}

        self.assertEqual(
            symbols,
            {
                "ES", "NQ", "YM", "RTY", "GC", "SI", "HG", "PL", "PA", "CL", "BRN", "NG", "RB",
                "US", "ZN", "ZC", "ZW", "ZS", "ZM", "ZL",
            },
        )
        self.assertTrue(any(
            contract.expiring_contract == "ESU2026" and contract.expiration_date.isoformat() == "2026-09-18"
            for contract in contracts
        ))
        self.assertTrue(any(
            contract.expiring_contract == "BZX2026" and contract.expiration_date.isoformat() == "2026-09-30"
            for contract in contracts
        ))
        self.assertTrue(any(
            contract.expiring_contract == "ZNU2026" and contract.expiration_date.isoformat() == "2026-09-21"
            for contract in contracts
        ))
        self.assertTrue(any(
            contract.expiring_contract == "ZCU2026" and contract.expiration_date.isoformat() == "2026-09-14"
            for contract in contracts
        ))


if __name__ == "__main__":
    unittest.main()
