#!/usr/bin/env python
"""Terminal demonstration of the two control points in the RMG system.

Runs the real production functions — ``purchase_invoice_matching.validate`` and
``finance_controls.validate_payment_entry`` — against a set of prepared
scenarios and prints what a user would see on screen for each one, including the
exact prompt text raised by the engine.

	python apps/rmg/rmg/tests/demo_scenarios.py
	python apps/rmg/rmg/tests/demo_scenarios.py --no-color
	python apps/rmg/rmg/tests/demo_scenarios.py --section match
	python apps/rmg/rmg/tests/demo_scenarios.py --section payment

Exits non-zero if any scenario does not behave as documented, so the same file
is usable as a smoke test as well as a demonstration.
"""

import argparse
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Frappe resolves its log directory relative to the bench's sites folder, so run
# from there and the demo works no matter where it is invoked from.
BENCH_ROOT = Path(__file__).resolve().parents[4]
if (BENCH_ROOT / "sites").is_dir():
	os.chdir(BENCH_ROOT / "sites")

from rmg.rmg_management.finance_controls import validate_payment_entry  # noqa: E402
from rmg.rmg_management.purchase_invoice_matching import validate as validate_invoice  # noqa: E402
from rmg.tests.sample_test_documents import (  # noqa: E402
	make_payment_entry,
	make_purchase_invoice,
	make_purchase_order,
	make_purchase_receipt,
)

WIDTH = 78


class Palette:
	def __init__(self, enabled):
		self.enabled = enabled

	def _wrap(self, code, text):
		return f"\033[{code}m{text}\033[0m" if self.enabled else text

	def bold(self, text):
		return self._wrap("1", text)

	def green(self, text):
		return self._wrap("32", text)

	def red(self, text):
		return self._wrap("31", text)

	def yellow(self, text):
		return self._wrap("33", text)

	def dim(self, text):
		return self._wrap("2", text)


class PaymentRefused(Exception):
	"""Stands in for the ``frappe.throw`` that stops a Payment Entry."""


def money(amount):
	return f"BDT {amount:>14,.2f}"


def banner(colour, title):
	print()
	print(colour.bold("=" * WIDTH))
	print(colour.bold(f"  {title}"))
	print(colour.bold("=" * WIDTH))


def scenario_header(colour, number, title):
	print()
	print(colour.bold(f" {number}  {title}"))
	print(colour.dim(" " + "-" * (WIDTH - 2)))


# ---------------------------------------------------------------------------
# Section 1: three-way invoice matching
# ---------------------------------------------------------------------------


def run_match(po_rate, ordered_qty, received_qty, rejected_qty, claimed_amount, linked=True):
	"""Run the real matching engine and return (invoice, captured prompt)."""
	po = make_purchase_order(rate=po_rate, qty=ordered_qty)
	receipt = make_purchase_receipt(received_qty=received_qty, rejected_qty=rejected_qty)
	invoice = make_purchase_invoice(claimed_amount)
	if not linked:
		invoice.custom_po_no = None

	captured = {}

	def fake_msgprint(message, title=None, indicator=None, **kwargs):
		captured["message"] = str(message)
		captured["title"] = str(title)
		captured["indicator"] = indicator

	with patch(
		"rmg.rmg_management.purchase_invoice_matching.frappe.get_doc",
		side_effect=[po, receipt],
	), patch(
		"rmg.rmg_management.purchase_invoice_matching.frappe.msgprint",
		side_effect=fake_msgprint,
	):
		validate_invoice(invoice)

	return invoice, captured


MATCH_SCENARIOS = [
	{
		"title": "Full delivery, nothing rejected — supplier bills correctly",
		"story": "The mill ships 5,000 m of fabric, QC passes all of it, the invoice agrees.",
		"po_rate": 250.0,
		"ordered_qty": 5000.0,
		"received_qty": 5000.0,
		"rejected_qty": 0.0,
		"claimed_amount": 1_250_000.00,
		"expect_status": "Matched",
		"expect_difference": 0,
	},
	{
		"title": "Partial rejection at QC — the overpayment this project prevents",
		"story": "200 m fail inspection for shading, but the supplier bills the full despatch.",
		"po_rate": 250.0,
		"ordered_qty": 5000.0,
		"received_qty": 5000.0,
		"rejected_qty": 200.0,
		"claimed_amount": 1_250_000.00,
		"expect_status": "Discrepancy",
		"expect_difference": 50_000.00,
	},
	{
		"title": "Rate mismatch — correct quantity billed at the wrong rate",
		"story": "All 5,000 m are accepted, but the invoice is raised at BDT 260 instead of the agreed 250.",
		"po_rate": 250.0,
		"ordered_qty": 5000.0,
		"received_qty": 5000.0,
		"rejected_qty": 0.0,
		"claimed_amount": 1_300_000.00,
		"expect_status": "Discrepancy",
		"expect_difference": 50_000.00,
	},
	{
		"title": "Supplier under-bills — a difference in the company's favour",
		"story": "Still held for review: any unexplained difference is a data problem, whichever way it points.",
		"po_rate": 250.0,
		"ordered_qty": 5000.0,
		"received_qty": 5000.0,
		"rejected_qty": 0.0,
		"claimed_amount": 1_200_000.00,
		"expect_status": "Discrepancy",
		"expect_difference": -50_000.00,
	},
	{
		"title": "Rounding difference inside tolerance — passes",
		"story": "A half-paisa difference is not a discrepancy; the engine ignores anything under BDT 0.01.",
		"po_rate": 250.0,
		"ordered_qty": 5000.0,
		"received_qty": 5000.0,
		"rejected_qty": 0.0,
		"claimed_amount": 1_250_000.005,
		"expect_status": "Matched",
		"expect_difference": 0,
	},
]


