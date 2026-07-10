# ABC CRM Developer Documentation

ABC CRM is an Odoo 19 addon. The repository root is the `abc_crm` addon directory and is mounted directly into Odoo as `/mnt/extra-addons/abc_crm`.

The addon extends `crm.lead` with project qualification fields, lead rating,
automatic disposition, sales-manager notifications, Philippine region data, a
bearer-authenticated JSON endpoint, and a public multi-step website form.

## Project Layout

```text
.
├── .github/workflows/ci.yml
├── .github/pull_request_template.md
├── .pre-commit-config.yaml
├── __init__.py
├── __manifest__.py
├── controllers/
│   └── lead_controller.py
├── data/
│   ├── config_parameters.xml
│   ├── lost_reason_data.xml
│   └── res.region.csv
├── docker-compose.yaml
├── models/
│   ├── crm_lead.py
│   ├── res_city.py
│   └── res_region.py
├── pyproject.toml
├── security/
│   ├── ir.model.access.csv
│   ├── ir_rule.xml
│   └── res_groups.xml
├── static/
│   ├── src/
│   │   ├── js/
│   │   │   └── abc_crm_multi_step_form.js
│   │   └── scss/
│   │       └── abc_crm_multi_step_form.scss
│   └── tests/
│       └── abc_crm_multi_step_form_security_tests.js
├── tests/
│   ├── test_crm_lead.py
│   ├── test_lead_controller.py
│   ├── test_website_lead_browser.py
│   └── test_website_lead_controller.py
└── views/
    ├── crm_lead_views.xml
    └── website_snippets.xml
```

## Local Stack

Local development uses Docker Compose:

- Odoo image: `odoo:19.0`
- PostgreSQL image: `postgres:18`
- Odoo service: `web`
- Database service: `db`
- Odoo port: `8069`
- Longpolling/gevent port: `8072`
- Addon mount: `./:/mnt/extra-addons/abc_crm`
- Odoo data volume: `abc-crm-web-data`
- PostgreSQL data volume: `abc-crm-db-data`

Start the stack:

```bash
docker compose up -d
```

Open Odoo:

```text
http://localhost:8069
```

Follow logs:

```bash
docker compose logs -f web
```

Stop the stack:

```bash
docker compose down
```

Remove local Odoo/PostgreSQL data:

```bash
docker compose down -v
```

## Addon Install and Upgrade

Install the addon into a local database:

```bash
docker compose run --rm web odoo \
  -d abc_crm_dev \
  --init abc_crm \
  --stop-after-init
```

Upgrade after Python, XML, CSV, security, or manifest changes:

```bash
docker compose run --rm web odoo \
  -d abc_crm_dev \
  --update abc_crm \
  --stop-after-init
```

Open an Odoo shell:

```bash
docker compose run --rm web odoo shell -d abc_crm_dev
```

## Developer Checks

Create a local virtual environment for tooling:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install ruff pre-commit pylint pylint-odoo
```

Ruff is configured in `pyproject.toml`:

- Python target: `py314`
- Line length: `88`
- Enabled lint families: `E`, `F`, `I`
- Format style: double quotes, spaces, automatic line endings

Run local checks:

```bash
ruff check .
ruff format --check .
python3 -m compileall .
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET

for path in sorted(Path(".").rglob("*.xml")):
    ET.parse(path)
    print(path)
PY
```

Apply safe Ruff fixes and formatting:

```bash
ruff check . --fix
ruff format .
```

Install pre-commit hooks:

```bash
pre-commit install
```

Run all pre-commit hooks manually:

```bash
pre-commit run --all-files
```

The pre-commit configuration checks whitespace, EOF, YAML, TOML, XML, large files, merge conflicts, case conflicts, line endings, debug statements, private keys, Ruff lint/format, Python compilation, and guards against committing `odoo.conf` or `.env` files. The `pylint-odoo` hook is configured for manual runs.

## Tests

Run all Odoo tests in a fresh database:

```bash
docker compose up -d db
docker compose exec db dropdb -U admin --if-exists abc_crm_test

docker compose run --rm web odoo \
  -d abc_crm_test \
  --init abc_crm \
  --test-enable \
  --test-tags=/abc_crm \
  --stop-after-init \
  --log-level=test
