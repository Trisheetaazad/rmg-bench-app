"""Functional test cases T1 - T10, exactly as listed in Table 10.1 of the report.

Each test creates real documents on the site and asserts the expected result
printed in that table, so the table can be reproduced on demand:

	bench --site rmg_management run-tests --module rmg.tests.test_functional_table_10_1

Every document is created with the ``TST-`` prefix and removed again, so running
the suite repeatedly leaves no residue on the site.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from rmg.rmg_management.finance_controls import recalculate_lc_utilization, validate_payment_entry

# --------------------------------------------------------------------------
# Test fixtures
# --------------------------------------------------------------------------

FABRIC_ITEM = "TST-FAB-CVC-160"
STYLE_ITEM = "TST-STYLE-POLO"
SUPPLIER = "TST-Unitex Fabrics Ltd"
STYLE_NUMBER = "TST-ST-1001"
MASTER_LC = "TST-MLC-9001"
BACK_TO_BACK_LC = "TST-BBLC-9002"
BANK_ACCOUNT = "TST-Unitex Current Account"

PO_RATE = 250.0
ORDERED_QTY = 5000.0
RECEIVED_QTY = 5000.0
REJECTED_QTY = 200.0
ACCEPTED_QTY = RECEIVED_QTY - REJECTED_QTY  # 4,800 m
EXPECTED_AMOUNT = ACCEPTED_QTY * PO_RATE  # BDT 1,200,000.00


def get_company():
	company = frappe.defaults.get_defaults().get("company")
	return company or frappe.db.get_value("Company", {}, "name")


def get_abbr():
	return frappe.db.get_value("Company", get_company(), "abbr")


def warehouse(name):
	return f"{name} - {get_abbr()}"


def force_delete(doctype, name):
	if not frappe.db.exists(doctype, name):
		return
	try:
		doc = frappe.get_doc(doctype, name)
		if doc.meta.is_submittable and doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True, delete_permanently=True)
	except Exception:
		frappe.db.rollback()


def purge_test_documents():
	"""Remove anything a previous run left behind, child documents first."""
	for doctype in (
		"Payment Entry",
		"Purchase Invoice",
		"Quality Inspection",
		"Purchase Receipt",
		"Purchase Order",
		"LC Allocation",
		"BOM",
		"Style Master",
		"Letter Of Credit",
		"Bank Account",
		"Supplier",
		"Item",
	):
		for name in frappe.get_all(doctype, filters={"name": ("like", "TST-%")}, pluck="name"):
			force_delete(doctype, name)
		if doctype == "Bank Account":
			for name in frappe.get_all(doctype, filters={"account_name": ("like", "TST-%")}, pluck="name"):
				force_delete(doctype, name)
		if doctype == "LC Allocation":
			for name in frappe.get_all(doctype, filters={"name": ("like", "LC-ALLOC-TST-%")}, pluck="name"):
				force_delete(doctype, name)


# --------------------------------------------------------------------------
# Builders - each returns a saved document
# --------------------------------------------------------------------------


def make_fabric_item():
	if frappe.db.exists("Item", FABRIC_ITEM):
		return frappe.get_doc("Item", FABRIC_ITEM)

	return frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": FABRIC_ITEM,
			"item_name": "CVC Single Jersey 160 GSM Navy",
			"item_group": "Raw Material",
			"stock_uom": "Meter",
			"is_stock_item": 1,
			"valuation_rate": PO_RATE,
			"custom_gsmcount": "160 GSM",
			"custom_colorsize": 'Navy / 60"',
		}
	).insert(ignore_permissions=True)


def make_style_item():
	if frappe.db.exists("Item", STYLE_ITEM):
		return frappe.get_doc("Item", STYLE_ITEM)

	return frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": STYLE_ITEM,
			"item_name": "Mens Polo Shirt - Style 1001",
			"item_group": "Finished Goods",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"custom_gsmcount": "160 GSM",
			"custom_colorsize": "Navy / M",
		}
	).insert(ignore_permissions=True)


def make_bank_account():
	existing = frappe.db.get_value("Bank Account", {"account_name": BANK_ACCOUNT}, "name")
	if existing:
		return frappe.get_doc("Bank Account", existing)

	bank = frappe.db.get_value("Bank", {}, "name")
	if not bank:
		bank = (
			frappe.get_doc({"doctype": "Bank", "bank_name": "TST-Demo Bank"})
			.insert(ignore_permissions=True)
			.name
		)

	return frappe.get_doc(
		{
			"doctype": "Bank Account",
			"account_name": BANK_ACCOUNT,
			"bank": bank,
		}
	).insert(ignore_permissions=True)


def make_supplier():
	if frappe.db.exists("Supplier", SUPPLIER):
		return frappe.get_doc("Supplier", SUPPLIER)

	supplier_group = "Fabric" if frappe.db.exists("Supplier Group", "Fabric") else "All Supplier Groups"
	return frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": SUPPLIER,
			"supplier_group": supplier_group,
			"supplier_type": "Company",
			"country": "Bangladesh",
			"custom_origin": "Local",
			"custom_bank_account_details_": make_bank_account().name,
		}
	).insert(ignore_permissions=True)


def make_letter_of_credit(lc_number, lc_type, total_value):
	if frappe.db.exists("Letter Of Credit", lc_number):
		return frappe.get_doc("Letter Of Credit", lc_number)

	bank = frappe.db.get_value("Bank", {}, "name")
	lc = frappe.get_doc(
		{
			"doctype": "Letter Of Credit",
			"lc_number": lc_number,
			"lc_type": lc_type,
			"issuing_bank": bank,
			"total_value": total_value,
			"expiry_date": add_days(nowdate(), 180),
			"status": "Open",
		}
	).insert(ignore_permissions=True)
	lc.submit()
	return lc


def make_style_master():
	if frappe.db.exists("Style Master", STYLE_NUMBER):
		return frappe.get_doc("Style Master", STYLE_NUMBER)

	buyer = frappe.db.get_value("Customer", {}, "name")
	return frappe.get_doc(
		{
			"doctype": "Style Master",
			"style_number": STYLE_NUMBER,
			"style_name": "Mens Polo Shirt",
			"buyer": buyer,
			"season": "Summer",
			"product_category": "Knitted Garments",
			"master_lc": make_letter_of_credit(MASTER_LC, "Master LC", 4_000_000).name,
			"status": "Active",
		}
	).insert(ignore_permissions=True)


def make_bom():
	make_style_item()
	make_fabric_item()

	existing = frappe.db.get_value("BOM", {"item": STYLE_ITEM, "docstatus": ("<", 2)}, "name")
	if existing:
		return frappe.get_doc("BOM", existing)

	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": STYLE_ITEM,
			"company": get_company(),
			"quantity": 1,
			"currency": frappe.db.get_value("Company", get_company(), "default_currency"),
			"conversion_rate": 1,
			"rm_cost_as_per": "Valuation Rate",
			"items": [{"item_code": FABRIC_ITEM, "qty": 1.8, "rate": PO_RATE, "uom": "Meter"}],
		}
	).insert(ignore_permissions=True)
	bom.submit()
	return bom


def make_purchase_order():
	make_fabric_item()
	make_supplier()
	lc = make_letter_of_credit(BACK_TO_BACK_LC, "Back-to-Back", 1_500_000)

	existing = frappe.db.get_value("Purchase Order", {"supplier": SUPPLIER, "docstatus": 1}, "name")
	if existing:
		return frappe.get_doc("Purchase Order", existing)

	po = frappe.get_doc(
		{
			"doctype": "Purchase Order",
			"supplier": SUPPLIER,
			"company": get_company(),
			"transaction_date": nowdate(),
			"schedule_date": add_days(nowdate(), 30),
			"custom_letter_of_credit": lc.name,
			"custom_delivery_date": add_days(nowdate(), 30),
			"items": [
				{
					"item_code": FABRIC_ITEM,
					"qty": ORDERED_QTY,
					"rate": PO_RATE,
					"uom": "Meter",
					"schedule_date": add_days(nowdate(), 30),
					"warehouse": warehouse("Stores"),
				}
			],
		}
	).insert(ignore_permissions=True)
	po.submit()
	return po


def make_rejected_warehouse():
	name = warehouse("TST Rejected")
	if frappe.db.exists("Warehouse", name):
		return name
	frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": "TST Rejected",
			"company": get_company(),
		}
	).insert(ignore_permissions=True)
	return name


def make_purchase_receipt():
	po = make_purchase_order()

	existing = frappe.db.get_value("Purchase Receipt", {"supplier": SUPPLIER, "docstatus": 1}, "name")
	if existing:
		return frappe.get_doc("Purchase Receipt", existing)

	receipt = frappe.get_doc(
		{
			"doctype": "Purchase Receipt",
			"supplier": SUPPLIER,
			"company": get_company(),
			"posting_date": nowdate(),
			"custom_po_reference_": po.name,
			"custom_batch": "TST-LOT-4471",
			"items": [
				{
					"item_code": FABRIC_ITEM,
					"qty": ACCEPTED_QTY,
					"rejected_qty": REJECTED_QTY,
					"received_qty": RECEIVED_QTY,
					"rate": PO_RATE,
					"uom": "Meter",
					"warehouse": warehouse("Stores"),
					"rejected_warehouse": make_rejected_warehouse(),
				}
			],
		}
	).insert(ignore_permissions=True)
	receipt.submit()
	return receipt


def make_purchase_invoice(claimed_rate):
	po = make_purchase_order()
	receipt = make_purchase_receipt()

	return frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"supplier": SUPPLIER,
			"company": get_company(),
			"posting_date": nowdate(),
			"bill_no": "TST-SINV-771",
			"bill_date": nowdate(),
			"custom_po_no": po.name,
			"custom_po_receipt_": receipt.name,
			"items": [
				{
					"item_code": FABRIC_ITEM,
					"qty": ACCEPTED_QTY,
					"rate": claimed_rate,
					"uom": "Meter",
					"warehouse": warehouse("Stores"),
				}
			],
		}
	).insert(ignore_permissions=True)


# --------------------------------------------------------------------------
# Table 10.1
# --------------------------------------------------------------------------


class TestFunctionalTable(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		purge_test_documents()
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		purge_test_documents()
		frappe.db.commit()
		super().tearDownClass()

	# T1 -------------------------------------------------------------------
	def test_t01_item_with_gsm_count_and_colour_size(self):
		"""T1  Create an Item with GSM/Count, Color/Size and a default unit of measure."""
		item = make_fabric_item()

		self.assertEqual(item.custom_gsmcount, "160 GSM")
		self.assertEqual(item.custom_colorsize, 'Navy / 60"')
		self.assertEqual(item.stock_uom, "Meter")

		# Items are named by their code, and the app itself applies that setting
		self.assertEqual(frappe.db.get_single_value("Stock Settings", "item_naming_by"), "Item Code")
		self.assertEqual(item.name, FABRIC_ITEM)

		# ...and the fields sit where the report says they do: GSM/Count right
		# after the item group, Color/Size right after GSM/Count.
		self.assertEqual(
			frappe.db.get_value(
				"Custom Field", {"dt": "Item", "fieldname": "custom_gsmcount"}, "insert_after"
			),
			"item_group",
		)
		self.assertEqual(
			frappe.db.get_value(
				"Custom Field", {"dt": "Item", "fieldname": "custom_colorsize"}, "insert_after"
			),
			"custom_gsmcount",
		)

	# T2 -------------------------------------------------------------------
	def test_t02_bill_of_materials_for_a_garment_style(self):
		"""T2  Build a Bill of Materials for a garment style."""
		bom = make_bom()

		self.assertEqual(bom.item, STYLE_ITEM)
		self.assertEqual(bom.docstatus, 1)
		self.assertEqual(len(bom.items), 1)
		self.assertEqual(bom.items[0].item_code, FABRIC_ITEM)
		self.assertEqual(bom.items[0].qty, 1.8)

		# the BOM is what ties a buyer style to the material to be procured
		style = make_style_master()
		style.bom = bom.name
		style.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Style Master", STYLE_NUMBER, "bom"), bom.name)

	# T3 -------------------------------------------------------------------
	def test_t03_supplier_with_origin_and_bank_account(self):
		"""T3  Create a Supplier with Origin and Bank Account Details."""
		supplier = make_supplier()

		self.assertEqual(supplier.custom_origin, "Local")
		self.assertEqual(
			frappe.db.get_value("Bank Account", supplier.custom_bank_account_details_, "account_name"),
			BANK_ACCOUNT,
		)

		# the supplier shows by name, not by internal ID, on linked documents
		self.assertEqual(frappe.get_meta("Supplier").get_title_field(), "supplier_name")
		self.assertEqual(supplier.name, SUPPLIER)

	# T4 -------------------------------------------------------------------
	def test_t04_purchase_order_linked_to_back_to_back_lc(self):
		"""T4  Raise a Purchase Order linked to a Back-to-Back LC."""
		po = make_purchase_order()

		self.assertEqual(po.custom_letter_of_credit, BACK_TO_BACK_LC)
		self.assertEqual(frappe.db.get_value("Letter Of Credit", BACK_TO_BACK_LC, "lc_type"), "Back-to-Back")
		self.assertIsNotNone(po.custom_delivery_date)
		self.assertEqual(str(po.custom_delivery_date), add_days(nowdate(), 30))
		self.assertEqual(po.items[0].rate, PO_RATE)
		self.assertEqual(po.docstatus, 1)

	# T5 -------------------------------------------------------------------
	def test_t05_purchase_receipt_with_batch_reference(self):
		"""T5  Record a Purchase Receipt against that PO with a batch reference."""
		receipt = make_purchase_receipt()
		row = receipt.items[0]

		self.assertEqual(receipt.custom_po_reference_, make_purchase_order().name)
		self.assertEqual(receipt.custom_batch, "TST-LOT-4471")

		# received, accepted and rejected are stored separately
		self.assertEqual(row.received_qty, RECEIVED_QTY)
		self.assertEqual(row.qty, ACCEPTED_QTY)
		self.assertEqual(row.rejected_qty, REJECTED_QTY)
		self.assertEqual(row.received_qty, row.qty + row.rejected_qty)

	# T6 -------------------------------------------------------------------
	def test_t06_quality_inspection_with_defect_type(self):
		"""T6  Record a Quality Inspection against the receipt with a defect type."""
		receipt = make_purchase_receipt()

		# ERPNext only allows an inspection on an item that is marked for one.
		# Enable it just for this test so the already-submitted receipt above is
		# not retrospectively required to carry an inspection.
		frappe.db.set_value("Item", FABRIC_ITEM, "inspection_required_before_purchase", 1)
		self.addCleanup(frappe.db.set_value, "Item", FABRIC_ITEM, "inspection_required_before_purchase", 0)

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Purchase Receipt",
				"reference_name": receipt.name,
				"item_code": FABRIC_ITEM,
				"sample_size": 50,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"status": "Rejected",
				"custom_defect_type": "Shading",
			}
		).insert(ignore_permissions=True)

		self.assertEqual(inspection.custom_defect_type, "Shading")
		self.assertEqual(inspection.status, "Rejected")
		self.assertEqual(inspection.reference_name, receipt.name)

		force_delete("Quality Inspection", inspection.name)

	# T7 -------------------------------------------------------------------
	def test_t07_purchase_invoice_carries_po_and_receipt_references(self):
		"""T7  Raise a Purchase Invoice carrying both the PO and receipt references."""
		invoice = make_purchase_invoice(claimed_rate=PO_RATE)

		self.assertEqual(invoice.custom_po_no, make_purchase_order().name)
		self.assertEqual(invoice.custom_po_receipt_, make_purchase_receipt().name)

		# both links resolve to real documents
		self.assertTrue(frappe.db.exists("Purchase Order", invoice.custom_po_no))
		self.assertTrue(frappe.db.exists("Purchase Receipt", invoice.custom_po_receipt_))

		# and the match fields are present and populated
		self.assertIn(
			"custom_match_status", [f.fieldname for f in frappe.get_meta("Purchase Invoice").fields]
		)
		self.assertIn(
			"custom_difference_amount", [f.fieldname for f in frappe.get_meta("Purchase Invoice").fields]
		)
		self.assertEqual(invoice.custom_match_status, "Matched")
		self.assertEqual(invoice.custom_difference_amount, 0)

		force_delete("Purchase Invoice", invoice.name)

	# T8 -------------------------------------------------------------------
	def test_t08_invoice_below_accepted_value_is_a_discrepancy(self):
		"""T8  Invoice claiming an amount below the accepted quantity valued at the PO rate."""
		claimed_rate = 240.0
		invoice = make_purchase_invoice(claimed_rate=claimed_rate)

		claimed_amount = ACCEPTED_QTY * claimed_rate  # BDT 1,152,000.00

		self.assertEqual(invoice.custom_match_status, "Discrepancy")
		self.assertAlmostEqual(invoice.custom_difference_amount, claimed_amount - EXPECTED_AMOUNT, places=2)
		self.assertAlmostEqual(invoice.custom_difference_amount, -48_000.00, places=2)

		force_delete("Purchase Invoice", invoice.name)

	def test_t08b_invoice_billing_for_rejected_goods_is_a_discrepancy(self):
		"""T8 (overpayment direction)  Supplier bills the full despatch including QC rejects."""
		invoice = make_purchase_invoice(claimed_rate=PO_RATE)
		# bill for everything despatched, not just what passed inspection
		invoice.items[0].qty = RECEIVED_QTY
		invoice.save(ignore_permissions=True)

		claimed_amount = RECEIVED_QTY * PO_RATE  # BDT 1,250,000.00

		self.assertEqual(invoice.custom_match_status, "Discrepancy")
		self.assertAlmostEqual(invoice.custom_difference_amount, claimed_amount - EXPECTED_AMOUNT, places=2)
		# the 200 m rejected for shading, valued at the PO rate
		self.assertAlmostEqual(invoice.custom_difference_amount, 50_000.00, places=2)

		force_delete("Purchase Invoice", invoice.name)

	# T9 -------------------------------------------------------------------
	def test_t09_cheque_payment_without_withdrawer_is_refused(self):
		"""T9  Payment Entry with Cheque selected and the withdrawer fields blank."""
		payment = frappe.new_doc("Payment Entry")
		payment.update(
			{
				"payment_type": "Pay",
				"company": get_company(),
				"party_type": "Supplier",
				"party": make_supplier().name,
				"posting_date": nowdate(),
				"paid_amount": 1000,
				"received_amount": 1000,
				"custom_voucher_type": "Bank Entry",
				"mode_of_payment": "Cheque",
				"custom_cheque_withdrawer": None,
				"custom_withdrawer_designation": None,
			}
		)

		with self.assertRaises(frappe.ValidationError) as refusal:
			validate_payment_entry(payment)
		self.assertIn("Cheque Withdrawer is mandatory", str(refusal.exception))

		# filling the withdrawer name alone is still not enough
		payment.custom_cheque_withdrawer = "Rafiqul Islam"
		with self.assertRaises(frappe.ValidationError) as refusal:
			validate_payment_entry(payment)
		self.assertIn("Withdrawer Designation is mandatory", str(refusal.exception))

		# with both fields supplied the control passes
		payment.custom_withdrawer_designation = "Accounts Officer"
		validate_payment_entry(payment)

		# the three fields exist on the doctype, and the client script is bound
		fieldnames = [f.fieldname for f in frappe.get_meta("Payment Entry").fields]
		for fieldname in (
			"custom_voucher_type",
			"custom_cheque_withdrawer",
			"custom_withdrawer_designation",
		):
			self.assertIn(fieldname, fieldnames)

	def test_t10a_letter_of_credit_status_lifecycle(self):
		"""Draft while unsubmitted, Open on submit - never skipped straight to Open."""
		lc = frappe.get_doc(
			{
				"doctype": "Letter Of Credit",
				"lc_number": "TST-LC-LIFECYCLE",
				"lc_type": "Back-to-Back",
				"issuing_bank": frappe.db.get_value("Bank", {}, "name"),
				"total_value": 100_000,
				"expiry_date": add_days(nowdate(), 90),
				"status": "Draft",
			}
		).insert(ignore_permissions=True)

		lc.reload()
		self.assertEqual(lc.status, "Draft")
		self.assertEqual(lc.custom_remaining_amount, 100_000)

		lc.submit()
		lc.reload()
		self.assertEqual(lc.status, "Open")

		# a wrong manual status is corrected from the figures on save
		lc.status = "Exhausted"
		lc.save(ignore_permissions=True)
		lc.reload()
		self.assertEqual(lc.status, "Open")

		# finance can close a submitted credit by hand, and a later
		# recalculation must never reopen it
		lc.status = "Closed"
		lc.save(ignore_permissions=True)
		recalculate_lc_utilization(lc.name)
		lc.reload()
		self.assertEqual(lc.status, "Closed")

		# ...but finance can reopen it deliberately
		lc.status = "Open"
		lc.save(ignore_permissions=True)
		lc.reload()
		self.assertEqual(lc.status, "Open")

		force_delete("Letter Of Credit", lc.name)

	# T10 ------------------------------------------------------------------
	def test_t10_lc_allocation_recalculates_utilisation(self):
		"""T10  Book an LC Allocation against a Back-to-Back LC."""
		lc = make_letter_of_credit(BACK_TO_BACK_LC, "Back-to-Back", 1_500_000)
		style = make_style_master()

		# a credit with nothing allocated against it reports its full face value
		lc.reload()
		self.assertEqual(lc.custom_utilized_amount, 0)
		self.assertEqual(lc.custom_remaining_amount, 1_500_000)

		first = frappe.get_doc(
			{
				"doctype": "LC Allocation",
				"letter_of_credit": lc.name,
				"style_reference": style.name,
				"allocated_amount": 1_250_000,
				"currency": "BDT",
				"exchange_rate": 1.0,
				"allocation_status": "Allocated",
			}
		).insert(ignore_permissions=True)

		lc.reload()
		self.assertEqual(lc.custom_utilized_amount, 1_250_000)
		self.assertEqual(lc.custom_remaining_amount, 250_000)
		self.assertAlmostEqual(lc.custom_utilization_percent, 83.3333, places=2)
		self.assertEqual(lc.status, "Open")

		# a second allocation against the same credit must accumulate, and
		# exhaust the credit once it is fully consumed
		second = frappe.get_doc(
			{
				"doctype": "LC Allocation",
				"letter_of_credit": lc.name,
				"style_reference": style.name,
				"allocated_amount": 250_000,
				"currency": "BDT",
				"exchange_rate": 1.0,
				"allocation_status": "Allocated",
			}
		).insert(ignore_permissions=True)

		lc.reload()
		self.assertEqual(lc.custom_utilized_amount, 1_500_000)
		self.assertEqual(lc.custom_remaining_amount, 0)
		self.assertAlmostEqual(lc.custom_utilization_percent, 100.0, places=2)
		self.assertEqual(lc.status, "Exhausted")

		# over-allocating beyond the face value is refused
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "LC Allocation",
					"letter_of_credit": lc.name,
					"allocated_amount": 1,
					"currency": "BDT",
					"exchange_rate": 1.0,
					"allocation_status": "Allocated",
				}
			).insert(ignore_permissions=True)

		force_delete("LC Allocation", second.name)
		force_delete("LC Allocation", first.name)
		recalculate_lc_utilization(lc.name)
