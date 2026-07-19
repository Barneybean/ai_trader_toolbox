#!/usr/bin/env python3
"""Regression tests for the rolling position manager."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from position_manager import PositionManagerError, evaluate


SCRIPT = Path(__file__).with_name("position_manager.py")


class LedgerTests(unittest.TestCase):
    def test_profitable_roll_is_reconciled_against_buy_and_hold(self):
        result = evaluate({
            "symbol": "XYZ",
            "starting_cash": 1_000,
            "current_price": 12,
            "benchmark_entry_price": 10,
            "transactions": [
                {"side": "buy", "shares": 50, "price": 10},
                {"side": "sell", "shares": 25, "price": 14},
                {"side": "buy", "shares": 25, "price": 8},
            ],
        })

        self.assertEqual(result["ledger"]["ending_cash"], 650.0)
        self.assertEqual(result["ledger"]["ending_shares"], 50.0)
        self.assertEqual(result["ledger"]["average_cost"], 9.0)
        self.assertEqual(result["performance"]["ending_value"], 1_250.0)
        self.assertEqual(result["performance"]["total_return_pct"], 25.0)
        self.assertEqual(result["performance"]["buy_hold_return_pct"], 20.0)
        self.assertEqual(result["performance"]["alpha_vs_buy_hold_pct_points"], 5.0)

    def test_fees_reduce_return_and_underperformance_is_warned(self):
        result = evaluate({
            "symbol": "FEE",
            "starting_cash": 1_000,
            "current_price": 10,
            "benchmark_entry_price": 10,
            "transactions": [
                {"side": "buy", "shares": 90, "price": 10, "fees": 10},
            ],
        })

        self.assertEqual(result["ledger"]["fees_paid"], 10.0)
        self.assertEqual(result["performance"]["ending_value"], 990.0)
        self.assertEqual(result["performance"]["total_return_pct"], -1.0)
        self.assertIn("ROLLING_UNDERPERFORMED_BUY_HOLD", result["warnings"])

    def test_overselling_fails_closed(self):
        with self.assertRaisesRegex(PositionManagerError, "sells 11 shares but only 10"):
            evaluate({
                "symbol": "BAD",
                "starting_cash": 1_000,
                "current_price": 10,
                "benchmark_entry_price": 10,
                "transactions": [
                    {"side": "buy", "shares": 10, "price": 10},
                    {"side": "sell", "shares": 11, "price": 11},
                ],
            })


class PlanTests(unittest.TestCase):
    def base_input(self):
        return {
            "symbol": "PLAN",
            "starting_cash": 100_000,
            "current_price": 10,
            "benchmark_entry_price": 10,
            "transactions": [{"side": "buy", "shares": 1_000, "price": 10}],
            "plan": {
                "stop_price": 8,
                "max_account_risk_pct": 2,
                "max_position_pct": 25,
                "tranches": [
                    {"price": 9.5, "weight": 1},
                    {"price": 9, "weight": 1},
                ],
            },
        }

    def test_existing_stop_risk_can_bind_and_block_adds(self):
        result = evaluate(self.base_input())

        self.assertEqual(result["plan"]["binding_constraints"], ["risk"])
        self.assertEqual(result["plan"]["planned_shares"], 0)
        self.assertEqual(result["plan"]["post_plan_risk_pct"], 2.0)
        self.assertIn("NO_CAPACITY_FOR_ADDS", result["warnings"])

    def test_concentration_limit_caps_tranches(self):
        data = self.base_input()
        data["plan"]["max_account_risk_pct"] = 10
        result = evaluate(data)

        self.assertEqual(result["plan"]["binding_constraints"], ["concentration"])
        self.assertLessEqual(result["plan"]["post_plan_position_pct"], 25.0)
        self.assertGreater(result["plan"]["planned_shares"], 0)

    def test_cash_limit_caps_tranches(self):
        data = self.base_input()
        data["starting_cash"] = 11_000
        data["plan"]["max_account_risk_pct"] = 20
        data["plan"]["max_position_pct"] = 100
        result = evaluate(data)

        self.assertIn("cash", result["plan"]["binding_constraints"])
        self.assertLessEqual(result["plan"]["planned_notional"], 1_000)

    def test_stop_must_be_below_current_and_tranche_prices(self):
        data = self.base_input()
        data["plan"]["stop_price"] = 10
        with self.assertRaisesRegex(PositionManagerError, "stop_price must be below"):
            evaluate(data)

    def test_whole_shares_flag_must_be_boolean(self):
        data = self.base_input()
        data["plan"]["whole_shares"] = "false"
        with self.assertRaisesRegex(PositionManagerError, "must be true or false"):
            evaluate(data)


class CliTests(unittest.TestCase):
    def test_json_cli_is_machine_readable(self):
        data = {
            "symbol": "CLI",
            "starting_cash": 1_000,
            "current_price": 11,
            "benchmark_entry_price": 10,
            "transactions": [{"side": "buy", "shares": 50, "price": 10}],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.flush()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), handle.name, "--json"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["symbol"], "CLI")
        self.assertEqual(output["performance"]["ending_value"], 1_050.0)


if __name__ == "__main__":
    unittest.main()
