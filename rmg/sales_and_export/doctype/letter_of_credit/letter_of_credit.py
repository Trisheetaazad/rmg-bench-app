# Copyright (c) 2026, Trisheeta and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LetterOfCredit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		expiry_date: DF.Date | None
		issuing_bank: DF.Link | None
		lc_number: DF.Data
		lc_type: DF.Literal["", "Master LC", "Back-to-Back"]
		status: DF.Literal["Draft", "Open", "Exhausted", "Closed"]
		total_value: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Letter Of Credit"
