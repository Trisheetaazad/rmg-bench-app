import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt


PO_RECEIPT_FIELD = "custom_po_receipt_"


def ensure_custom_fields():
	create_custom_fields(
		{
			"Payment Entry": [
				{
					"fieldname": "custom_voucher_type",
					"label": "Voucher Type",
					"fieldtype": "Select",
					"options": "Contra Entry\nBank Entry",
					"reqd": 1,
					"insert_after": "payment_type",
				},
				{
					"fieldname": "custom_cheque_withdrawer",
					"label": "Cheque Withdrawer",
					"fieldtype": "Data",
					"insert_after": "mode_of_payment",
				},
				{
					"fieldname": "custom_withdrawer_designation",
					"label": "Withdrawer Designation",
					"fieldtype": "Data",
					"insert_after": "custom_cheque_withdrawer",
				},
			],
			"Letter Of Credit": [
				{
					"fieldname": "custom_utilized_amount",
					"label": "Utilized Amount",
					"fieldtype": "Currency",
					"read_only": 1,
					"insert_after": "total_value",
				},
				{
					"fieldname": "custom_remaining_amount",
					"label": "Remaining Amount",
					"fieldtype": "Currency",
					"read_only": 1,
					"insert_after": "custom_utilized_amount",
				},
				{
					"fieldname": "custom_utilization_percent",
					"label": "Utilization Percent",
					"fieldtype": "Percent",
					"read_only": 1,
					"insert_after": "custom_remaining_amount",
				},
			],
			"Purchase Invoice": [
				{
					"fieldname": "custom_match_status",
					"label": "Three-Way Match Status",
					"fieldtype": "Select",
					"options": "Matched\nDiscrepancy",
					"read_only": 1,
					"insert_after": PO_RECEIPT_FIELD,
				},
				{
					"fieldname": "custom_difference_amount",
					"label": "Three-Way Match Difference",
					"fieldtype": "Currency",
					"read_only": 1,
					"insert_after": "custom_match_status",
				},
			]
		}
	)

	from rmg.rmg_management.finance_controls import recalculate_all_lc_utilization

	recalculate_all_lc_utilization()


def calculate_match(po, receipt, claimed_amount):
	"""Return the expected amount and difference for a PO, receipt, and invoice claim."""
	expected_amount = 0.0

	for po_item in po.items:
		accepted_quantity = sum(
			flt(receipt_item.qty) - flt(receipt_item.rejected_qty)
			for receipt_item in receipt.items
			if receipt_item.item_code == po_item.item_code
		)
		expected_amount += accepted_quantity * flt(po_item.rate)

	difference = round(flt(claimed_amount) - expected_amount, 2)
	return expected_amount, difference


def validate(doc, method=None):
	"""Compare the invoice claim with accepted receipt quantity at the PO rate."""
	if not doc.custom_po_no or not getattr(doc, PO_RECEIPT_FIELD, None):
		return

	po = frappe.get_doc("Purchase Order", doc.custom_po_no)
	receipt = frappe.get_doc("Purchase Receipt", getattr(doc, PO_RECEIPT_FIELD))
	expected_amount, difference = calculate_match(po, receipt, doc.grand_total)

	if abs(difference) < 0.01:
		doc.custom_match_status = "Matched"
		doc.custom_difference_amount = 0
		return

	doc.custom_match_status = "Discrepancy"
	doc.custom_difference_amount = difference
	frappe.msgprint(
		_("Invoice does not match. Claimed {0}, expected {1}, difference {2}.").format(
			doc.grand_total or 0.0, expected_amount, difference
		),
		title=_("Three-Way Match Failed"),
		indicator="red",
	)
