from __future__ import annotations

import unittest

from app.modules.assets import (
    DEFAULT_FUTURES,
    TICKER_DISPLAY,
    TICKER_EMOJIS,
    format_price,
    normalize_ticker,
)
from app.modules.render import DAILY_MODEL_ORDER, WEEKLY_MODEL_ORDER, render_digest, render_stream


def _inside(model: str, ticker: str) -> dict:
    return {
        "ticker": ticker,
        "model": model,
        "timeframe": "D" if model == "ID" else "W",
        "signal_date": "2026-08-08",
        "computed": {"previous_high": 100.0, "previous_low": 90.0},
    }


class RenderStreamTests(unittest.TestCase):
    def test_inside_day_uses_failure_model_and_pdh_pdl(self) -> None:
        rendered = render_stream("ID", [_inside("ID", "CAD")], source="test")

        self.assertIn("<:cxy:1535631926809989120> CAD - Inside Day Failure", rendered)
        self.assertIn("📈 Model: Inside Day Failure", rendered)
        self.assertIn("🔑 Key Levels: PDH `100.00000` / PDL `90.00000`", rendered)
        self.assertNotIn("Type: Inside", rendered)

    def test_inside_week_uses_failure_model_and_pwh_pwl(self) -> None:
        rendered = render_stream("IW", [_inside("IW", "ZN=F")], source="test")

        self.assertIn("<:us:1531341929311244419> ZN - Inside Week Failure", rendered)
        self.assertIn("📈 Model: Inside Week Failure", rendered)
        self.assertIn("🔑 Key Levels: PWH `100.000000` / PWL `90.000000`", rendered)

    def test_new_futures_tickers_get_their_live_emojis(self) -> None:
        cases = {
            "HG=F": "<:hg:1535238536855556196> HG",
            "HO=F": "<:ho:1541470211973185636> HO",
            "PL=F": "<:pl:1541470215139762237> PL",
            "PA=F": "<:pa:1541470213583671408> PA",
        }

        for ticker, expected in cases.items():
            with self.subTest(ticker=ticker):
                rendered = render_stream("ID", [_inside("ID", ticker)], source="test")
                self.assertIn(expected, rendered)

    def test_emoji_map_only_uses_canonical_tickers(self) -> None:
        self.assertFalse(any("=" in ticker or "." in ticker for ticker in TICKER_EMOJIS))

        rendered = render_stream("ID", [_inside("ID", "CL=F")], source="test")
        self.assertIn("<:crudeoil:1294743881434533898> CL", rendered)

    def test_webhook_tickers_are_not_provider_rewritten(self) -> None:
        self.assertEqual(normalize_ticker("EU"), "EU")
        self.assertEqual(normalize_ticker("USDCAD"), "USDCAD")
        self.assertEqual(normalize_ticker("UCAD"), "CAD")
        self.assertEqual(normalize_ticker("UCHF"), "CHF")
        self.assertEqual(normalize_ticker("NU"), "NZD")
        self.assertEqual(normalize_ticker("FX:EU"), "EU")
        self.assertNotIn("=X", normalize_ticker("EURUSD"))

    def test_every_default_asset_has_a_canonical_display_ticker(self) -> None:
        self.assertTrue(set(DEFAULT_FUTURES).issubset(TICKER_DISPLAY))

    def test_prices_snap_to_contract_tick_sizes(self) -> None:
        self.assertEqual(format_price("YM", 47001.64), "47002")
        self.assertEqual(format_price("ES=F", 6000.124), "6000.00")
        self.assertEqual(format_price("ZN", 110.023), "110.015625")
        self.assertEqual(format_price("CAD", 1.372346), "1.37235")

    def test_each_rendered_asset_has_a_tick_size(self) -> None:
        from app.modules.assets import TICKER_TICK_SIZES

        self.assertTrue(set(TICKER_EMOJIS).issubset(TICKER_TICK_SIZES))

    def test_digest_groups_models_and_shows_key_levels(self) -> None:
        rendered = render_digest("**Test digest**", [_inside("ID", "YM=F")], [])

        self.assertIn("**Active setups:** 1", rendered)
        self.assertIn("## Inside Day Failures", rendered)
        self.assertIn("<:ym:1294743731643351212> **YM** • `D`", rendered)
        self.assertIn("**Key levels:** PDH `100` / PDL `90`", rendered)
        self.assertIn("**Model:** Inside Day Failure", rendered)
        self.assertIn("**Feed:** Futures scan", rendered)

    def test_zebra_digest_uses_trigger_level_not_pattern(self) -> None:
        signal = {
            "ticker": "NQ=F",
            "model": "Bearish Zebra",
            "timeframe": "D",
            "direction": "bearish",
            "computed": {"previous_high": 22010.25, "previous_low": 21995.0, "price": 22000.5},
        }
        rendered = render_digest("**Test digest**", [signal], [])

        self.assertIn("**Key levels:** PDH `22010.25` • PDL `21995.00` • Price `22000.50`", rendered)
        self.assertIn("Expected continuation: **Down**", rendered)
        self.assertIn("## Bearish Zebra", rendered)
        self.assertNotIn("Pattern", rendered)

        stream = render_stream("Bearish Zebra", [signal], source="test")
        self.assertIn("📈 Model: Bearish Zebra", stream)
        self.assertNotIn("📈 Type:", stream)

    def test_digest_labels_tradingview_source(self) -> None:
        signal = _inside("ID", "GU") | {"source": "tradingview"}
        rendered = render_digest("**Test digest**", [signal], [])

        self.assertIn("**Feed:** TradingView", rendered)

    def test_weekly_digest_excludes_daily_models_and_renders_weekly_retest(self) -> None:
        weekly_retest = {
            "ticker": "YM=F",
            "model": "+RR Weekly",
            "timeframe": "W",
            "direction": "bull",
            "computed": {"d1_high": 47000, "d1_low": 46800, "d2_close": 47020, "d3_level": 47010},
        }
        daily = _inside("ID", "ES=F")
        rendered = render_digest(
            "**Weekly**",
            [daily, weekly_retest],
            [],
            WEEKLY_MODEL_ORDER,
        )

        self.assertIn("## Bullish Weekly Rounded Retests", rendered)
        self.assertIn("**YM** • `W`", rendered)
        self.assertNotIn("Inside Day Failures", rendered)
        self.assertNotIn("**ES**", rendered)
        self.assertIn("ID", DAILY_MODEL_ORDER)
        self.assertIn("+RR Weekly", WEEKLY_MODEL_ORDER)
