"""Build a realistic demonstration chain on the site, ready for a live walkthrough.

Creates every document of the order lifecycle with garment-industry figures, in
dependency order, and stops just before the Purchase Invoice so the three-way
match can be triggered live in front of an audience.

	bench --site rmg_management execute rmg.tests.seed_demo_data.seed

	# wipe the previous demo data and rebuild it from scratch
	bench --site rmg_management execute rmg.tests.seed_demo_data.seed \\
		--kwargs "{'reset': True}"

	# also create the discrepancy invoice, as a fallback if the live entry fails
	bench --site rmg_management execute rmg.tests.seed_demo_data.seed \\
		--kwargs "{'reset': True, 'with_invoice': True}"

	# remove everything this script created
	bench --site rmg_management execute rmg.tests.seed_demo_data.reset

The documents use their own names and never collide with the ``TST-`` records
created by the automated test suite.
"""

import frappe
from frappe.utils import add_days, flt, nowdate

# --------------------------------------------------------------------------
# The demonstration order
# --------------------------------------------------------------------------

BUYER = "Nordwind Apparel GmbH"
BANK = "Prime Bank PLC"
BANK_ACCOUNT = "Unitex Fabrics Current Account"
SUPPLIER = "Unitex Fabrics Ltd"

FABRIC_ITEM = "FAB-CVC-160-NAVY"
STYLE_ITEM = "STYLE-1001-POLO"
STYLE_NUMBER = "ST-1001"

MASTER_LC = "MLC-2026-0042"
BACK_TO_BACK_LC = "BBLC-2026-0117"

# Export order: 12,000 polo shirts at BDT 320
GARMENT_QTY = 12_000
GARMENT_RATE = 320.0
MASTER_LC_VALUE = 4_000_000.0

# Procurement: 5,000 m of fabric at BDT 250, 200 m rejected for shading
PO_RATE = 250.0
ORDERED_QTY = 5_000.0
RECEIVED_QTY = 5_000.0
REJECTED_QTY = 200.0
ACCEPTED_QTY = RECEIVED_QTY - REJECTED_QTY
BACK_TO_BACK_LC_VALUE = 1_500_000.0
ALLOCATED_AMOUNT = 1_250_000.0
BATCH_REFERENCE = "LOT-4471"

EXPECTED_AMOUNT = ACCEPTED_QTY * PO_RATE  # BDT 1,200,000
SUPPLIER_CLAIM = RECEIVED_QTY * PO_RATE  # BDT 1,250,000 - bills the rejects too
OVERPAYMENT = SUPPLIER_CLAIM - EXPECTED_AMOUNT  # BDT 50,000


def money(amount):
	return f"BDT {flt(amount):,.2f}"


def company():
	return frappe.defaults.get_defaults().get("company") or frappe.db.get_value("Company", {}, "name")


def warehouse(name):
	return f"{name} - {frappe.db.get_value('Company', company(), 'abbr')}"


def step(message):
	print(f"  ->  {message}")


def existing(doctype, name):
	return frappe.get_doc(doctype, name) if frappe.db.exists(doctype, name) else None


# --------------------------------------------------------------------------
# Builders, in dependency order
# --------------------------------------------------------------------------


def build_items():
	fabric = existing("Item", FABRIC_ITEM)
	if not fabric:
		fabric = frappe.get_doc(
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
		step(f"Item          {FABRIC_ITEM}  (160 GSM, Navy / 60\", Meter)")

	style = existing("Item", STYLE_ITEM)
	if not style:
		style = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": STYLE_ITEM,
				"item_name": "Mens Short Sleeve Polo - Style 1001",
				"item_group": "Finished Goods",
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"custom_gsmcount": "160 GSM",
				"custom_colorsize": "Navy / S-M-L-XL",
			}
		).insert(ignore_permissions=True)
		step(f"Item          {STYLE_ITEM}  (finished garment)")

	return fabric, style


def build_bom():
	found = frappe.db.get_value("BOM", {"item": STYLE_ITEM, "docstatus": 1}, "name")
	if found:
		return frappe.get_doc("BOM", found)

	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": STYLE_ITEM,
			"company": company(),
			"quantity": 1,
			"currency": frappe.db.get_value("Company", company(), "default_currency"),
			"conversion_rate": 1,
			"rm_cost_as_per": "Valuation Rate",
			"items": [{"item_code": FABRIC_ITEM, "qty": 1.8, "rate": PO_RATE, "uom": "Meter"}],
		}
	).insert(ignore_permissions=True)
	bom.submit()
	step(f"BOM           {bom.name}  (1.8 m of fabric per shirt)")
	return bom


