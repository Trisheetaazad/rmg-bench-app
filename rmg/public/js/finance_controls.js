frappe.ui.form.on("Payment Entry", {
	mode_of_payment(frm) {
		const is_cheque = (frm.doc.mode_of_payment || "").toLowerCase().includes("cheque");

		frm.toggle_display("custom_cheque_withdrawer", is_cheque);
		frm.toggle_reqd("custom_cheque_withdrawer", is_cheque);
		frm.toggle_display("custom_withdrawer_designation", is_cheque);
		frm.toggle_reqd("custom_withdrawer_designation", is_cheque);
	},

	refresh(frm) {
		frm.trigger("mode_of_payment");
	},
});
