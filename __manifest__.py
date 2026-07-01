{
    "name": "ABC CRM",
    "author": "MIS",
    "version": "1.0.0",
    "license": "OEEL-1",
    "depends": [
        "crm",
        "base",
    ],
    "data": [
        "data/res.region.csv",
        "data/config_parameters.xml",
        "views/crm_lead_views.xml",
        "security/ir.model.access.csv",
        "security/res_groups.xml",
        # 'data/ir_cron.xml',
        # 'data/crm_pls_fields_data.xml',
    ],
    "installable": True,
    "application": True,
}
