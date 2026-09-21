import frappe
from frappe.utils import now_datetime


def before_tests():
	"""Give a fresh test site the ERPNext master data the tests rely on.

	Frappe runs only the ``before_tests`` hook of the app under test, so on a
	new CI site ERPNext's setup wizard never runs: there is no company, fiscal
	year, warehouse, item group or supplier group. Complete the wizard once with
	a Bangladeshi test company. On a site that is already set up this is a no-op.
	"""
	frappe.clear_cache()

	if not frappe.get_list("Company"):
		from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

		year = now_datetime().year
		result = setup_complete(
			{
				"currency": "BDT",
				"full_name": "Test User",
				"company_name": "RMG Test Company",
				"timezone": "Asia/Dhaka",
				"company_abbr": "RMGT",
				"industry": "Manufacturing",
				"country": "Bangladesh",
				"fy_start_date": f"{year}-01-01",
				"fy_end_date": f"{year}-12-31",
				"language": "english",
				"company_tagline": "Testing",
				"email": "test@example.com",
				"password": "test",
				"chart_of_accounts": "Standard",
			}
		)

		# setup_complete reports failure instead of raising, so check for it
		if not frappe.get_list("Company"):
			frappe.throw(f"ERPNext setup wizard did not create a company: {result}")

	frappe.db.commit()  # nosemgrep
