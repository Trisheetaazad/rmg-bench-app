import frappe


def apply_item_naming():
	"""Name Items by their item code, so fabric and trim codes stay readable.

	This is a site-level Stock Setting, so it has to be applied by the app on
	install and migrate; otherwise a fresh site falls back to a naming series.
	"""
	if frappe.db.get_single_value("Stock Settings", "item_naming_by") != "Item Code":
		frappe.db.set_single_value("Stock Settings", "item_naming_by", "Item Code")
