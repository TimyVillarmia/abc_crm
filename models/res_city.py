from odoo import fields, models


class ResCity(models.Model):
    _name = "res.city"

    region_id = fields.Many2one("res.region", string="Region")