```

Run only the lead controller test class:

```bash
docker compose run --rm web odoo \
  -d abc_crm_test \
  --update abc_crm \
  --test-enable \
  --test-tags=/abc_crm:TestAbcCrmLeadController \
  --stop-after-init \
  --log-level=test
```

Run only the CRM lead model test class:

```bash
docker compose run --rm web odoo \
  -d abc_crm_test \
  --update abc_crm \
  --test-enable \
  --test-tags=/abc_crm:TestCrmLead \
  --stop-after-init \
  --log-level=test
```

Run only the website lead controller test class:

```bash
docker compose run --rm web odoo \
  -d abc_crm_test \
  --update abc_crm \
  --test-enable \
  --test-tags=/abc_crm:TestAbcCrmWebsiteLeadController \
  --stop-after-init \
  --log-level=test
```

Run only the website lead browser security test class:

```bash
docker compose run --rm web odoo \
  -d abc_crm_test \
  --update abc_crm \
  --test-enable \
  --test-tags=/abc_crm:TestAbcCrmWebsiteLeadBrowser \
  --stop-after-init \
  --log-level=test
```

`tests/test_crm_lead.py` uses `TransactionCase` and verifies:

- Rating calculation from the six qualification fields.
- Qualified lead conversion to an unassigned opportunity.
- Unqualified lead lost disposition with `abc_crm.lost_reason_unqualified`.
- `project_location` computation from address, region, zip, and country.
- Model constraints for non-negative project value, non-past target dates, and
  valid phone numbers when a phone is provided.

`tests/test_lead_controller.py` uses `HttpCase`, generates an API key for `base.user_admin`, and verifies:

- Successful `POST /abc_crm/lead` lead creation.
- Text trimming for payload values.
- `function` mapping to the lead position/job title field.
- `message` mapping to lead `name` and HTML `description`.
- `project_location` mapping through `street` and the computed `project_location`.
- Float, future date, Philippine phone, and strict `yes`/`no` parsing.
- UTM source, medium, and campaign creation/defaulting/reuse.
- Rating value `65` for the sample valid payload.
- `400` responses for missing fields, unknown fields, invalid `company_type`, invalid booleans, invalid project value, and invalid date format.

`tests/test_website_lead_controller.py` uses `HttpCase` and verifies:

- Successful public form submission with Odoo CSRF protection.
- Rejection of missing or invalid CSRF tokens without lead creation.
- Server-side validation for email, phone, message length, company type, booleans, project value, date, unknown fields, and text length limits.
- Honeypot submissions returning neutral success without creating leads.
- Website UTM defaults: `Website` source and `Website Form` medium.
- Qualification values limited to `yes` and `no`.

`tests/test_website_lead_browser.py` runs browser security checks from `static/tests/abc_crm_multi_step_form_security_tests.js` and verifies:

- Current, stale, and missing CSRF token handling.
- Duplicate submission protection and request timeout recovery.
- Cross-origin form action rejection.
- Safe handling of invalid JSON, HTML error responses, and XSS-like payloads.

## Manifest Data

The addon depends on:

- `base`
- `spreadsheet_dashboard`
- `board`
- `sale_crm`
- `partnership`
- `crm`
- `sales_team`
- `website`
- `phone_validation`

The manifest declares version `1.0.0`, license `OEEL-1`, and installs the addon
as an application.

The current manifest loads:

- `data/res.region.csv`
- `data/config_parameters.xml`
- `views/crm_lead_views.xml`
- `views/website_snippets.xml`
- `security/res_groups.xml`
- `security/ir.model.access.csv`
- `security/ir_rule.xml`
- `data/lost_reason_data.xml`

Frontend assets are loaded through `web.assets_frontend`:

- `static/src/js/abc_crm_multi_step_form.js`
- `static/src/scss/abc_crm_multi_step_form.scss`

Frontend test assets are loaded through `web.assets_tests`:

- `static/tests/abc_crm_multi_step_form_security_tests.js`

Current data/config notes:

- `data/res.region.csv` loads Luzon, Visayas, and Mindanao.
- `data/config_parameters.xml` defines `abc_crm.passing_rate = 70`.
- `data/lost_reason_data.xml` defines `abc_crm.lost_reason_unqualified` on Odoo 19 model `crm.lost.reason`.
- `security/res_groups.xml` defines Marketing, Sales Manager, General Manager,
  Sales Team Leader, and Sales Representative roles and adjusts CRM
  configuration, team, board, and spreadsheet dashboard menu visibility.
- `security/ir.model.access.csv` gives internal users read access to regions and
  adds role-specific access for sales teams, sales team members, and sales
  orders. CRM lead access continues to come from the standard sales groups
  implied by the custom roles.
- `security/ir_rule.xml` applies own-lead versus all-lead rules and adds
  team/team-member scopes for Sales Representatives and Sales Team Leaders.

## CRM Behavior

`models/crm_lead.py` adds these fields to `crm.lead`:

- Project fields: `project_name`, `project_location`, `project_type`, `estimated_project_value`, `target_completion_date`, `company_type`, `region_id`
- Qualification fields: `is_five_storey_up`, `is_ongoing`, `is_aac_user`, `is_open`, `has_aac_needs`, `has_design_specifications`
- Assignment helper fields: `allowed_user_ids`, `is_restricted`
- Computed rating field: `rating`

Rating rules:

| Field | Points |
| --- | ---: |
| `is_five_storey_up` | 15 |
| `is_ongoing` | 25 |
| `has_aac_needs` | 15 |
| `is_aac_user` | 10 |
| `is_open` | 10 |
| `has_design_specifications` | 25 |

When qualification fields are provided on create or changed on write:

- Leads with `rating >= abc_crm.passing_rate` are converted to opportunities.
- Leads with `rating < abc_crm.passing_rate` are marked lost.
- If `abc_crm.passing_rate` is not configured, the code default is `70.0`.

Converted opportunities are left unassigned by clearing `user_id` and `team_id`. If `abc_crm.group_sales_manager` has users, their partners are subscribed to the opportunity and receive the message `New opportunity requires assignment.`

Team assignment behavior:

- `allowed_user_ids` limits selectable assignees to members of the selected sales team.
- `is_restricted` makes team and user assignment read-only for Marketing and Sales Representative users.
- The CRM form replaces `state_id` with `region_id`, adds Qualification Sheet and Client Information Sheet tabs, and hides the standard Misc page.

Role and menu behavior:

- Marketing, Sales Manager, and General Manager imply Odoo's standard
  `sales_team.group_sale_salesman_all_leads` group.
- Sales Team Leader and Sales Representative imply Odoo's standard
  `sales_team.group_sale_salesman` group.
- Sales Managers can create and update sales teams and team members; Sales Team
  Leaders can do so within their record-rule scope. Neither role receives
  delete access from this addon's custom ACLs.
- Sales Representatives receive read-only sales-team access and create/update
  access to sales orders, without delete access from this addon.
- `abc_crm.group_crm_all` and `abc_crm.group_crm_own` are declared but are not
  currently implied by the five business roles.
- The board and spreadsheet dashboard menus are enabled for all five business
  roles. CRM configuration and team configuration menus are enabled for the
  General Manager, Sales Manager, and Sales Team Leader roles.

## Lead Intake API

Endpoint:

```text
POST /abc_crm/lead
```

Headers:

```text
Authorization: bearer <odoo-api-key>
Content-Type: application/json
```

Example payload:

```json
{
  "contact_name": "Jane Buyer",
  "partner_name": "ABC Construction",
  "function": "Purchasing Manager",
  "email_from": "jane@example.com",
  "phone": "+639170000000",
  "message": "Website inquiry",
  "project_name": "Warehouse Extension",
  "project_location": "Cebu City",
  "project_type": "Commercial",
  "estimated_project_value": "1250000.50",
  "target_completion_date": "2099-12-31",
  "company_type": "contractor",
  "is_five_storey_up": "yes",
  "is_ongoing": "no",
  "is_aac_user": "yes",
  "is_open": "no",
  "has_aac_needs": "yes",
  "has_design_specifications": "yes",
  "utm_source": "Website",
  "utm_medium": "Form",
  "utm_campaign": "June Launch"
}
```

Required text fields:

- `contact_name`
- `partner_name`
- `function`
- `email_from`
- `phone`
- `message`
- `project_name`
- `project_location`
- `project_type`
- `company_type`
- `utm_source`
- `utm_medium`

Required boolean fields:

- `is_five_storey_up`
- `is_ongoing`
- `is_aac_user`
- `is_open`
- `has_aac_needs`
- `has_design_specifications`

Optional fields:

- `estimated_project_value`
- `target_completion_date`
- `utm_campaign`

Accepted `company_type` values:

- `contractor`
- `developer`
- `homeowner`
- `architect`
- `trader`

Each qualification field accepts exactly one of these JSON string values:

- `"yes"`
- `"no"`

JSON booleans, integers, and aliases such as `"true"`, `"false"`, `"1"`,
`"0"`, `"y"`, and `"n"` are rejected.

Unknown payload fields are rejected.

## Website Form

The addon provides a website snippet named `ABC CRM Multi-Step Form`.

The snippet is registered from `views/website_snippets.xml` and uses frontend assets from:

- `static/src/js/abc_crm_multi_step_form.js`
- `static/src/scss/abc_crm_multi_step_form.scss`

Website form endpoint:

```text
POST /abc_crm/website/lead
```

The website route is public, uses Odoo CSRF protection, and submits form-encoded data. It accepts the same lead field names as `POST /abc_crm/lead`, plus these form-only fields:

- `csrf_token`: Odoo CSRF token.
- `abc_crm_hp`: honeypot field; non-empty values return success without creating a lead.

The website route sets these UTM defaults for public form submissions:

- `utm_source = Website`
- `utm_medium = Website Form`

Both lead intake routes accept only `yes` and `no` for qualification values,
matching the radio values in the snippet.

The snippet also sends this campaign default unless the form payload is changed:

- `utm_campaign = Website Inquiry`

The JavaScript widget handles step navigation, required-field validation, review summary rendering, AJAX submission, and success/error alerts.

## CI

CI is defined in `.github/workflows/ci.yml`.

It runs manually through `workflow_dispatch`, and on pushes and pull requests to
`main` when Python, XML, CSV, `static/src` frontend asset, manifest, local
tooling, Docker Compose, or workflow files change. A change only under
`static/tests` does not currently match the automatic path filters.

Jobs:

- `lint`: runs Ruff, Ruff format check, Python compile, XML syntax validation, and non-blocking `pylint-odoo`.
- `test`: starts PostgreSQL `18`, mounts the repository as `/mnt/extra-addons/abc_crm:ro` inside `odoo:19.0`, installs `abc_crm`, and runs `--test-tags=/abc_crm`.
- `security`: runs Gitleaks on pushes to `main`.

CI timeout limits:

- `lint`: 10 minutes
- `test`: 25 minutes
- `security`: 10 minutes

There is no separate Node or SCSS build job. The repository does not include a `package.json`, and Odoo compiles the website assets in the Odoo runtime.

## Current Notes

- The repository is the addon directory itself; do not document or mount it as `custom_addons/abc_crm`.
- `docker-compose.yaml` correctly mounts the repository to `/mnt/extra-addons/abc_crm`.
- The manifest includes `website`, `phone_validation`, `sale_crm`, `partnership`, `sales_team`, `board`, `spreadsheet_dashboard`, `views/website_snippets.xml`, `security/ir_rule.xml`, frontend assets under `web.assets_frontend`, and browser test assets under `web.assets_tests`.
- `data/config_parameters.xml` defines `abc_crm.passing_rate`, and `models/crm_lead.py` reads the same key with a code default of `70.0`.
- Both `/abc_crm/lead` and `/abc_crm/website/lead` require `yes`/`no` strings
  for all six qualification fields.
- `pyproject.toml` is checked in and configures Ruff for Python 3.14.
- `.pre-commit-config.yaml` is checked in and should be used for local quality gates.
- `.github/pull_request_template.md` is checked in and documents expected PR context, Odoo impact, testing, screenshots, migration notes, and review checklist items.
- Docker-based Odoo tests are the expected integration verification path for this addon.
