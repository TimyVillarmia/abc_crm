# custom_addons/abc_crm/controllers/lead_controller.py

import logging

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.tools import single_email_re

_logger = logging.getLogger(__name__)


class AbcCrmLeadController(http.Controller):
    allowed_fields = {
        # Contact fields
        "contact_name",
        "partner_name",
        "email_from",
        "phone",
        "function",
        # Main inquiry field
        "message",
        # Project fields
        "project_name",
        "project_location",
        "project_type",
        "estimated_project_value",
        "target_completion_date",
        "company_type",
        # Qualification criteria
        "is_five_storey_up",
        "is_ongoing",
        "is_aac_user",
        "is_open",
        "has_aac_needs",
        "has_design_specifications",
        # UTM fields
        "utm_source",
        "utm_medium",
        "utm_campaign",
    }

    required_text_fields = [
        "contact_name",
        "partner_name",
        "email_from",
        "phone",
        "message",
        "project_name",
        "project_location",
        "project_type",
        "company_type",
        "function",
        "utm_source",
        "utm_medium",
    ]

    required_boolean_fields = [
        "is_five_storey_up",
        "is_ongoing",
        "is_aac_user",
        "is_open",
        "has_aac_needs",
        "has_design_specifications",
    ]

    @http.route(
        "/abc_crm/lead",
        type="http",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def create_lead(self, **kwargs):
        payload = request.httprequest.get_json(silent=True)

        if not isinstance(payload, dict):
            return self._json_error("Request body must be a JSON object.", 400)

        try:
            lead = self._create_lead_from_payload(payload, sudo=False)
        except AccessError:
            return self._json_error(
                "You do not have permission to create CRM leads or UTM records.",
                403,
            )
        except (ValidationError, UserError) as error:
            return self._json_error(str(error), 400)
        except Exception:
            _logger.exception("Failed to create CRM lead from /abc_crm/lead")
            return self._json_error("Unexpected server error.", 500)

        return request.make_json_response(
            {
                "success": True,
                "lead": self._serialize_lead(lead),
            },
            status=201,
        )

    @http.route(
        "/abc_crm/website/lead",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def create_website_lead(self, **kwargs):
        extra_fields = {"csrf_token", "abc_crm_hp"}
        unknown_fields = sorted(set(kwargs.keys()) - self.allowed_fields - extra_fields)
        if unknown_fields:
            return self._json_error(
                "Unknown field(s): %s" % ", ".join(unknown_fields),
                400,
            )

        if self._clean_string(kwargs.get("abc_crm_hp")):
            return request.make_json_response(
                {
                    "success": True,
                    "lead": False,
                },
                status=200,
            )

        payload = {
            field_name: kwargs.get(field_name)
            for field_name in self.allowed_fields
            if field_name in kwargs
        }

        payload.update(
            {
                "utm_source": "Website",
                "utm_medium": "Website Form",
            }
        )

        try:
            lead = self._create_lead_from_payload(payload, sudo=True)
        except (ValidationError, UserError) as error:
            return self._json_error(str(error), 400)
        except Exception:
            _logger.exception("Failed to create CRM lead from /abc_crm/website/lead")
            return self._json_error("Unexpected server error.", 500)

        return request.make_json_response(
            {
                "success": True,
                "lead": self._serialize_lead(lead),
            },
            status=201,
        )

    def _create_lead_from_payload(self, payload, sudo=False):
        self._validate_payload(payload)
        self._validate_company_type(payload.get("company_type"))

        source = self._get_or_create_utm(
            "utm.source",
            payload.get("utm_source"),
            sudo=sudo,
        )

        medium = self._get_or_create_utm(
            "utm.medium",
            payload.get("utm_medium"),
            sudo=sudo,
        )

        campaign = False
        if self._clean_string(payload.get("utm_campaign")):
            campaign = self._get_or_create_utm(
                "utm.campaign",
                payload.get("utm_campaign"),
                sudo=sudo,
            )

        lead_values = {
            "type": "lead",
            # User requested:
            # message becomes the lead name.
            "name": self._clean_string(payload.get("message")),
            # Keep the message in description too so the full inquiry is visible.
            "description": self._clean_string(payload.get("message")),
            # Standard CRM/contact fields
            "contact_name": self._clean_string(payload.get("contact_name")),
            "partner_name": self._clean_string(payload.get("partner_name")),
            "email_from": self._clean_string(payload.get("email_from")),
            "phone": self._clean_string(payload.get("phone")),
            "function": self._clean_string(payload.get("function")),
            # Project fields
            "project_name": self._clean_string(payload.get("project_name")),
            "project_type": self._clean_string(payload.get("project_type")),
            "estimated_project_value": self._parse_float(
                payload.get("estimated_project_value")
            ),
            "target_completion_date": self._parse_date(
                payload.get("target_completion_date")
            ),
            "company_type": self._clean_string(payload.get("company_type")),
            "street": self._clean_string(payload.get("project_location")),
            "is_five_storey_up": self._parse_bool(payload.get("is_five_storey_up")),
            "is_ongoing": self._parse_bool(payload.get("is_ongoing")),
            "is_aac_user": self._parse_bool(payload.get("is_aac_user")),
            "is_open": self._parse_bool(payload.get("is_open")),
            "has_aac_needs": self._parse_bool(payload.get("has_aac_needs")),
            "has_design_specifications": self._parse_bool(
                payload.get("has_design_specifications")
            ),
            # UTM relational fields
            "source_id": source.id,
            "medium_id": medium.id,
        }

        if campaign:
            lead_values["campaign_id"] = campaign.id

        lead_model = request.env["crm.lead"]
        if sudo:
            lead_model = lead_model.sudo()

        return lead_model.create(lead_values)

    def _validate_payload(self, payload):
        unknown_fields = sorted(set(payload.keys()) - self.allowed_fields)

        if unknown_fields:
            raise ValidationError("Unknown field(s): %s" % ", ".join(unknown_fields))

        missing_text_fields = [
            field_name
            for field_name in self.required_text_fields
            if not self._clean_string(payload.get(field_name))
        ]

        missing_boolean_fields = [
            field_name
            for field_name in self.required_boolean_fields
            if field_name not in payload
        ]

        missing_fields = missing_text_fields + missing_boolean_fields

        if missing_fields:
            raise ValidationError(
                "Missing required field(s): %s" % ", ".join(missing_fields)
            )

        self._validate_email(payload.get("email_from"))
        self._validate_message(payload.get("message"))

    def _validate_email(self, email):
        if not self._clean_string(email):
            raise ValidationError(_("Email is required."))

        if not single_email_re.fullmatch(email):
            raise ValidationError(_("Please enter a valid email address."))

    def _get_or_create_utm(self, model_name, name, sudo=False):
        clean_name = self._clean_string(name)

        model = request.env[model_name]
        if sudo:
            model = model.sudo()

        record = model.search(
            [("name", "=", clean_name)],
            limit=1,
        )

        if record:
            return record

        return model.create(
            {
                "name": clean_name,
            }
        )

    def _validate_company_type(self, value):
        company_type = self._clean_string(value)

        allowed_company_types = {
            "contractor",
            "developer",
            "homeowner",
            "architect",
            "trader",
        }

        if company_type not in allowed_company_types:
            raise ValidationError(
                "Invalid company_type. Allowed values: %s"
                % ", ".join(sorted(allowed_company_types))
            )

    def _parse_bool(self, value):
        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            if value == 1:
                return True

            if value == 0:
                return False

            raise ValidationError("Invalid boolean value: %s" % value)

        clean_value = self._clean_string(value).lower()

        if clean_value in {"true", "1", "yes", "y"}:
            return True

        if clean_value in {"false", "0", "no", "n"}:
            return False

        raise ValidationError("Invalid boolean value: %s" % value)

    def _validate_message(self, value):
        message = self._clean_string(value)

        if len(message) < 10:
            raise ValidationError("Inquiry must be at least 10 characters.")

        if len(message) > 1000:
            raise ValidationError("Inquiry cannot exceed 1000 characters.")

    def _parse_float(self, value):
        clean_value = self._clean_string(value)

        if not clean_value:
            return 0.0

        try:
            return float(clean_value)
        except ValueError as error:
            raise ValidationError(
                "Invalid estimated_project_value: %s" % value
            ) from error

    def _parse_date(self, value):
        clean_value = self._clean_string(value)

        if not clean_value:
            return False

        try:
            return fields.Date.to_date(clean_value)
        except Exception as error:
            raise ValidationError(
                "Invalid target_completion_date. Use YYYY-MM-DD."
            ) from error

    def _clean_string(self, value):
        return str(value or "").strip()

    def _serialize_lead(self, lead):
        return {
            "id": lead.id,
            "name": lead.name,
            "type": lead.type,
            "active": lead.active,
            "contact_name": lead.contact_name,
            "partner_name": lead.partner_name,
            "email_from": lead.email_from,
            "phone": lead.phone,
            "project_name": lead.project_name,
            "project_location": lead.project_location,
            "project_type": lead.project_type,
            "function": lead.function,
            "estimated_project_value": lead.estimated_project_value,
            "target_completion_date": (
                lead.target_completion_date.isoformat()
                if lead.target_completion_date
                else False
            ),
            "company_type": lead.company_type,
            "rating": lead.rating,
            "utm_source": lead.source_id.name or False,
            "utm_medium": lead.medium_id.name or False,
            "utm_campaign": lead.campaign_id.name or False,
        }

    def _json_error(self, message, status):
        return request.make_json_response(
            {
                "success": False,
                "error": message,
            },
            status=status,
        )
