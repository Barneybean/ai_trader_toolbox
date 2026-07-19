#!/usr/bin/env python3
"""Rolling position manager — verify a ledger and risk-cap staged adds.

This engine turns "sell strength, rebuild on qualified weakness" into auditable
math. It replays a complete cash-funded transaction ledger using average-cost
accounting, marks the remaining position to a user-supplied current price,
compares the result with an all-in buy-and-hold benchmark, and sizes optional
buy tranches within three configurable limits:

  1. cash remaining after the ledger;
  2. maximum position concentration; and
  3. maximum account loss from the plan's stop.

It does not fetch prices, persist account data, choose entry levels, perform
tax-lot accounting, or place orders. Inputs stay in the user's local JSON file.

Usage:
  python3 scripts/analysis/position_manager.py plan.json
  python3 scripts/analysis/position_manager.py plan.json --json

Input shape (fictional numbers):
  {
    "symbol": "XYZ",
    "starting_cash": 100000,
    "current_price": 10,
    "benchmark_entry_price": 8,
    "transactions": [
      {"side": "buy", "shares": 5000, "price": 8, "fees": 5},
      {"side": "sell", "shares": 1000, "price": 12, "fees": 5}
    ],
    "plan": {
      "stop_price": 7.5,
      "max_account_risk_pct": 2,
      "max_position_pct": 25,
      "whole_shares": true,
      "tranches": [
        {"price": 9.5, "weight": 1},
        {"price": 8.75, "weight": 1}
      ]
    }
  }

The benchmark invests starting_cash at benchmark_entry_price with fractional
shares and no fees. The comparison is intentionally demanding: more shares do
not prove value-add; only after-cost ending value does.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import desk_log  # noqa: E402


ZERO = Decimal("0")
CENT = Decimal("0.01")
FOUR_DP = Decimal("0.0001")
EPSILON = Decimal("0.00000001")


class PositionManagerError(ValueError):
    """Raised when a ledger or plan cannot be reconciled safely."""


def _number(value: Any, label: str, *, allow_zero: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise PositionManagerError(f"{label} must be a number")
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise PositionManagerError(f"{label} must be a number") from exc
    if not number.is_finite():
        raise PositionManagerError(f"{label} must be finite")
    if number < ZERO or (number == ZERO and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise PositionManagerError(f"{label} must be {qualifier}")
    return number


def _float(value: Decimal, places: Decimal = CENT) -> float:
    return float(value.quantize(places))


def _shares(value: Decimal, whole_shares: bool) -> Decimal:
    quantum = Decimal("1") if whole_shares else FOUR_DP
    return value.quantize(quantum, rounding=ROUND_DOWN)


def _replay_ledger(data: dict[str, Any]) -> dict[str, Decimal | int]:
    starting_cash = _number(data.get("starting_cash"), "starting_cash")
    cash = starting_cash
    shares = ZERO
    cost_basis = ZERO
    realized = ZERO
    fees_paid = ZERO
    transactions = data.get("transactions", [])
    if not isinstance(transactions, list):
        raise PositionManagerError("transactions must be a list")

    for index, transaction in enumerate(transactions, start=1):
        if not isinstance(transaction, dict):
            raise PositionManagerError(f"transaction {index} must be an object")
        side = str(transaction.get("side", "")).lower()
        if side not in {"buy", "sell"}:
            raise PositionManagerError(f"transaction {index} side must be buy or sell")
        quantity = _number(transaction.get("shares"), f"transaction {index} shares")
        price = _number(transaction.get("price"), f"transaction {index} price")
        fees = _number(
            transaction.get("fees", 0),
            f"transaction {index} fees",
            allow_zero=True,
        )
        fees_paid += fees

        if side == "buy":
            debit = quantity * price + fees
            if debit > cash + EPSILON:
                raise PositionManagerError(
                    f"transaction {index} needs {debit} cash but only {cash} is available"
                )
            cash -= debit
            cost_basis += debit
            shares += quantity
            continue

        if quantity > shares + EPSILON:
            raise PositionManagerError(
                f"transaction {index} sells {quantity} shares but only {shares} are held"
            )
        average_cost = cost_basis / shares
        basis_removed = average_cost * quantity
        proceeds = quantity * price - fees
        if proceeds < ZERO:
            raise PositionManagerError(f"transaction {index} fees exceed sale proceeds")
        cash += proceeds
        cost_basis -= basis_removed
        shares -= quantity
        realized += proceeds - basis_removed
        if shares.copy_abs() <= EPSILON:
            shares = ZERO
            cost_basis = ZERO

    return {
        "starting_cash": starting_cash,
        "cash": cash,
        "shares": shares,
        "cost_basis": cost_basis,
        "realized": realized,
        "fees_paid": fees_paid,
        "transaction_count": len(transactions),
    }


def _build_plan(
    plan: dict[str, Any],
    *,
    account_value: Decimal,
    cash: Decimal,
    current_price: Decimal,
    existing_shares: Decimal,
) -> tuple[dict[str, Any], list[str]]:
    stop = _number(plan.get("stop_price"), "plan.stop_price", allow_zero=True)
    risk_pct = _number(plan.get("max_account_risk_pct", 2), "plan.max_account_risk_pct")
    concentration_pct = _number(plan.get("max_position_pct", 25), "plan.max_position_pct")
    if risk_pct > 100 or concentration_pct > 100:
        raise PositionManagerError("plan percentage limits cannot exceed 100")
    if stop >= current_price:
        raise PositionManagerError("plan.stop_price must be below current_price")

    raw_tranches = plan.get("tranches")
    if not isinstance(raw_tranches, list) or not raw_tranches:
        raise PositionManagerError("plan.tranches must be a non-empty list")

    tranches: list[tuple[Decimal, Decimal]] = []
    for index, tranche in enumerate(raw_tranches, start=1):
        if not isinstance(tranche, dict):
            raise PositionManagerError(f"plan tranche {index} must be an object")
        price = _number(tranche.get("price"), f"plan tranche {index} price")
        weight = _number(tranche.get("weight", 1), f"plan tranche {index} weight")
        if stop >= price:
            raise PositionManagerError(
                f"plan.stop_price must be below tranche {index} price"
            )
        tranches.append((price, weight))

    total_weight = sum((weight for _, weight in tranches), ZERO)
    normalized = [(price, weight / total_weight) for price, weight in tranches]
    risk_rate = sum(
        (weight * (price - stop) / price for price, weight in normalized),
        ZERO,
    )

    risk_budget = account_value * risk_pct / Decimal("100")
    existing_risk = existing_shares * (current_price - stop)
    remaining_risk = max(risk_budget - existing_risk, ZERO)
    risk_capacity = remaining_risk / risk_rate

    max_position_value = account_value * concentration_pct / Decimal("100")
    existing_position_value = existing_shares * current_price
    concentration_capacity = max(max_position_value - existing_position_value, ZERO)
    cash_capacity = max(cash, ZERO)
    capacities = {
        "cash": cash_capacity,
        "concentration": concentration_capacity,
        "risk": risk_capacity,
    }
    budget = min(capacities.values())
    binding = [
        name for name, capacity in capacities.items()
        if (capacity - budget).copy_abs() <= CENT
    ]

    whole_shares = plan.get("whole_shares", True)
    if not isinstance(whole_shares, bool):
        raise PositionManagerError("plan.whole_shares must be true or false")
    planned_rows = []
    planned_shares = ZERO
    planned_notional = ZERO
    planned_risk = ZERO
    for index, (price, weight) in enumerate(normalized, start=1):
        allocation = budget * weight
        quantity = _shares(allocation / price, whole_shares)
        notional = quantity * price
        risk = quantity * (price - stop)
        planned_shares += quantity
        planned_notional += notional
        planned_risk += risk
        planned_rows.append({
            "index": index,
            "price": _float(price),
            "weight_pct": _float(weight * Decimal("100")),
            "shares": int(quantity) if whole_shares else _float(quantity, FOUR_DP),
            "notional": _float(notional),
            "risk_to_stop": _float(risk),
        })

    post_position_value = existing_position_value + planned_notional
    post_risk = existing_risk + planned_risk
    warnings = []
    if existing_risk > risk_budget + CENT:
        warnings.append("EXISTING_POSITION_EXCEEDS_RISK_CAP")
    if existing_position_value > max_position_value + CENT:
        warnings.append("EXISTING_POSITION_EXCEEDS_CONCENTRATION_CAP")
    if planned_shares == ZERO:
        warnings.append("NO_CAPACITY_FOR_ADDS")

    return {
        "stop_price": _float(stop),
        "max_account_risk_pct": _float(risk_pct),
        "max_position_pct": _float(concentration_pct),
        "binding_constraints": binding,
        "available_capacity": {name: _float(value) for name, value in capacities.items()},
        "existing_risk_to_stop": _float(existing_risk),
        "planned_risk_to_stop": _float(planned_risk),
        "planned_shares": int(planned_shares) if whole_shares else _float(planned_shares, FOUR_DP),
        "planned_notional": _float(planned_notional),
        "post_plan_shares": (
            int(existing_shares + planned_shares)
            if whole_shares and existing_shares == existing_shares.to_integral_value()
            else _float(existing_shares + planned_shares, FOUR_DP)
        ),
        "post_plan_position_pct": _float(post_position_value / account_value * Decimal("100")),
        "post_plan_risk_pct": _float(post_risk / account_value * Decimal("100")),
        "tranches": planned_rows,
    }, warnings


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one complete ledger and optional staged-add plan."""
    if not isinstance(data, dict):
        raise PositionManagerError("input must be a JSON object")
    symbol = str(data.get("symbol", "")).strip().upper()
    if not symbol:
        raise PositionManagerError("symbol is required")
    current_price = _number(data.get("current_price"), "current_price")
    benchmark_price = _number(
        data.get("benchmark_entry_price"),
        "benchmark_entry_price",
    )
    ledger = _replay_ledger(data)

    shares = ledger["shares"]
    cash = ledger["cash"]
    cost_basis = ledger["cost_basis"]
    starting_cash = ledger["starting_cash"]
    current_value = shares * current_price
    ending_value = cash + current_value
    unrealized = current_value - cost_basis
    total_pnl = ending_value - starting_cash
    total_return = total_pnl / starting_cash * Decimal("100")

    benchmark_shares = starting_cash / benchmark_price
    benchmark_value = benchmark_shares * current_price
    benchmark_return = (benchmark_value - starting_cash) / starting_cash * Decimal("100")
    alpha = total_return - benchmark_return

    average_cost = cost_basis / shares if shares else ZERO
    warnings = ["SHARE_COUNT_IS_NOT_RETURN"]
    if alpha < -EPSILON:
        warnings.append("ROLLING_UNDERPERFORMED_BUY_HOLD")

    output: dict[str, Any] = {
        "symbol": symbol,
        "accounting_method": "average_cost_not_tax_lots",
        "ledger": {
            "starting_cash": _float(starting_cash),
            "ending_cash": _float(cash),
            "ending_shares": _float(shares, FOUR_DP),
            "average_cost": _float(average_cost, FOUR_DP),
            "remaining_cost_basis": _float(cost_basis),
            "realized_pnl": _float(ledger["realized"]),
            "unrealized_pnl": _float(unrealized),
            "fees_paid": _float(ledger["fees_paid"]),
            "transaction_count": ledger["transaction_count"],
        },
        "performance": {
            "current_price": _float(current_price),
            "ending_value": _float(ending_value),
            "total_pnl": _float(total_pnl),
            "total_return_pct": _float(total_return),
            "buy_hold_ending_value": _float(benchmark_value),
            "buy_hold_return_pct": _float(benchmark_return),
            "alpha_vs_buy_hold_pct_points": _float(alpha),
        },
        "plan": None,
        "warnings": warnings,
    }

    if data.get("plan") is not None:
        if not isinstance(data["plan"], dict):
            raise PositionManagerError("plan must be an object")
        plan_output, plan_warnings = _build_plan(
            data["plan"],
            account_value=ending_value,
            cash=cash,
            current_price=current_price,
            existing_shares=shares,
        )
        output["plan"] = plan_output
        output["warnings"].extend(plan_warnings)

    return output