def build_bank_account():
	if not frappe.db.exists("Bank", BANK):
		frappe.get_doc({"doctype": "Bank", "bank_name": BANK}).insert(ignore_permissions=True)
		step(f"Bank          {BANK}")

	found = frappe.db.get_value("Bank Account", {"account_name": BANK_ACCOUNT}, "name")
	if found:
		return frappe.get_doc("Bank Account", found)

	account = frappe.get_doc(
		{"doctype": "Bank Account", "account_name": BANK_ACCOUNT, "bank": BANK}
	).insert(ignore_permissions=True)
	step(f"Bank Account  {account.name}")
	return account


def build_supplier():
	found = existing("Supplier", SUPPLIER)
	if found:
		return found

	group = "Fabric" if frappe.db.exists("Supplier Group", "Fabric") else "All Supplier Groups"
	supplier = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": SUPPLIER,
			"supplier_group": group,
			"supplier_type": "Company",
			"country": "Bangladesh",
			"custom_origin": "Local",
			"custom_bank_account_details_": build_bank_account().name,
		}
	).insert(ignore_permissions=True)
	step(f"Supplier      {SUPPLIER}  (Origin: Local)")
	return supplier


def build_letter_of_credit(lc_number, lc_type, total_value):
	found = existing("Letter Of Credit", lc_number)
	if found:
		return found

	if not frappe.db.exists("Bank", BANK):
		frappe.get_doc({"doctype": "Bank", "bank_name": BANK}).insert(ignore_permissions=True)

	lc = frappe.get_doc(
		{
			"doctype": "Letter Of Credit",
			"lc_number": lc_number,
			"lc_type": lc_type,
			"issuing_bank": BANK,
			"total_value": total_value,
			"expiry_date": add_days(nowdate(), 180),
			"status": "Open",
		}
	).insert(ignore_permissions=True)
	lc.submit()
	step(f"Letter Of Credit  {lc_number}  ({lc_type}, {money(total_value)})")
	return lc


def build_customer():
	if frappe.db.exists("Customer", BUYER):
		return frappe.get_doc("Customer", BUYER)

	group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": BUYER,
			"customer_group": group,
			"territory": territory,
		}
	).insert(ignore_permissions=True)
	step(f"Customer      {BUYER}  (the foreign buyer)")
	return customer


def build_sales_order(master_lc):
	found = frappe.db.get_value("Sales Order", {"customer": BUYER, "docstatus": ("<", 2)}, "name")
	if found:
		return frappe.get_doc("Sales Order", found)

	order = frappe.get_doc(
		{
			"doctype": "Sales Order",
			"customer": build_customer().name,
			"company": company(),
			"transaction_date": nowdate(),
			"delivery_date": add_days(nowdate(), 90),
			"custom_style_number": STYLE_NUMBER,
			"custom_master_lc_reference": master_lc.name,
			"items": [
				{
					"item_code": STYLE_ITEM,
					"qty": GARMENT_QTY,
					"rate": GARMENT_RATE,
					"delivery_date": add_days(nowdate(), 90),
					"warehouse": warehouse("Finished Goods"),
				}
			],
		}
	).insert(ignore_permissions=True)
	order.submit()
	step(
		f"Sales Order   {order.name}  ({GARMENT_QTY:,} pcs @ {money(GARMENT_RATE)} "
		f"= {money(order.grand_total)})"
	)
	return order


def build_style_master(master_lc, bom):
	found = existing("Style Master", STYLE_NUMBER)
	if found:
		return found

	style = frappe.get_doc(
		{
			"doctype": "Style Master",
			"style_number": STYLE_NUMBER,
			"style_name": "Mens Short Sleeve Polo",
			"buyer": BUYER,
			"season": "Summer",
			"product_category": "Knitted Garments",
			"master_lc": master_lc.name,
			"bom": bom.name,
			"status": "Active",
		}
	).insert(ignore_permissions=True)
	step(f"Style Master  {STYLE_NUMBER}  (buyer style -> Master LC -> BOM)")
	return style


def build_lc_allocation(back_to_back_lc, style):
	found = frappe.db.get_value(
		"LC Allocation", {"letter_of_credit": back_to_back_lc.name}, "name"
	)
	if found:
		return frappe.get_doc("LC Allocation", found)

	allocation = frappe.get_doc(
		{
			"doctype": "LC Allocation",
			"letter_of_credit": back_to_back_lc.name,
			"style_reference": style.name,
			"allocated_amount": ALLOCATED_AMOUNT,
			"currency": "BDT",
			"exchange_rate": 1.0,
			"allocation_status": "Allocated",
		}
	).insert(ignore_permissions=True)

	back_to_back_lc.reload()
	step(
		f"LC Allocation {allocation.name}  ({money(ALLOCATED_AMOUNT)} booked -> "
		f"{back_to_back_lc.custom_utilization_percent:.2f}% utilised)"
	)
	return allocation