def demo_matching(colour):
	banner(colour, "SECTION 1  —  THREE-WAY INVOICE MATCHING")
	print(colour.dim("  rule:  expected amount = accepted quantity x purchase order rate"))
	print(colour.dim("  fires: Purchase Invoice -> validate  (server side, hooks.py doc_events)"))

	failures = 0

	for index, case in enumerate(MATCH_SCENARIOS, start=1):
		scenario_header(colour, f"1.{index}", case["title"])
		print(colour.dim(f"      {case['story']}"))
		print()

		accepted_qty = case["received_qty"] - case["rejected_qty"]
		expected_amount = accepted_qty * case["po_rate"]

		print(f"      Purchase Order     {case['ordered_qty']:>10,.0f} m ordered @ {money(case['po_rate'])}")
		print(
			f"      Purchase Receipt   {case['received_qty']:>10,.0f} m received, "
			f"{case['rejected_qty']:,.0f} rejected, {accepted_qty:,.0f} accepted"
		)
		print(f"      Supplier claims    {money(case['claimed_amount'])}")
		print(f"      System expects     {money(expected_amount)}   ({accepted_qty:,.0f} x {case['po_rate']:,.2f})")
		print()

		invoice, prompt = run_match(
			case["po_rate"],
			case["ordered_qty"],
			case["received_qty"],
			case["rejected_qty"],
			case["claimed_amount"],
		)

		status = invoice.custom_match_status
		tint = colour.green if status == "Matched" else colour.red
		print(f"      Three-Way Match Status      {tint(colour.bold(str(status)))}")
		print(f"      Three-Way Match Difference  {money(float(invoice.custom_difference_amount or 0))}")
		print()

		if prompt:
			print(colour.red(f'      ON SCREEN  [{prompt["indicator"]}]  {prompt["title"]}'))
			print(colour.red(f'                 "{prompt["message"]}"'))
			print(colour.dim("                 Invoice is held for procurement review."))
		else:
			print(colour.green("      ON SCREEN  (no prompt — the invoice saves quietly)"))
			print(colour.dim("                 Invoice is cleared to go to Finance for payment."))

		ok = status == case["expect_status"] and abs(
			float(invoice.custom_difference_amount or 0) - case["expect_difference"]
		) < 0.01
		failures += 0 if ok else 1
		print()
		print("      " + (colour.green("PASS") if ok else colour.red("FAIL")) + colour.dim(f"  expected {case['expect_status']}"))

	# The engine must stay out of the way when the invoice is not linked up.
	scenario_header(colour, "1.6", "Invoice with no PO / Receipt reference — engine stays silent")
	print(colour.dim("      Nothing to compare against, so no status is written and no prompt is shown."))
	print()
	invoice, prompt = run_match(250.0, 5000.0, 5000.0, 0.0, 1_250_000.00, linked=False)
	silent = invoice.custom_match_status is None and not prompt
	print(f"      Three-Way Match Status      {colour.dim(str(invoice.custom_match_status))}")
	print(colour.green("      ON SCREEN  (no prompt)") if silent else colour.red("      unexpected output"))
	failures += 0 if silent else 1
	print()
	print("      " + (colour.green("PASS") if silent else colour.red("FAIL")) + colour.dim("  expected no match attempted"))

	return failures


# ---------------------------------------------------------------------------
# Section 2: payment entry financial controls
# ---------------------------------------------------------------------------


def run_payment(**fields):
	"""Run the real payment control and return the refusal message, if any."""
	doc = make_payment_entry(**fields)

	def fake_throw(message, *args, **kwargs):
		raise PaymentRefused(str(message))

	try:
		with patch("rmg.rmg_management.finance_controls.frappe.throw", side_effect=fake_throw):
			validate_payment_entry(doc)
	except PaymentRefused as refusal:
		return str(refusal)

	return None


