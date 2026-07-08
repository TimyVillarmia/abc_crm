from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import single_email_re

from odoo.addons.phone_validation.tools.phone_validation import (
    phone_parse,
)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    project_name = fields.Char("Project Name")
    project_location = fields.Char(
        string="Project Location",
        compute="_compute_project_location",
        store=True,
    )
    project_type = fields.Char("Project Type")
    estimated_project_value = fields.Float("Estimated Project Value")
    target_completion_date = fields.Date("Target Completion Date")
    company_type = fields.Selection(
        [
            ("contractor", "Contractor"),
            ("developer", "Developer"),
            ("homeowner", "Homeowner"),
            ("architect", "Architect"),
            ("trader", "Trader"),
        ]
    )
    region_id = fields.Many2one("res.region", string="Region Name")

    # criteria
    is_five_storey_up = fields.Boolean()
    is_ongoing = fields.Boolean()
    is_aac_user = fields.Boolean()
    is_open = fields.Boolean()
    has_aac_needs = fields.Boolean()
    has_design_specifications = fields.Boolean()
    rating = fields.Integer(compute="_compute_lead_rating")
    is_restricted = fields.Boolean(compute="_compute_is_restricted")

    def _compute_is_restricted(self):
        is_restricted = self.env.user.has_group(
            "abc_crm.group_marketing"
        ) or self.env.user.has_group("abc_crm.group_general_manager")
        for lead in self:
            lead.is_restricted = is_restricted

    @api.model_create_multi
    def create(self, vals_list):
        qualifying_fields = {
            "is_five_storey_up",
            "is_ongoing",
            "is_aac_user",
            "is_open",
            "has_aac_needs",
            "has_design_specifications",
        }

        records = super().create(vals_list)

        has_qualifying = any(
            qualifying_fields.intersection(vals.keys()) for vals in vals_list
        )

        if not has_qualifying:
            return records

        records._compute_lead_rating()

        threshold = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("abc_crm.auto_convert_threshold", default=70.0)
        )

        qualified = records.filtered(
            lambda lead: lead.type == "lead" and lead.rating >= threshold
        )
        unqualified = records.filtered(
            lambda lead: lead.type == "lead" and lead.rating < threshold
        )

        if qualified:
            qualified.convert_opportunity(
                partner=False,
                user_ids=False,
                team_id=False,
            )
        if unqualified:
            unqualified.action_set_lost()

        return records

    def write(self, vals):
        qualifying_fields = {
            "is_five_storey_up",
            "is_ongoing",
            "is_aac_user",
            "is_open",
            "has_aac_needs",
            "has_design_specifications",
        }

        if not qualifying_fields.intersection(vals.keys()):
            return super().write(vals)

        rating_before = {lead.id: lead.rating for lead in self}

        res = super().write(vals)

        self._compute_lead_rating()

        threshold = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("abc_crm.auto_convert_threshold", default=70.0)
        )

        changed = self.filtered(lambda lead: lead.rating != rating_before[lead.id])

        qualified = changed.filtered(
            lambda lead: lead.type == "lead" and lead.rating >= threshold
        )
        unqualified = changed.filtered(
            lambda lead: lead.type == "lead" and lead.rating < threshold
        )

        if qualified:
            qualified.convert_opportunity(
                partner=False,
                user_ids=False,
                team_id=False,
            )
        if unqualified:
            unqualified.action_set_lost()

        return res

    @api.depends("street", "street2", "city", "region_id", "zip", "country_id")
    def _compute_project_location(self):
        for lead in self:
            parts = [
                lead.street,
                lead.street2,
                lead.city,
                lead.region_id.name if lead.region_id else False,
                lead.zip,
                lead.country_id.name if lead.country_id else False,
            ]
            lead.project_location = ", ".join(filter(None, parts))

    @api.constrains("email_from")
    def _check_email_from(self):
        for lead in self:
            email = (lead.email_from or "").strip()

            if not email:
                raise ValidationError(
                    _("Email is required.")
                )

            if not single_email_re.fullmatch(email):
                raise ValidationError(
                    _(
                        "Please enter a valid email address."
                    )
                )

    @api.depends(
        "is_five_storey_up",
        "is_ongoing",
        "is_aac_user",
        "is_open",
        "has_aac_needs",
        "has_design_specifications",
    )
    def _compute_lead_rating(self):
        for lead in self:
            total = 0
            if lead.is_five_storey_up:
                total += 15
            if lead.is_ongoing:
                total += 25
            if lead.has_aac_needs:
                total += 15
            if lead.is_aac_user:
                total += 10
            if lead.is_open:
                total += 10
            if lead.has_design_specifications:
                total += 25
            lead.rating = total

    def action_set_lost(self, **kwargs):
        lost_reason = kwargs.get("lost_reason_id")

        if not lost_reason:
            unqualified_reason = self.env.ref(
                "abc_crm.lost_reason_unqualified", raise_if_not_found=False
            )
            if unqualified_reason:
                kwargs["lost_reason_id"] = unqualified_reason.id

        return super().action_set_lost(**kwargs)

    
    @api.constrains("estimated_project_value")
    def _check_estimated_project_value(self):
        for lead in self:
            if lead.estimated_project_value < 0:
                raise ValidationError(
                    _(
                        "Estimated Project Value cannot be negative."
                    )
                )
        
    @api.constrains("target_completion_date")
    def _check_target_completion_date(self):
        for lead in self:
            if not lead.target_completion_date:
                continue

            today = fields.Date.context_today(lead)

            if lead.target_completion_date < today:
                raise ValidationError(
                    _(
                        "Target Completion Date cannot "
                        "be in the past."
                    )
                )
    
    @api.constrains("phone", "country_id")
    def _check_phone(self):
        for lead in self:
            phone = (lead.phone or "").strip()

            if not phone:
                continue

            country_code = (
                lead.country_id.code
                if lead.country_id
                else "PH"
            )

            try:
                phone_parse(phone, country_code)
            except UserError as exc:
                raise ValidationError(
                    _(
                        "Please enter a valid phone or "
                        "landline number."
                    )
                ) from exc

    def convert_opportunity(self, partner=False, user_ids=False, team_id=False):
        result = super().convert_opportunity(
            partner=partner,
            user_ids=False,
            team_id=False,
        )

        self.write(
            {
                "user_id": False,
                "team_id": False,
            }
        )

        group = self.env.ref("abc_crm.group_sales_manager", raise_if_not_found=False)

        managers = (
            group.user_ids.mapped("partner_id") if group else self.env["res.partner"]
        )

        if managers:
            self.message_subscribe(partner_ids=managers.ids)

            self.message_post(
                body="New opportunity requires assignment.",
                partner_ids=managers.ids,
                message_type="notification",
            )

        return result
