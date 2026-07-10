import json
import re
from datetime import date, timedelta

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

    def _post_website_lead(self, payload):
        website_payload = {
            **payload,
            "csrf_token": self._csrf_token(),
        }
        return self.url_open(
            "/abc_crm/website/lead",
            data=website_payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    def _csrf_token(self):
        if not hasattr(self, "_cached_csrf_token"):
            response = self.url_open("/web/login")
            match = re.search(
                rb'name="csrf_token"[^>]*value="([^"]+)"',
                response.content,
            )
            self.assertTrue(match, "Could not find CSRF token on login page")
            self._cached_csrf_token = match.group(1).decode()
        return self._cached_csrf_token

    def _json_response(self, response):
        return json.loads(response.content.decode())

    def _lead_count(self):
        return self.env["crm.lead"].with_context(active_test=False).search_count([])

    def _valid_payload(self, **overrides):
        payload = {
            "contact_name": "  Jane Buyer  ",
            "partner_name": "  ABC Construction  ",
            "function": "  Purchasing Manager  ",
            "email_from": "  jane@example.com  ",
            "phone": "  +639170000000  ",
            "message": "  Website inquiry  ",
            "project_name": "  Warehouse Extension  ",
            "project_location": "  Cebu City  ",
            "project_type": "  Commercial  ",
            "estimated_project_value": "1250000.50",
            "target_completion_date": (date.today() + timedelta(days=180)).isoformat(),
            "company_type": "contractor",
            "is_five_storey_up": "yes",
            "is_ongoing": "no",
            "is_aac_user": "yes",
            "is_open": "no",
            "has_aac_needs": "yes",
            "has_design_specifications": "yes",
            "utm_source": "  Website  ",
            "utm_medium": "  Form  ",
            "utm_campaign": "  June Launch  ",
        }
        payload.update(overrides)
        return payload

    def test_create_lead_from_json_payload(self):
        payload = self._valid_payload()
        response = self._post_lead(payload)
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
        self.assertEqual(lead.function, "Purchasing Manager")
        self.assertEqual(lead.email_from, "jane@example.com")
        self.assertEqual(lead.phone, "+639170000000")
        self.assertEqual(lead.project_name, "Warehouse Extension")
        self.assertEqual(lead.street, "Cebu City")
        self.assertEqual(lead.project_type, "Commercial")
        self.assertEqual(lead.estimated_project_value, 1250000.50)
        self.assertEqual(
            lead.target_completion_date.isoformat(),
            payload["target_completion_date"],
        )
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
        self.assertEqual(body["lead"]["function"], "Purchasing Manager")
        self.assertEqual(body["lead"]["estimated_project_value"], 1250000.50)
        self.assertEqual(
            body["lead"]["target_completion_date"],
            payload["target_completion_date"],
        )
        self.assertEqual(body["lead"]["company_type"], "contractor")
        self.assertEqual(body["lead"]["rating"], 65)
        self.assertEqual(body["lead"]["utm_source"], "Website")
        self.assertEqual(body["lead"]["utm_medium"], "Form")
        self.assertEqual(body["lead"]["utm_campaign"], "June Launch")

    def test_website_route_creates_lead_without_bearer_auth(self):
        response = self._post_website_lead(self._valid_payload())
        body = self._json_response(response)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(body["success"])

        lead = self.env["crm.lead"].browse(body["lead"]["id"])
        self.assertTrue(lead.exists())
        self.assertEqual(lead.name, "Website inquiry")
        self.assertEqual(lead.contact_name, "Jane Buyer")
        self.assertEqual(lead.rating, 65)

    def test_website_route_rejects_missing_required_fields(self):
        response = self._post_website_lead(
            {
                "contact_name": "Jane Buyer",
            }
        )
        body = self._json_response(response)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(body["success"])
        self.assertIn("Missing required field(s):", body["error"])
        self.assertIn("partner_name", body["error"])

    def test_website_route_honeypot_does_not_create_lead(self):
        before_count = self.env["crm.lead"].search_count([])
        payload = self._valid_payload(abc_crm_hp="filled by bot")

        response = self._post_website_lead(payload)
        body = self._json_response(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            body,
            {
                "success": True,
                "lead": False,
            },
        )
        self.assertEqual(self.env["crm.lead"].search_count([]), before_count)

    def test_website_route_reuses_existing_utm_records_by_name(self):
        utm_values = {
            "utm_source": "Website Route Source",
            "utm_medium": "Website Route Medium",
            "utm_campaign": "Website Route Campaign",
        }

        first_response = self._post_website_lead(self._valid_payload(**utm_values))
        first_body = self._json_response(first_response)

        second_response = self._post_website_lead(
            self._valid_payload(message="Second website route inquiry", **utm_values)
        )
        second_body = self._json_response(second_response)

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)

        first_lead = self.env["crm.lead"].browse(first_body["lead"]["id"])
        second_lead = self.env["crm.lead"].browse(second_body["lead"]["id"])

        self.assertEqual(first_lead.source_id, second_lead.source_id)
        self.assertEqual(first_lead.medium_id, second_lead.medium_id)
        self.assertEqual(first_lead.campaign_id, second_lead.campaign_id)
        self.assertEqual(first_lead.source_id.name, "Website")
        self.assertEqual(first_lead.medium_id.name, "Website Form")
        self.assertEqual(first_lead.campaign_id.name, "Website Route Campaign")

        self.assertEqual(
            self.env["utm.source"].search_count([("name", "=", "Website")]),
            1,
        )
        self.assertEqual(
            self.env["utm.medium"].search_count([("name", "=", "Website Form")]),
            1,
        )
        self.assertEqual(
            self.env["utm.campaign"].search_count(
                [("name", "=", "Website Route Campaign")]
            ),
            1,
        )

    def test_website_route_qualified_lead_is_converted_without_assignment(self):
        response = self._post_website_lead(
            self._valid_payload(
                is_five_storey_up="yes",
                is_ongoing="yes",
                is_aac_user="yes",
                is_open="yes",
                has_aac_needs="yes",
                has_design_specifications="yes",
            )
        )
        body = self._json_response(response)

        self.assertEqual(response.status_code, 201)

        lead = self.env["crm.lead"].browse(body["lead"]["id"])

        self.assertEqual(lead.rating, 100)
        self.assertEqual(lead.type, "opportunity")
        self.assertTrue(lead.active)
        self.assertFalse(lead.user_id)
        self.assertFalse(lead.team_id)

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
        invalid_values = [
            "true",
            "false",
            "1",
            "0",
            "y",
            "n",
            True,
            False,
            "sometimes",
        ]

        for invalid_value in invalid_values:
            with self.subTest(invalid_value=invalid_value):
                before_count = self._lead_count()
                response = self._post_lead(self._valid_payload(is_open=invalid_value))
                body = self._json_response(response)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    body,
                    {
                        "success": False,
                        "error": "Invalid boolean value: %s" % invalid_value,
                    },
                )
                self.assertEqual(self._lead_count(), before_count)

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
