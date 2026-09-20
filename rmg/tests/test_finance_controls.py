"""Unit tests for the Payment Entry financial controls.

These cover every branch of ``validate_payment_entry``: the payments that are
allowed through, and each of the five conditions that refuse a payment before it
can post to the ledger. No database is required.
"""

from unittest import TestCase
from unittest.mock import patch

from rmg.rmg_management.finance_controls import validate_payment_entry
from rmg.tests.sample_test_documents import make_payment_entry


class PaymentRefused(Exception):
	"""Raised in place of ``frappe.throw`` so the message can be asserted on."""


def run_validation(doc):
	"""Run the real control, turning a refusal into ``PaymentRefused``."""

	def fake_throw(message, *args, **kwargs):
		raise PaymentRefused(str(message))

	with patch("rmg.rmg_management.finance_controls.frappe.throw", side_effect=fake_throw):
		validate_payment_entry(doc)


class TestPaymentEntryAccepted(TestCase):
	def test_bank_entry_without_cheque_is_accepted(self):
		doc = make_payment_entry(voucher_type="Bank Entry", mode_of_payment="Bank Draft")

		run_validation(doc)

	def test_contra_entry_is_accepted(self):
		doc = make_payment_entry(voucher_type="Contra Entry", mode_of_payment="Cash")

		run_validation(doc)

	def test_cheque_with_complete_withdrawer_details_is_accepted(self):
		doc = make_payment_entry(
			voucher_type="Bank Entry",
			mode_of_payment="Cheque",
			cheque_withdrawer="Rafiqul Islam",
			withdrawer_designation="Accounts Officer",
		)

		run_validation(doc)


class TestPaymentEntryRefused(TestCase):
	def test_missing_voucher_type_is_refused(self):
		doc = make_payment_entry(voucher_type=None)

		with self.assertRaises(PaymentRefused) as refusal:
			run_validation(doc)

		self.assertIn("Voucher Type", str(refusal.exception))

	def test_voucher_type_outside_the_allowed_list_is_refused(self):
		doc = make_payment_entry(voucher_type="Journal Entry")

		with self.assertRaises(PaymentRefused) as refusal:
			run_validation(doc)

		self.assertIn("Contra Entry or Bank Entry", str(refusal.exception))

	def test_missing_mode_of_payment_is_refused(self):
		doc = make_payment_entry(mode_of_payment=None)

		with self.assertRaises(PaymentRefused) as refusal:
			run_validation(doc)

		self.assertIn("Mode of Payment is mandatory", str(refusal.exception))

	def test_cheque_without_withdrawer_is_refused(self):
		doc = make_payment_entry(
			mode_of_payment="Cheque",
			cheque_withdrawer=None,
			withdrawer_designation="Accounts Officer",
		)

		with self.assertRaises(PaymentRefused) as refusal:
			run_validation(doc)

		self.assertIn("Cheque Withdrawer is mandatory", str(refusal.exception))

	def test_cheque_without_designation_is_refused(self):
		doc = make_payment_entry(
			mode_of_payment="Cheque",
			cheque_withdrawer="Rafiqul Islam",
			withdrawer_designation=None,
		)

		with self.assertRaises(PaymentRefused) as refusal:
			run_validation(doc)

		self.assertIn("Withdrawer Designation is mandatory", str(refusal.exception))

	def test_cheque_detection_is_case_insensitive(self):
		"""'Bank Cheque' must trigger the same control as 'Cheque'."""
		doc = make_payment_entry(mode_of_payment="Bank CHEQUE", cheque_withdrawer=None)

		with self.assertRaises(PaymentRefused) as refusal:
			run_validation(doc)

		self.assertIn("Cheque Withdrawer is mandatory", str(refusal.exception))
