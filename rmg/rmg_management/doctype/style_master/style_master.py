# Copyright (c) 2026, Trisheeta and contributors
# For license information, please see license.txt

import frappe
from frappe import ValidationError
from frappe.model.document import Document


class StyleMaster(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bom: DF.Link | None
		buyer: DF.Link | None
		description: DF.TextEditor | None
		master_lc: DF.Link | None
		notes: DF.Text | None
		product_category: DF.Literal["", "Knitted Garments", "Denim", "Woven Garments", "Accessories", "Home Textile"]
		season: DF.Literal["", "Spring", "Summer", "Autumn", "Winter", "All Year"]
		status: DF.Literal["Draft", "Active", "Hold", "Closed"]
		style_name: DF.Data
		style_number: DF.Data

	def validate(self):
		if not self.style_number:
			frappe.throw("Style Number is mandatory.")
		if not self.style_name:
			frappe.throw("Style Name is mandatory.")
		if self.master_lc:
			lc = frappe.get_doc("Letter Of Credit", self.master_lc)
			if lc.status == "Closed":
				raise ValidationError("Master LC is already closed and cannot be linked to a new style.")
		if not self.status:
			self.status = "Draft"