def build_purchase_order(back_to_back_lc):
	found = frappe.db.get_value("Purchase Order", {"supplier": SUPPLIER, "docstatus": 1}, "name")
	if found:
		return frappe.get_doc("Purchase Order", found)

	order = frappe.get_doc(
		{
			"doctype": "Purchase Order",
			"supplier": SUPPLIER,
			"company": company(),
			"transaction_date": nowdate(),
			"schedule_date": add_days(nowdate(), 30),
			"custom_letter_of_credit": back_to_back_lc.name,
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
	order.submit()
	step(
		f"Purchase Order {order.name}  ({ORDERED_QTY:,.0f} m @ {money(PO_RATE)} "
		f"= {money(order.grand_total)}, LC {back_to_back_lc.name})"
	)
	return order


def build_rejected_warehouse():
	name = warehouse("Rejected")
	if frappe.db.exists("Warehouse", name):
		return name
	frappe.get_doc(
		{"doctype": "Warehouse", "warehouse_name": "Rejected", "company": company()}
	).insert(ignore_permissions=True)
	step(f"Warehouse     {name}  (for QC rejections)")
	return name


def build_purchase_receipt(purchase_order):
	found = frappe.db.get_value("Purchase Receipt", {"supplier": SUPPLIER, "docstatus": 1}, "name")
	if found:
		return frappe.get_doc("Purchase Receipt", found)

	receipt = frappe.get_doc(
		{
			"doctype": "Purchase Receipt",
			"supplier": SUPPLIER,
			"company": company(),
			"posting_date": nowdate(),
			"custom_po_reference_": purchase_order.name,
			"custom_batch": BATCH_REFERENCE,
			"items": [
				{
					"item_code": FABRIC_ITEM,
					"qty": ACCEPTED_QTY,
					"rejected_qty": REJECTED_QTY,
					"received_qty": RECEIVED_QTY,
					"rate": PO_RATE,
					"uom": "Meter",
					"warehouse": warehouse("Stores"),
					"rejected_warehouse": build_rejected_warehouse(),
				}
			],
		}
	).insert(ignore_permissions=True)
	receipt.submit()
	step(
		f"Purchase Receipt {receipt.name}  (received {RECEIVED_QTY:,.0f} m, "
		f"accepted {ACCEPTED_QTY:,.0f} m, rejected {REJECTED_QTY:,.0f} m, batch {BATCH_REFERENCE})"
	)
	return receipt


def build_quality_inspection(receipt):
	found = frappe.db.get_value(
		"Quality Inspection", {"reference_name": receipt.name, "docstatus": ("<", 2)}, "name"
	)
	if found:
		return frappe.get_doc("Quality Inspection", found)

	# The item must be marked for inspection before ERPNext allows a QI. Turn the
	# flag off again afterwards so documents can still be entered live on stage
	# without every receipt demanding an inspection first.
	frappe.db.set_value("Item", FABRIC_ITEM, "inspection_required_before_purchase", 1)
	try:
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
	finally:
		frappe.db.set_value("Item", FABRIC_ITEM, "inspection_required_before_purchase", 0)

	step(f"Quality Inspection {inspection.name}  (Defect Type: Shading, status Rejected)")
	return inspection


def build_discrepancy_invoice(purchase_order, receipt):
	"""The supplier bills the full despatch, rejects included."""
	found = frappe.db.get_value(
		"Purchase Invoice", {"bill_no": "UFL-INV-2026-0331", "docstatus": ("<", 2)}, "name"
	)
	if found:
		return frappe.get_doc("Purchase Invoice", found)

	invoice = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"supplier": SUPPLIER,
			"company": company(),
			"posting_date": nowdate(),
			"bill_no": "UFL-INV-2026-0331",
			"bill_date": nowdate(),
			"custom_po_no": purchase_order.name,
			"custom_po_receipt_": receipt.name,
			"items": [
				{
					"item_code": FABRIC_ITEM,
					"qty": RECEIVED_QTY,
					"rate": PO_RATE,
					"uom": "Meter",
					"warehouse": warehouse("Stores"),
				}
			],
		}
	).insert(ignore_permissions=True)
	step(
		f"Purchase Invoice {invoice.name}  (claims {money(SUPPLIER_CLAIM)} -> "
		f"{invoice.custom_match_status}, difference {money(invoice.custom_difference_amount)})"
	)
	return invoice


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

