from odoo import fields, models


class ResRegion(models.Model):
    _name = "res.region"

    name = fields.Selection(
        [
            ("Luzon", "Luzon"),
            ("Visayas", "Visayas"),
            ("Mindanao", "Mindanao"),
        ],
        string="Region Name",
        required=True,
    )
    country_id = fields.Many2one("res.country", string="Country")
    code = fields.Char("Region Code", required=True)
