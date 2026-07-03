{
    "name": "ABC CRM",
    "author": "MIS",
    "version": "1.0.0",
    "license": "OEEL-1",
    "depends": [
        "crm",
        "sales_team",
        "base",
    ],
    "data": [
        "data/res.region.csv",
        "data/config_parameters.xml",
        "views/crm_lead_views.xml",
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/lost_reason_data.xml",
    ],
    "installable": True,
    "application": True,
}
