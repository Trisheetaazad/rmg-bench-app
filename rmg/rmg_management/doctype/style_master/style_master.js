// Copyright (c) 2026, Trisheeta and contributors
// For license information, please see license.txt

frappe.ui.form.on("Style Master", {
	refresh(frm) {
		if (!frm.doc.status) {
			frm.set_value("status", "Draft");
		}
	},
});
