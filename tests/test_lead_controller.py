import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestAbcCrmLeadController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_key = (
            cls.env["res.users.apikeys"]
            .with_user(cls.env.ref("base.user_admin"))
            .sudo()
            ._generate(None, "ABC CRM controller test", False)
        )

    def _post_lead(self, payload):
        return self.url_open(
            "/abc_crm/lead",
            data=json.dumps(payload),
            headers={
                "Authorization": "bearer %s" % self.api_key,
                "Content-Type": "application/json",
            },
        )

    def _json_response(self, response):
        return json.loads(response.content.decode())

    def _valid_payload(self, **overrides):
        payload = {
            "contact_name": "  Jane Buyer  ",
            "partner_name": "  ABC Construction  ",
            "email_from": "  jane@example.com  ",
            "phone": "  +63 900 000 0000  ",
            "message": "  Website inquiry  ",
            "project_name": "  Warehouse Extension  ",
            "project_location": "  Cebu City  ",
            "project_type": "  Commercial  ",
            "estimated_project_value": "1250000.50",
            "target_completion_date": "2026-12-31",
            "company_type": "contractor",
            "is_five_storey_up": "yes",
            "is_ongoing": "0",
            "is_aac_user": True,
            "is_open": False,
            "has_aac_needs": "true",
            "has_design_specifications": 1,
            "utm_source": "  Website  ",
            "utm_medium": "  Form  ",
            "utm_campaign": "  June Launch  ",
        }
        payload.update(overrides)
        return payload

    def test_create_lead_from_json_payload(self):
        response = self._post_lead(self._valid_payload())
        body = self._json_response(response)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(body["success"])

        lead = self.env["crm.lead"].browse(body["lead"]["id"])
        self.assertTrue(lead.exists())
        self.assertEqual(lead.name, "Website inquiry")
        self.assertEqual(lead.description, "<p>Website inquiry</p>")
        self.assertEqual(lead.type, "lead")
        self.assertEqual(lead.contact_name, "Jane Buyer")
        self.assertEqual(lead.partner_name, "ABC Construction")
        self.assertEqual(lead.email_from, "jane@example.com")
        self.assertEqual(lead.phone, "+63 900 000 0000")
        self.assertEqual(lead.project_name, "Warehouse Extension")
        self.assertEqual(lead.street, "Cebu City")
        self.assertEqual(lead.project_type, "Commercial")
        self.assertEqual(lead.estimated_project_value, 1250000.50)
        self.assertEqual(lead.target_completion_date.isoformat(), "2026-12-31")
        self.assertEqual(lead.company_type, "contractor")
        self.assertTrue(lead.is_five_storey_up)
        self.assertFalse(lead.is_ongoing)
        self.assertTrue(lead.is_aac_user)
        self.assertFalse(lead.is_open)
        self.assertTrue(lead.has_aac_needs)
        self.assertTrue(lead.has_design_specifications)
        self.assertEqual(lead.rating, 65)
        self.assertEqual(lead.source_id.name, "Website")
        self.assertEqual(lead.medium_id.name, "Form")
        self.assertEqual(lead.campaign_id.name, "June Launch")

        self.assertEqual(body["lead"]["name"], "Website inquiry")
        self.assertEqual(body["lead"]["type"], "lead")
        self.assertEqual(body["lead"]["active"], lead.active)
        self.assertEqual(body["lead"]["project_name"], "Warehouse Extension")
        self.assertEqual(body["lead"]["project_location"], "Cebu City")
        self.assertEqual(body["lead"]["project_type"], "Commercial")
        self.assertEqual(body["lead"]["estimated_project_value"], 1250000.50)
        self.assertEqual(body["lead"]["target_completion_date"], "2026-12-31")
        self.assertEqual(body["lead"]["company_type"], "contractor")
        self.assertEqual(body["lead"]["rating"], 65)
        self.assertEqual(body["lead"]["utm_source"], "Website")
        self.assertEqual(body["lead"]["utm_medium"], "Form")
        self.assertEqual(body["lead"]["utm_campaign"], "June Launch")

    def test_rejects_missing_required_fields(self):
        response = self._post_lead(
            {
                "contact_name": "Jane Buyer",
            }
        )
        body = self._json_response(response)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(body["success"])
        self.assertIn("Missing required field(s):", body["error"])
        self.assertIn("partner_name", body["error"])
        self.assertIn("email_from", body["error"])
        self.assertIn("phone", body["error"])
        self.assertIn("message", body["error"])
        self.assertIn("project_name", body["error"])
        self.assertIn("project_location", body["error"])
        self.assertIn("project_type", body["error"])
        self.assertIn("company_type", body["error"])
        self.assertIn("is_five_storey_up", body["error"])
        self.assertIn("is_ongoing", body["error"])
        self.assertIn("is_aac_user", body["error"])
        self.assertIn("is_open", body["error"])
        self.assertIn("has_aac_needs", body["error"])
        self.assertIn("has_design_specifications", body["error"])
        self.assertIn("utm_source", body["error"])
        self.assertIn("utm_medium", body["error"])

    def test_rejects_unknown_fields(self):
        payload = self._valid_payload(name="Not accepted by endpoint")
        response = self._post_lead(payload)
        body = self._json_response(response)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            body,
            {
                "success": False,
                "error": "Unknown field(s): name",
            },
        )

    def test_rejects_invalid_company_type(self):
        response = self._post_lead(self._valid_payload(company_type="supplier"))
        body = self._json_response(response)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(body["success"])
        self.assertIn("Invalid company_type.", body["error"])

    def test_rejects_invalid_boolean_value(self):
        response = self._post_lead(self._valid_payload(is_open="sometimes"))
        body = self._json_response(response)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            body,
            {
                "success": False,
                "error": "Invalid boolean value: sometimes",
            },
        )

    def test_rejects_invalid_estimated_project_value(self):
        response = self._post_lead(
            self._valid_payload(estimated_project_value="not a number")
        )
        body = self._json_response(response)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            body,
            {
                "success": False,
                "error": "Invalid estimated_project_value: not a number",
            },
        )

    def test_rejects_invalid_target_completion_date(self):
        response = self._post_lead(
            self._valid_payload(target_completion_date="12/31/2026")
        )
        body = self._json_response(response)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            body,
            {
                "success": False,
                "error": "Invalid target_completion_date. Use YYYY-MM-DD.",
            },
        )