from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCrmLead(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param(
            "abc_crm.auto_convert_threshold",
            "70",
        )
        self.country_ph = self.env.ref("base.ph", raise_if_not_found=False)
        if not self.country_ph:
            self.country_ph = self.env["res.country"].create(
                {
                    "name": "Philippines",
                    "code": "PH",
                }
            )

    def _future_date(self):
        return fields.Date.add(fields.Date.today(), days=30)

    def _valid_lead_values(self, **overrides):
        values = {
            "name": "ABC CRM test lead",
            "type": "lead",
            "email_from": "buyer@example.com",
            "phone": "+639170000000",
            "target_completion_date": self._future_date(),
        }
        values.update(overrides)
        return values

    def _create_lead(self, **overrides):
        return self.env["crm.lead"].create(self._valid_lead_values(**overrides))

    def test_rating_is_computed_from_qualification_fields(self):
        lead = self._create_lead(
            is_five_storey_up=True,
            is_ongoing=False,
            is_aac_user=True,
            is_open=False,
            has_aac_needs=True,
            has_design_specifications=True,
        )

        self.assertEqual(lead.rating, 65)

    def test_qualified_lead_is_converted_without_assignment(self):
        lead = self._create_lead(
            user_id=self.env.user.id,
            team_id=self.env["crm.team"].create({"name": "ABC CRM Test Team"}).id,
            is_five_storey_up=True,
            is_ongoing=True,
            is_aac_user=True,
            is_open=True,
            has_aac_needs=True,
            has_design_specifications=True,
        )

        self.assertEqual(lead.rating, 100)
        self.assertEqual(lead.type, "opportunity")
        self.assertTrue(lead.active)
        self.assertFalse(lead.user_id)
        self.assertFalse(lead.team_id)

    def test_unqualified_lead_is_marked_lost_with_default_reason(self):
        lead = self._create_lead(
            is_five_storey_up=True,
            is_ongoing=False,
            is_aac_user=False,
            is_open=False,
            has_aac_needs=False,
            has_design_specifications=False,
        )

        self.assertEqual(lead.rating, 15)
        self.assertFalse(lead.active)
        self.assertEqual(
            lead.lost_reason_id,
            self.env.ref("abc_crm.lost_reason_unqualified"),
        )

    def test_project_location_combines_address_parts(self):
        region = self.env["res.region"].create(
            {
                "name": "Visayas",
                "code": "VIS-TEST",
                "country_id": self.country_ph.id,
            }
        )

        lead = self._create_lead(
            street="Block 1",
            street2="Lot 2",
            city="Cebu City",
            region_id=region.id,
            zip="6000",
            country_id=self.country_ph.id,
        )

        self.assertEqual(
            lead.project_location,
            "Block 1, Lot 2, Cebu City, Visayas, 6000, Philippines",
        )

    def test_estimated_project_value_cannot_be_negative(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Estimated Project Value cannot be negative.",
        ):
            self._create_lead(estimated_project_value=-1)

    def test_target_completion_date_cannot_be_in_the_past(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Target Completion Date cannot be in the past.",
        ):
            self._create_lead(
                target_completion_date=fields.Date.subtract(
                    fields.Date.today(),
                    days=1,
                )
            )

    def test_phone_must_be_valid_when_provided(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Please enter a valid phone or landline number.",
        ):
            self._create_lead(phone="not a phone")
