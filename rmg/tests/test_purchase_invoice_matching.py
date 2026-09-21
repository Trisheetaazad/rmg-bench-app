"""Unit tests for the three-way invoice matching rule.

The rule under test is:

	expected amount = accepted quantity x purchase order rate

``calculate_match`` is deliberately kept free of database access, so these run
in milliseconds and need no site.
"""

from unittest import TestCase
from unittest.mock import patch

from rmg.rmg_management.purchase_invoice_matching import calculate_match, validate
from rmg.tests.sample_test_documents import (
	make_purchase_invoice,
	make_purchase_order,
	make_purchase_receipt,
)

PO_RATE = 10.0
RECEIVED_QTY = 10.0


def run_validate(claimed_amount, rejected_qty=0.0, po_rate=PO_RATE, received_qty=RECEIVED_QTY):
	"""Run the real ``validate`` handler and return (invoice, msgprint mock)."""
	po = make_purchase_order(rate=po_rate)
	receipt = make_purchase_receipt(received_qty=received_qty, rejected_qty=rejected_qty)
	invoice = make_purchase_invoice(claimed_amount)

	with (
		patch(
			"rmg.rmg_management.purchase_invoice_matching.frappe.get_doc",
			side_effect=[po, receipt],
		),
		patch("rmg.rmg_management.purchase_invoice_matching.frappe.msgprint") as msgprint,
	):
		validate(invoice)

	return invoice, msgprint


class TestAcceptedQuantity(TestCase):
	"""``qty`` on a Purchase Receipt Item is already the Accepted Quantity."""

	def test_accepted_quantity_is_received_minus_rejected(self):
		receipt = make_purchase_receipt(received_qty=5000, rejected_qty=200)
		row = receipt.items[0]

		self.assertEqual(row.qty, 4800)
		self.assertEqual(row.rejected_qty, 200)
		self.assertEqual(row.received_qty, row.qty + row.rejected_qty)

	def test_rejection_is_deducted_exactly_once(self):
		"""Guards the bug where the QC rejection was subtracted twice."""
		po = make_purchase_order(rate=250.0)
		receipt = make_purchase_receipt(received_qty=5000, rejected_qty=200)

		expected_amount, _difference = calculate_match(po, receipt, claimed_amount=0)

		self.assertEqual(expected_amount, 4800 * 250.0)


class TestPurchaseInvoiceMatching(TestCase):
	def test_full_delivery_is_matched(self):
		invoice, msgprint = run_validate(claimed_amount=100)

		self.assertEqual(invoice.custom_match_status, "Matched")
		self.assertEqual(invoice.custom_difference_amount, 0)
		msgprint.assert_not_called()

	def test_rounding_difference_within_tolerance_is_matched(self):
		invoice, msgprint = run_validate(claimed_amount=100.005)

		self.assertEqual(invoice.custom_match_status, "Matched")
		msgprint.assert_not_called()

	def test_invoice_without_references_is_left_alone(self):
		po = make_purchase_order()
		receipt = make_purchase_receipt()
		invoice = make_purchase_invoice(100)
		invoice.custom_po_no = None

		with (
			patch(
				"rmg.rmg_management.purchase_invoice_matching.frappe.get_doc",
				side_effect=[po, receipt],
			),
			patch("rmg.rmg_management.purchase_invoice_matching.frappe.msgprint") as msgprint,
		):
			validate(invoice)

		self.assertIsNone(invoice.custom_match_status)
		msgprint.assert_not_called()


class TestPurchaseInvoiceMatchingDiscrepancies(TestCase):
	def test_partial_rejection_creates_overpayment_discrepancy(self):
		"""10 received, 2 rejected at QC, supplier still bills for all 10."""
		invoice, msgprint = run_validate(claimed_amount=100, rejected_qty=2)

		self.assertEqual(invoice.custom_match_status, "Discrepancy")
		self.assertEqual(invoice.custom_difference_amount, 20)
		msgprint.assert_called_once()
		self.assertIn("expected 80.0", msgprint.call_args.args[0])

	def test_underbilling_is_also_held_for_review(self):
		invoice, msgprint = run_validate(claimed_amount=80)

		self.assertEqual(invoice.custom_match_status, "Discrepancy")
		self.assertEqual(invoice.custom_difference_amount, -20)
		msgprint.assert_called_once()


class TestPurchaseInvoiceMatchingRateMismatch(TestCase):
	def test_rate_mismatch_creates_discrepancy(self):
		invoice, msgprint = run_validate(claimed_amount=120)

		self.assertEqual(invoice.custom_match_status, "Discrepancy")
		self.assertEqual(invoice.custom_difference_amount, 20)
		msgprint.assert_called_once()
		self.assertIn("difference 20.0", msgprint.call_args.args[0])
