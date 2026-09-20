"""Sample test documents: lightweight stand-ins for real Frappe documents.

The business rules in ``purchase_invoice_matching`` and ``finance_controls`` only
ever read plain fields off a document, so they can be exercised without a
database by passing these objects in. This is what keeps the test suite fast
enough to run on every push, and it is what the demonstration runner in
``demo_scenarios.py`` uses as well.
"""


class SampleDoc:
	"""A document that supports both ``doc.field`` and ``doc.get("field")``."""

	def __init__(self, **fields):
		self.__dict__.update(fields)

	def get(self, fieldname, default=None):
		return self.__dict__.get(fieldname, default)

	def __repr__(self):
		return f"SampleDoc({self.__dict__})"


def make_purchase_order(item_code="ITEM-001", rate=10.0, qty=10.0):
	"""A Purchase Order carrying the agreed rate for one item."""
	return SampleDoc(items=[SampleDoc(item_code=item_code, rate=rate, qty=qty)])


def make_purchase_receipt(item_code="ITEM-001", received_qty=10.0, rejected_qty=0.0):
	"""A Purchase Receipt carrying the received and QC-rejected quantities.

	Mirrors ERPNext exactly: ``qty`` is the *Accepted Quantity* and the framework
	enforces ``received_qty = qty + rejected_qty``.
	"""
	accepted_qty = received_qty - rejected_qty
	return SampleDoc(
		items=[
			SampleDoc(
				item_code=item_code,
				qty=accepted_qty,
				rejected_qty=rejected_qty,
				received_qty=received_qty,
			)
		]
	)


def make_purchase_invoice(claimed_amount, po="PO-001", receipt="PR-001"):
	"""A supplier invoice claiming ``claimed_amount`` against a PO and a receipt."""
	return SampleDoc(
		custom_po_no=po,
		custom_po_receipt_=receipt,
		grand_total=claimed_amount,
		custom_match_status=None,
		custom_difference_amount=None,
	)


def make_payment_entry(
	voucher_type="Bank Entry",
	mode_of_payment="Bank Draft",
	cheque_withdrawer=None,
	withdrawer_designation=None,
):
	"""A Payment Entry with the fields the finance controls validate."""
	return SampleDoc(
		custom_voucher_type=voucher_type,
		mode_of_payment=mode_of_payment,
		custom_cheque_withdrawer=cheque_withdrawer,
		custom_withdrawer_designation=withdrawer_designation,
	)
