{
    "name": "ABC CRM",
    "author": "MIS",
    "version": "1.0.0",
    "license": "OEEL-1",
    "depends": [
        "base",
        "spreadsheet_dashboard",
        "board",
        "sale_crm",
        "partnership",
        "crm",
        "sales_team",
        "website",
        "phone_validation",
    ],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/res.region.csv",
        "data/config_parameters.xml",
        "data/lost_reason_data.xml",
        "views/crm_lead_views.xml",
        "views/res_partner_views.xml",
        "views/website_snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "abc_crm/static/src/js/abc_crm_multi_step_form.js",
            "abc_crm/static/src/scss/abc_crm_multi_step_form.scss",
        ],
        "web.assets_tests": [
            "abc_crm/static/tests/abc_crm_multi_step_form_security_tests.js",
        ],
    },
    "installable": True,
    "application": True,
}