def _print_human(result: dict[str, Any]) -> None:
    ledger = result["ledger"]
    perf = result["performance"]
    print(f"ROLLING POSITION MANAGER — {result['symbol']}")
    print(
        f"Result: {perf['ending_value']:,.2f} | return {perf['total_return_pct']:+.2f}% "
        f"vs buy-and-hold {perf['buy_hold_return_pct']:+.2f}% "
        f"(alpha {perf['alpha_vs_buy_hold_pct_points']:+.2f} pts)"
    )
    print(
        f"Ledger: cash {ledger['ending_cash']:,.2f} | shares {ledger['ending_shares']:,.4f} "
        f"| average cost {ledger['average_cost']:,.4f} | fees {ledger['fees_paid']:,.2f}"
    )
    print(
        f"P&L: realized {ledger['realized_pnl']:+,.2f} | "
        f"unrealized {ledger['unrealized_pnl']:+,.2f}"
    )

    plan = result.get("plan")
    if plan:
        constraints = ", ".join(plan["binding_constraints"])
        print(
            f"Plan: {plan['planned_shares']} shares / {plan['planned_notional']:,.2f} "
            f"| binding: {constraints} | post-position {plan['post_plan_position_pct']:.2f}% "
            f"| post-risk {plan['post_plan_risk_pct']:.2f}%"
        )
        for tranche in plan["tranches"]:
            print(
                f"  {tranche['index']}. buy {tranche['shares']} @ {tranche['price']:.2f} "
                f"({tranche['weight_pct']:.1f}% weight; risk {tranche['risk_to_stop']:,.2f})"
            )

    if result["warnings"]:
        print("Warnings: " + ", ".join(result["warnings"]))
    print(
        "Advisory math only: levels are user-supplied, average cost is not tax-lot accounting, "
        "and no order was placed."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="local JSON ledger and optional tranche plan")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as handle:
            data = json.load(handle)
        result = evaluate(data)
    except (OSError, json.JSONDecodeError, PositionManagerError) as exc:
        print(f"position_manager: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(desk_log.run(main))
