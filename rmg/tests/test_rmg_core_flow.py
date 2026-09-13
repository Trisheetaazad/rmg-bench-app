import frappe
from frappe.tests.utils import FrappeTestCase


class TestRmgCoreFlow(FrappeTestCase):
	def test_style_master_and_lc_allocation_flow(self):
		if not frappe.db.exists("Customer", "Demo Buyer"):
			frappe.get_doc({"doctype": "Customer", "customer_name": "Demo Buyer"}).insert(ignore_permissions=True)

		if not frappe.db.exists("Bank", "Bank of Test"):
			frappe.get_doc({"doctype": "Bank", "bank_name": "Bank of Test"}).insert(ignore_permissions=True)

		style = frappe.get_doc(
			{
				"doctype": "Style Master",
				"style_number": "ST-1001",
				"style_name": "Classic Polo",
				"buyer": "Demo Buyer",
				"season": "Spring",
				"product_category": "Knitted Garments",
			}
		)
		style.insert(ignore_permissions=True)
		self.assertTrue(style.name)

		lc = frappe.get_doc(
			{
				"doctype": "Letter Of Credit",
				"lc_number": "LC-1001",
				"lc_type": "Master LC",
				"issuing_bank": "Bank of Test",
				"total_value": 100000,
				"expiry_date": "2099-12-31",
				"status": "Open",
			}
		)
		lc.insert(ignore_permissions=True)
		self.assertTrue(lc.name)

		allocation = frappe.get_doc(
			{
				"doctype": "LC Allocation",
				"letter_of_credit": lc.name,
				"allocated_amount": 50000,
				"currency": "USD",
				"exchange_rate": 1.0,
				"allocation_status": "Allocated",
			}
		)
		allocation.insert(ignore_permissions=True)
		self.assertEqual(allocation.allocated_amount, 50000)
