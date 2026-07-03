{
    "name": "ABC CRM",
    "author": "MIS",
    "version": "1.0.0",
    "license": "OEEL-1",
    "depends": [
        "crm",
        "base",
        "website",
    ],
    "data": [
        "data/res.region.csv",
        "data/config_parameters.xml",
        "data/lost_reason_data.xml",
        "views/crm_lead_views.xml",
        "views/website_snippets.xml",
        "security/ir.model.access.csv",
        "security/res_groups.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "abc_crm/static/src/js/abc_crm_multi_step_form.js",
            "abc_crm/static/src/scss/abc_crm_multi_step_form.scss",
        ],
    },
    "installable": True,
    "application": True,
}
