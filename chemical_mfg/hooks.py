app_name = "chemical_mfg"
app_title = "Chemical Mfg"
app_publisher = "sai"
app_description = "mfg"
app_email = "sai@aitsind.com"
app_license = "mit"


override_doctype_class = {
    "Job Card": "chemical_mfg.chemical_mfg.overrides.jobcard.ChemicalJobCard",
}

# override_doctype_class = {
#     "Job Card": "chemical_mfg.chemical_mfg.overrides.jobcard.CustomJobCard",
#     "Work Order": "chemical_mfg.chemical_mfg.overrides.workorder.CustomWorkOrder",
# }


# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "chemical_mfg",
# 		"logo": "/assets/chemical_mfg/logo.png",
# 		"title": "Chemical Mfg",
# 		"route": "/chemical_mfg",
# 		"has_permission": "chemical_mfg.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/chemical_mfg/css/chemical_mfg.css"
# app_include_js = "/assets/chemical_mfg/js/chemical_mfg.js"

# include js, css files in header of web template
# web_include_css = "/assets/chemical_mfg/css/chemical_mfg.css"
# web_include_js = "/assets/chemical_mfg/js/chemical_mfg.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "chemical_mfg/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "chemical_mfg/public/icons.svg"

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

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "chemical_mfg.utils.jinja_methods",
# 	"filters": "chemical_mfg.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "chemical_mfg.install.before_install"
# after_install = "chemical_mfg.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "chemical_mfg.uninstall.before_uninstall"
# after_uninstall = "chemical_mfg.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "chemical_mfg.utils.before_app_install"
# after_app_install = "chemical_mfg.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "chemical_mfg.utils.before_app_uninstall"
# after_app_uninstall = "chemical_mfg.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "chemical_mfg.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"chemical_mfg.tasks.all"
# 	],
# 	"daily": [
# 		"chemical_mfg.tasks.daily"
# 	],
# 	"hourly": [
# 		"chemical_mfg.tasks.hourly"
# 	],
# 	"weekly": [
# 		"chemical_mfg.tasks.weekly"
# 	],
# 	"monthly": [
# 		"chemical_mfg.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "chemical_mfg.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "chemical_mfg.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "chemical_mfg.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["chemical_mfg.utils.before_request"]
# after_request = ["chemical_mfg.utils.after_request"]

# Job Events
# ----------
# before_job = ["chemical_mfg.utils.before_job"]
# after_job = ["chemical_mfg.utils.after_job"]

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
# 	"chemical_mfg.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

