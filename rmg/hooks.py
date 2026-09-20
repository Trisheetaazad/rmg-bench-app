app_name = "rmg"
app_title = "RMG Management"
app_publisher = "Trisheeta"
app_description = "Sales Invoice and Purchase Order Management for RMG"
app_email = "trisheetaazad@gmail.com"
app_license = "mit"


# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "rmg",
# 		"logo": "/assets/rmg/logo.png",
# 		"title": "RMG Management",
# 		"route": "/rmg",
# 		"has_permission": "rmg.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/rmg/css/rmg.css"
# app_include_js = "/assets/rmg/js/rmg.js"

# include js, css files in header of web template
# web_include_css = "/assets/rmg/css/rmg.css"
# web_include_js = "/assets/rmg/js/rmg.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "rmg/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Payment Entry": "public/js/finance_controls.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "rmg/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "rmg.utils.jinja_methods",
# 	"filters": "rmg.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "rmg.install.before_install"
# after_install = "rmg.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "rmg.uninstall.before_uninstall"
# after_uninstall = "rmg.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "rmg.utils.before_app_install"
# after_app_install = "rmg.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "rmg.utils.before_app_uninstall"
# after_app_uninstall = "rmg.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "rmg.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "rmg.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Payment Entry": {
		"validate": "rmg.rmg_management.finance_controls.validate_payment_entry",
	},
	"Letter Of Credit": {
		"after_insert": "rmg.rmg_management.finance_controls.refresh_lc_utilization",
		"on_update": "rmg.rmg_management.finance_controls.refresh_lc_utilization",
		"on_update_after_submit": "rmg.rmg_management.finance_controls.refresh_lc_utilization",
	},
	"LC Allocation": {
		"after_insert": "rmg.rmg_management.finance_controls.update_lc_utilization",
		"on_update": "rmg.rmg_management.finance_controls.update_lc_utilization",
		"on_trash": "rmg.rmg_management.finance_controls.remove_lc_utilization",
	},
	"Purchase Invoice": {
		"validate": "rmg.rmg_management.purchase_invoice_matching.validate",
	},
}

after_install = "rmg.rmg_management.purchase_invoice_matching.ensure_custom_fields"
after_migrate = "rmg.rmg_management.purchase_invoice_matching.ensure_custom_fields"

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"rmg.tasks.all"
# 	],
# 	"daily": [
# 		"rmg.tasks.daily"
# 	],
# 	"hourly": [
# 		"rmg.tasks.hourly"
# 	],
# 	"weekly": [
# 		"rmg.tasks.weekly"
# 	],
# 	"monthly": [
# 		"rmg.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "rmg.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "rmg.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "rmg.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "rmg.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["rmg.utils.before_request"]
# after_request = ["rmg.utils.after_request"]

# Job Events
# ----------
# before_job = ["rmg.utils.before_job"]
# after_job = ["rmg.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"rmg.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

