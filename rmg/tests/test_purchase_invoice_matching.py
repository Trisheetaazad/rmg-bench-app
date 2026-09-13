from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from rmg.rmg_management.purchase_invoice_matching import validate


def make_document(**fields):
	return SimpleNamespace(**fields)


def make_match_documents(claimed_amount, rejected_quantity=0, po_rate=10):
	po = make_document(items=[make_document(item_code="ITEM-001", rate=po_rate)])
	receipt = make_document(
		items=[make_document(item_code="ITEM-001", qty=10, rejected_qty=rejected_quantity)]
	)
	invoice = make_document(
		custom_po_no="PO-001",
		custom_po_receipt_="PR-001",
		grand_total=claimed_amount,
		custom_match_status=None,
		custom_difference_amount=None,
	)
	return po, receipt, invoice


class TestPurchaseInvoiceMatching(TestCase):
	def test_full_delivery_is_matched(self):
		po, receipt, invoice = make_match_documents(claimed_amount=100)

		with patch(
			"rmg.rmg_management.purchase_invoice_matching.frappe.get_doc",
			side_effect=[po, receipt],
		), patch("rmg.rmg_management.purchase_invoice_matching.frappe.msgprint") as msgprint:
			validate(invoice)

		self.assertEqual(invoice.custom_match_status, "Matched")
		self.assertEqual(invoice.custom_difference_amount, 0)
		msgprint.assert_not_called()


class TestPurchaseInvoiceMatchingDiscrepancies(TestCase):
	def test_partial_rejection_creates_overpayment_discrepancy(self):
		po, receipt, invoice = make_match_documents(claimed_amount=100, rejected_quantity=2)

		with patch(
			"rmg.rmg_management.purchase_invoice_matching.frappe.get_doc",
			side_effect=[po, receipt],
		), patch("rmg.rmg_management.purchase_invoice_matching.frappe.msgprint") as msgprint:
			validate(invoice)

		self.assertEqual(invoice.custom_match_status, "Discrepancy")
		self.assertEqual(invoice.custom_difference_amount, 20)
		msgprint.assert_called_once()
		self.assertIn("expected 80.0", msgprint.call_args.args[0])


class TestPurchaseInvoiceMatchingRateMismatch(TestCase):
	def test_rate_mismatch_creates_discrepancy(self):
		po, receipt, invoice = make_match_documents(claimed_amount=120)

		with patch(
			"rmg.rmg_management.purchase_invoice_matching.frappe.get_doc",
			side_effect=[po, receipt],
		), patch("rmg.rmg_management.purchase_invoice_matching.frappe.msgprint") as msgprint:
			validate(invoice)

		self.assertEqual(invoice.custom_match_status, "Discrepancy")
		self.assertEqual(invoice.custom_difference_amount, 20)
		msgprint.assert_called_once()
		self.assertIn("difference 20.0", msgprint.call_args.args[0])
