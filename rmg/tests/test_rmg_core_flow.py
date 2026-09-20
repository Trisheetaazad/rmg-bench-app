import frappe
from frappe.tests import IntegrationTestCase


class TestRmgCoreFlow(IntegrationTestCase):
	def test_style_master_and_lc_allocation_flow(self):
		if not frappe.db.exists("Customer", "TST-Demo Buyer"):
			frappe.get_doc({"doctype": "Customer", "customer_name": "TST-Demo Buyer"}).insert(ignore_permissions=True)

		if not frappe.db.exists("Bank", "TST-Bank of Test"):
			frappe.get_doc({"doctype": "Bank", "bank_name": "TST-Bank of Test"}).insert(ignore_permissions=True)

		style = frappe.get_doc(
			{
				"doctype": "Style Master",
				"style_number": "TST-CORE-1001",
				"style_name": "Classic Polo",
				"buyer": "TST-Demo Buyer",
				"season": "Spring",
				"product_category": "Knitted Garments",
			}
		)
		style.insert(ignore_permissions=True)
		self.assertTrue(style.name)

		lc = frappe.get_doc(
			{
				"doctype": "Letter Of Credit",
				"lc_number": "TST-CORE-LC-1001",
				"lc_type": "Master LC",
				"issuing_bank": "TST-Bank of Test",
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
