import frappe
from frappe import _
from frappe.utils import flt


PAYMENT_ENTRY_VOUCHER_TYPES = ("Contra Entry", "Bank Entry")
ACTIVE_ALLOCATION_STATUSES = ("Allocated", "Closed")


def validate_payment_entry(doc, method=None):
	if doc.get("custom_voucher_type") not in PAYMENT_ENTRY_VOUCHER_TYPES:
		frappe.throw(_("Voucher Type must be selected as Contra Entry or Bank Entry."))

	if not doc.get("mode_of_payment"):
		frappe.throw(_("Mode of Payment is mandatory."))

	if "cheque" in (doc.get("mode_of_payment") or "").lower():
		if not doc.get("custom_cheque_withdrawer"):
			frappe.throw(_("Cheque Withdrawer is mandatory for cheque payments."))
		if not doc.get("custom_withdrawer_designation"):
			frappe.throw(_("Withdrawer Designation is mandatory for cheque payments."))


def recalculate_lc_utilization(lc_name):
	if not frappe.db.exists("Letter Of Credit", lc_name):
		return

	lc_total = flt(frappe.db.get_value("Letter Of Credit", lc_name, "total_value"))
	utilized_amount = flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(allocated_amount), 0)
			FROM `tabLC Allocation`
			WHERE letter_of_credit = %s
				AND allocation_status IN %s
			""",
			(lc_name, ACTIVE_ALLOCATION_STATUSES),
		)[0][0]
	)
	remaining_amount = max(lc_total - utilized_amount, 0)
	utilization_percent = (utilized_amount / lc_total * 100) if lc_total else 0
	current_status, docstatus = frappe.db.get_value("Letter Of Credit", lc_name, ["status", "docstatus"])
	if current_status == "Closed":
		status = "Closed"
	elif docstatus == 0:
		status = "Draft"
	elif lc_total and utilized_amount >= lc_total:
		status = "Exhausted"
	else:
		status = "Open"

	frappe.db.set_value(
		"Letter Of Credit",
		lc_name,
		{
			"status": status,
			"custom_utilized_amount": utilized_amount,
			"custom_remaining_amount": remaining_amount,
			"custom_utilization_percent": utilization_percent,
		},
		update_modified=False,
	)


def recalculate_all_lc_utilization():
	for lc_name in frappe.get_all("Letter Of Credit", pluck="name"):
		recalculate_lc_utilization(lc_name)


def update_lc_utilization(doc, method=None):
	recalculate_lc_utilization(doc.letter_of_credit)


def refresh_lc_utilization(doc, method=None):
	"""Keep a credit's own utilisation fields correct from the moment it exists.

	Without this a newly created Letter Of Credit shows a remaining amount of
	zero until some allocation happens to trigger a recalculation.
	"""
	recalculate_lc_utilization(doc.name)


def remove_lc_utilization(doc, method=None):
	recalculate_lc_utilization(doc.letter_of_credit)
