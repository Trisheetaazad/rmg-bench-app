# Copyright (c) 2026, Trisheeta and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LCAllocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allocated_amount: DF.Currency
		allocation_status: DF.Literal["Draft", "Allocated", "Released", "Closed"]
		currency: DF.Link | None
		exchange_rate: DF.Float
		letter_of_credit: DF.Link
		notes: DF.Text | None
		style_reference: DF.Link | None
	# end: auto-generated types

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allocation_status: DF.Literal["Draft", "Allocated", "Released", "Closed"]
		allocated_amount: DF.Currency
		currency: DF.Link | None
		exchange_rate: DF.Float
		letter_of_credit: DF.Link
		notes: DF.Text | None
		style_reference: DF.Link | None

	def validate(self):
		if self.allocated_amount is None or self.allocated_amount <= 0:
			frappe.throw("Allocated Amount must be greater than zero.")
		if not self.letter_of_credit:
			frappe.throw("Letter Of Credit is mandatory.")

		existing_total = frappe.db.sql(
			"""
			SELECT IFNULL(SUM(allocated_amount), 0)
			FROM `tabLC Allocation`
			WHERE letter_of_credit = %s AND name != %s
			""",
			(self.letter_of_credit, self.name),
		)[0][0] or 0
		
		lc_total = frappe.db.get_value("Letter Of Credit", self.letter_of_credit, "total_value") or 0
		remaining = float(lc_total) - float(existing_total)
		if self.allocated_amount > remaining:
			frappe.throw(
				f"Allocation exceeds available LC balance. Remaining available amount: {remaining:.2f}"
			)
		if self.allocation_status in (None, "", "Draft"):
					self.allocation_status = "Allocated"