PAYMENT_SCENARIOS = [
	{
		"title": "Bank Entry paid by bank draft — complete",
		"fields": {"voucher_type": "Bank Entry", "mode_of_payment": "Bank Draft"},
		"expect_refused": False,
	},
	{
		"title": "Contra Entry in cash — complete",
		"fields": {"voucher_type": "Contra Entry", "mode_of_payment": "Cash"},
		"expect_refused": False,
	},
	{
		"title": "Cheque with both withdrawer fields filled — complete",
		"fields": {
			"voucher_type": "Bank Entry",
			"mode_of_payment": "Cheque",
			"cheque_withdrawer": "Rafiqul Islam",
			"withdrawer_designation": "Accounts Officer",
		},
		"expect_refused": False,
	},
	{
		"title": "Cheque issued with no withdrawer name — REFUSED",
		"fields": {
			"voucher_type": "Bank Entry",
			"mode_of_payment": "Cheque",
			"cheque_withdrawer": None,
			"withdrawer_designation": "Accounts Officer",
		},
		"expect_refused": True,
	},
	{
		"title": "Cheque issued with no withdrawer designation — REFUSED",
		"fields": {
			"voucher_type": "Bank Entry",
			"mode_of_payment": "Cheque",
			"cheque_withdrawer": "Rafiqul Islam",
			"withdrawer_designation": None,
		},
		"expect_refused": True,
	},
	{
		"title": "Voucher type left blank — REFUSED",
		"fields": {"voucher_type": None, "mode_of_payment": "Cheque"},
		"expect_refused": True,
	},
	{
		"title": "Voucher type outside the permitted list — REFUSED",
		"fields": {"voucher_type": "Journal Entry", "mode_of_payment": "Cash"},
		"expect_refused": True,
	},
	{
		"title": "Mode of payment left blank — REFUSED",
		"fields": {"voucher_type": "Bank Entry", "mode_of_payment": None},
		"expect_refused": True,
	},
	{
		"title": "Mode of payment 'Bank Cheque', withdrawer blank — REFUSED",
		"fields": {
			"voucher_type": "Bank Entry",
			"mode_of_payment": "Bank CHEQUE",
			"cheque_withdrawer": None,
		},
		"expect_refused": True,
	},
]


def demo_payments(colour):
	banner(colour, "SECTION 2  —  PAYMENT ENTRY FINANCIAL CONTROLS")
	print(colour.dim("  rule:  voucher type + mode of payment always; withdrawer details when a cheque"))
	print(colour.dim("  fires: Payment Entry -> validate  (server side; the client script mirrors it)"))

	failures = 0

	for index, case in enumerate(PAYMENT_SCENARIOS, start=1):
		scenario_header(colour, f"2.{index}", case["title"])

		fields = case["fields"]
		print(f"      Voucher Type            {fields.get('voucher_type') or colour.dim('(blank)')}")
		print(f"      Mode of Payment         {fields.get('mode_of_payment') or colour.dim('(blank)')}")
		if "cheque" in str(fields.get("mode_of_payment") or "").lower():
			print(f"      Cheque Withdrawer       {fields.get('cheque_withdrawer') or colour.dim('(blank)')}")
			print(f"      Withdrawer Designation  {fields.get('withdrawer_designation') or colour.dim('(blank)')}")
		print()

		refusal = run_payment(**fields)

		if refusal:
			print(colour.red(colour.bold("      SUBMISSION REFUSED")))
			print(colour.red(f'      ON SCREEN  "{refusal}"'))
			print(colour.dim("                 No ledger entry is posted."))
		else:
			print(colour.green(colour.bold("      SUBMISSION ACCEPTED")))
			print(colour.dim("                 Payment posts to the ledger."))

		ok = bool(refusal) == case["expect_refused"]
		failures += 0 if ok else 1
		print()
		expected = "refusal" if case["expect_refused"] else "acceptance"
		print("      " + (colour.green("PASS") if ok else colour.red("FAIL")) + colour.dim(f"  expected {expected}"))

	return failures


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--no-color", action="store_true", help="plain output, for projectors and log files")
	parser.add_argument(
		"--section",
		choices=["match", "payment", "all"],
		default="all",
		help="run only one section of the demonstration",
	)
	args = parser.parse_args()

	colour = Palette(enabled=not args.no_color and sys.stdout.isatty())

	print()
	print(colour.bold("RMG MANAGEMENT — SUPPLIER INVOICE AND PAYMENT CONTROL DEMONSTRATION"))
	print(colour.dim("Every result below is produced by the same server-side code that runs on the site."))

	total_scenarios = 0
	failures = 0

	if args.section in ("match", "all"):
		failures += demo_matching(colour)
		total_scenarios += len(MATCH_SCENARIOS) + 1
	if args.section in ("payment", "all"):
		failures += demo_payments(colour)
		total_scenarios += len(PAYMENT_SCENARIOS)

	banner(colour, "SUMMARY")
	passed = total_scenarios - failures
	line = f"  {passed} of {total_scenarios} scenarios behaved exactly as documented."
	print(colour.green(colour.bold(line)) if not failures else colour.red(colour.bold(line)))
	print()

	return 1 if failures else 0


if __name__ == "__main__":
	raise SystemExit(main())