DEMO_DOCUMENTS = [
	("Purchase Invoice", {"bill_no": "UFL-INV-2026-0331"}),
	("Quality Inspection", {"item_code": FABRIC_ITEM}),
	("Purchase Receipt", {"supplier": SUPPLIER}),
	("Purchase Order", {"supplier": SUPPLIER}),
	("LC Allocation", {"letter_of_credit": BACK_TO_BACK_LC}),
	("Sales Order", {"customer": BUYER}),
	("Style Master", {"style_number": STYLE_NUMBER}),
	("BOM", {"item": STYLE_ITEM}),
	("Letter Of Credit", {"lc_number": ("in", [MASTER_LC, BACK_TO_BACK_LC])}),
	("Supplier", {"supplier_name": SUPPLIER}),
	("Bank Account", {"account_name": BANK_ACCOUNT}),
	("Customer", {"customer_name": BUYER}),
	("Item", {"item_code": ("in", [FABRIC_ITEM, STYLE_ITEM])}),
]


def _purge():
	"""Remove every document this script creates, children first."""
	print("\nRemoving previous demonstration data")
	removed = 0
	for doctype, filters in DEMO_DOCUMENTS:
		for name in frappe.get_all(doctype, filters=filters, pluck="name"):
			try:
				doc = frappe.get_doc(doctype, name)
				if doc.meta.is_submittable and doc.docstatus == 1:
					doc.cancel()
				frappe.delete_doc(
					doctype, name, force=True, ignore_permissions=True, delete_permanently=True
				)
				removed += 1
				step(f"removed {doctype} {name}")
			except Exception as error:
				print(f"      could not remove {doctype} {name}: {error}")
	frappe.db.commit()
	print(f"\n  {removed} document(s) removed.\n")


def reset():
	"""Entry point: remove the demonstration data and leave the site clean."""
	_purge()


def seed(reset=False, with_invoice=False):
	"""Create the full demonstration chain in dependency order."""
	if reset:
		_purge()

	print("\nBuilding the demonstration chain\n")

	build_items()
	bom = build_bom()
	build_bank_account()
	build_supplier()
	master_lc = build_letter_of_credit(MASTER_LC, "Master LC", MASTER_LC_VALUE)
	build_customer()
	build_sales_order(master_lc)
	style = build_style_master(master_lc, bom)
	back_to_back_lc = build_letter_of_credit(
		BACK_TO_BACK_LC, "Back-to-Back", BACK_TO_BACK_LC_VALUE
	)
	build_lc_allocation(back_to_back_lc, style)
	purchase_order = build_purchase_order(back_to_back_lc)
	receipt = build_purchase_receipt(purchase_order)
	build_quality_inspection(receipt)

	if with_invoice:
		build_discrepancy_invoice(purchase_order, receipt)

	frappe.db.commit()
	print_walkthrough(purchase_order, receipt, with_invoice)


def print_walkthrough(purchase_order, receipt, invoice_created):
	line = "=" * 74
	print(f"\n{line}\n  READY FOR THE DEMONSTRATION\n{line}\n")
	print("  Open these in order:\n")
	print(f"    1. Sales Order        buyer {BUYER}, style {STYLE_NUMBER}, Master LC {MASTER_LC}")
	print(f"    2. Style Master       {STYLE_NUMBER} -> Master LC -> BOM")
	print(f"    3. Letter Of Credit   {BACK_TO_BACK_LC}   Back-to-Back, {money(BACK_TO_BACK_LC_VALUE)}")
	print(f"       LC Allocation      {money(ALLOCATED_AMOUNT)} booked, utilisation recalculated")
	print(f"    4. Purchase Order     {purchase_order.name}   {ORDERED_QTY:,.0f} m @ {money(PO_RATE)}")
	print(
		f"    5. Purchase Receipt   {receipt.name}   accepted {ACCEPTED_QTY:,.0f} m, "
		f"rejected {REJECTED_QTY:,.0f} m"
	)
	print("    6. Quality Inspection Defect Type: Shading\n")

	if invoice_created:
		print("    7. Purchase Invoice   already created, showing the discrepancy\n")
	else:
		print("  Then create the Purchase Invoice live — this is the moment:\n")
		print(f"       Supplier    {SUPPLIER}")
		print(f"       PO No       {purchase_order.name}")
		print(f"       PO Receipt  {receipt.name}")
		print(f"       Item        {FABRIC_ITEM}")
		print(f"       Quantity    {RECEIVED_QTY:,.0f}      <- the full despatch, rejects included")
		print(f"       Rate        {PO_RATE:,.2f}\n")

	print("  On save the engine reports:\n")
	print(f"       claimed     {money(SUPPLIER_CLAIM)}")
	print(f"       expected    {money(EXPECTED_AMOUNT)}   ({ACCEPTED_QTY:,.0f} m x {money(PO_RATE)})")
	print(f"       difference  {money(OVERPAYMENT)}   <- the overpayment that is stopped\n")
	print("  Then Payment Entry: choose Cheque, leave the withdrawer fields blank,")
	print("  and the server refuses the submission.\n")
	print(f"{line}\n")
