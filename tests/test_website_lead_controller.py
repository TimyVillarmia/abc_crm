import json
import re
from contextlib import contextmanager
from datetime import date, timedelta

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestAbcCrmWebsiteLeadController(HttpCase):
    def _csrf_token(self):
        response = self.url_open("/web/login")
        match = re.search(
            rb'name="csrf_token"[^>]*value="([^"]+)"',
            response.content,
        )
        self.assertTrue(match, "Could not find CSRF token on login page")
        return match.group(1).decode()

    def _json_response(self, response):
        return json.loads(response.content.decode())

    def _lead_count(self):
        return self.env["crm.lead"].with_context(active_test=False).search_count([])

    @contextmanager
    def _assert_lead_delta(self, expected_delta):
        before = self._lead_count()
        yield before
        self.assertEqual(self._lead_count(), before + expected_delta)

    def _valid_payload(self, **overrides):
        payload = {
            "contact_name": "Jane Buyer",
            "partner_name": "ABC Construction",
            "function": "Purchasing Manager",
            "email_from": "jane@example.com",
            "phone": "+639170000000",
            "message": "Website inquiry for a warehouse project",
            "project_name": "Warehouse Extension",
            "project_location": "Cebu City",
            "project_type": "Commercial",
            "estimated_project_value": "1250000.50",
            "target_completion_date": (date.today() + timedelta(days=180)).isoformat(),
            "company_type": "contractor",
            "is_five_storey_up": "yes",
            "is_ongoing": "no",
            "is_aac_user": "yes",
            "is_open": "no",
            "has_aac_needs": "yes",
            "has_design_specifications": "yes",
            "utm_campaign": "Security Tests",
        }
        payload.update(overrides)
        return payload

    def _post_website_lead(self, payload, csrf_token=None, include_csrf=True):
        data = dict(payload)
        if include_csrf:
            data["csrf_token"] = csrf_token if csrf_token is not None else self._csrf_token()

        return self.url_open(
            "/abc_crm/website/lead",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def _post_phone_validation(self, phone, csrf_token=None, include_csrf=True):
        data = {"phone": phone}
        if include_csrf:
            data["csrf_token"] = csrf_token if csrf_token is not None else self._csrf_token()

        return self.url_open(
            "/abc_crm/website/phone/validate",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def _assert_rejected_without_lead(self, payload, expected_status=400):
        with self._assert_lead_delta(0):
            response = self._post_website_lead(payload)

        self.assertEqual(response.status_code, expected_status)
        return self._json_response(response)

    def test_valid_submission_creates_exactly_one_lead(self):
        payload = self._valid_payload()

        with self._assert_lead_delta(1):
            response = self._post_website_lead(payload)

        body = self._json_response(response)
        self.assertIn(response.status_code, (200, 201))
        self.assertTrue(body["success"])

        lead = self.env["crm.lead"].browse(body["lead"]["id"])
        self.assertTrue(lead.exists())
        self.assertEqual(lead.name, payload["message"])
        self.assertEqual(lead.contact_name, payload["contact_name"])
        self.assertEqual(lead.partner_name, payload["partner_name"])
        self.assertEqual(lead.function, payload["function"])
        self.assertEqual(lead.email_from, payload["email_from"])
        self.assertEqual(lead.phone, payload["phone"])
        self.assertEqual(lead.project_name, payload["project_name"])
        self.assertEqual(lead.street, payload["project_location"])
        self.assertEqual(lead.project_type, payload["project_type"])
        self.assertEqual(lead.company_type, payload["company_type"])
        self.assertEqual(lead.estimated_project_value, 1250000.50)
        self.assertEqual(
            lead.target_completion_date.isoformat(),
            payload["target_completion_date"],
        )
        self.assertTrue(lead.is_five_storey_up)
        self.assertFalse(lead.is_ongoing)
        self.assertTrue(lead.is_aac_user)
        self.assertFalse(lead.is_open)
        self.assertTrue(lead.has_aac_needs)
        self.assertTrue(lead.has_design_specifications)
        self.assertEqual(lead.source_id.name, "Website")
        self.assertEqual(lead.medium_id.name, "Website Form")

    def test_invalid_csrf_token_is_rejected_without_creating_lead(self):
        with self._assert_lead_delta(0):
            response = self._post_website_lead(
                self._valid_payload(),
                csrf_token="intentionally-invalid-token",
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Bad Request", response.content)

    def test_missing_csrf_token_is_rejected_without_creating_lead(self):
        with self._assert_lead_delta(0):
            response = self._post_website_lead(
                self._valid_payload(),
                include_csrf=False,
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Bad Request", response.content)

    def test_server_side_validation_bypass_is_rejected(self):
        invalid_cases = [
            {"email_from": "invalid-email"},
            {"phone": "abc"},
            {"message": "short"},
            {"company_type": "invalid"},
            {"is_five_storey_up": "maybe"},
            {"estimated_project_value": "-100"},
        ]

        for overrides in invalid_cases:
            with self.subTest(overrides=overrides):
                body = self._assert_rejected_without_lead(self._valid_payload(**overrides))
                self.assertFalse(body["success"])

    def test_phone_validation_route_uses_the_lead_phone_parser(self):
        for phone in ["09170000000", "+639170000000", "02 8123 4567"]:
            with self.subTest(phone=phone):
                with self._assert_lead_delta(0):
                    response = self._post_phone_validation(phone)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(self._json_response(response), {"valid": True})

        with self._assert_lead_delta(0):
            response = self._post_phone_validation("1234567")

        self.assertEqual(response.status_code, 200)
        body = self._json_response(response)
        self.assertFalse(body["valid"])
        self.assertEqual(
            body["error"],
            "Please enter a valid phone or landline number.",
        )

    def test_unknown_fields_are_rejected(self):
        body = self._assert_rejected_without_lead(self._valid_payload(is_admin="true"))

        self.assertEqual(
            body,
            {
                "success": False,
                "error": "Unknown field(s): is_admin",
            },
        )

    def test_honeypot_returns_neutral_success_without_creating_lead(self):
        with self._assert_lead_delta(0):
            response = self._post_website_lead(self._valid_payload(abc_crm_hp="bot-value"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._json_response(response),
            {
                "success": True,
                "lead": False,
            },
        )

    def test_field_length_limits_reject_oversized_values(self):
        oversized_values = {
            "contact_name": "A" * 121,
            "partner_name": "A" * 161,
            "function": "A" * 121,
            "project_name": "A" * 161,
            "project_location": "A" * 256,
            "project_type": "A" * 121,
            "email_from": ("%s@example.com" % ("a" * 250)),
            "phone": "+63917" + ("0" * 40),
            "message": "A" * 1001,
        }

        for field_name, value in oversized_values.items():
            with self.subTest(field_name=field_name):
                body = self._assert_rejected_without_lead(
                    self._valid_payload(**{field_name: value})
                )
                self.assertFalse(body["success"])
                self.assertIn(field_name, body["error"])

    def test_allowed_selection_values(self):
        for company_type in [
            "contractor",
            "developer",
            "homeowner",
            "architect",
            "trader",
        ]:
            with self.subTest(company_type=company_type):
                with self._assert_lead_delta(1):
                    response = self._post_website_lead(
                        self._valid_payload(company_type=company_type)
                    )
                self.assertEqual(response.status_code, 201)

        body = self._assert_rejected_without_lead(self._valid_payload(company_type="supplier"))
        self.assertFalse(body["success"])
        self.assertIn("Invalid company_type", body["error"])

    def test_yes_no_fields_reject_non_allowlisted_values(self):
        yes_no_fields = [
            "is_five_storey_up",
            "is_ongoing",
            "is_aac_user",
            "is_open",
            "has_aac_needs",
            "has_design_specifications",
        ]

        for field_name in yes_no_fields:
            with self.subTest(field_name=field_name, value="yes"):
                with self._assert_lead_delta(1):
                    response = self._post_website_lead(self._valid_payload(**{field_name: "yes"}))
                self.assertEqual(response.status_code, 201)

            with self.subTest(field_name=field_name, value="no"):
                with self._assert_lead_delta(1):
                    response = self._post_website_lead(self._valid_payload(**{field_name: "no"}))
                self.assertEqual(response.status_code, 201)

            for invalid_value in ["true", "false", "1", "0", "y", "n", "maybe"]:
                with self.subTest(field_name=field_name, value=invalid_value):
                    body = self._assert_rejected_without_lead(
                        self._valid_payload(**{field_name: invalid_value})
                    )
                    self.assertFalse(body["success"])
                    self.assertIn("Invalid boolean value", body["error"])

    def test_optional_fields_may_be_empty(self):
        with self._assert_lead_delta(1):
            response = self._post_website_lead(
                self._valid_payload(
                    estimated_project_value="",
                    target_completion_date="",
                )
            )

        self.assertEqual(response.status_code, 201)
        body = self._json_response(response)
        lead = self.env["crm.lead"].browse(body["lead"]["id"])
        self.assertEqual(lead.estimated_project_value, 0.0)
        self.assertFalse(lead.target_completion_date)

    def test_date_validation(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        body = self._assert_rejected_without_lead(
            self._valid_payload(target_completion_date=yesterday)
        )
        self.assertFalse(body["success"])
        self.assertIn("Target Completion Date cannot be in the past", body["error"])

        for target_date in [today, tomorrow]:
            with self.subTest(target_date=target_date):
                with self._assert_lead_delta(1):
                    response = self._post_website_lead(
                        self._valid_payload(target_completion_date=target_date)
                    )
                self.assertEqual(response.status_code, 201)

    def test_project_value_validation(self):
        body = self._assert_rejected_without_lead(self._valid_payload(estimated_project_value="-1"))
        self.assertFalse(body["success"])
        self.assertIn("Estimated Project Value cannot be negative", body["error"])

        for value in ["", "0", "250000"]:
            with self.subTest(value=value):
                with self._assert_lead_delta(1):
                    response = self._post_website_lead(
                        self._valid_payload(estimated_project_value=value)
                    )
                self.assertEqual(response.status_code, 201)
