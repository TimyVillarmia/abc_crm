# ABC CRM Developer Documentation

ABC CRM is an Odoo 19 addon. The repository root is the `abc_crm` addon directory and is mounted directly into Odoo as `/mnt/extra-addons/abc_crm`.

The addon extends `crm.lead` with project qualification fields, lead rating, automatic disposition, sales-manager notifications, Philippine region data, and a bearer-authenticated lead intake endpoint.

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
│   └── src/
│       ├── js/
│       │   └── abc_crm_multi_step_form.js
│       └── scss/
│           └── abc_crm_multi_step_form.scss
├── tests/
│   └── test_lead_controller.py
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

`tests/test_lead_controller.py` uses `HttpCase`, generates an API key for `base.user_admin`, and verifies:

- Successful `POST /abc_crm/lead` lead creation.
- Text trimming for payload values.
- `message` mapping to lead `name` and HTML `description`.
- `project_location` mapping through `street` and the computed `project_location`.
- Float, date, and boolean parsing.
- UTM source, medium, and campaign creation/reuse.
- Rating value `65` for the sample valid payload.
- `400` responses for missing fields, unknown fields, invalid `company_type`, invalid booleans, invalid project value, and invalid date format.

## Manifest Data

The addon depends on:

- `base`
- `spreadsheet_dashboard`
- `board`
- `crm`
- `sales_team`
- `website`

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

Current data/config notes:

- `data/res.region.csv` loads Luzon, Visayas, and Mindanao.
- `data/config_parameters.xml` defines `crm.passing_rate = 70`.
- `data/lost_reason_data.xml` defines `abc_crm.lost_reason_unqualified` on Odoo 19 model `crm.lost.reason`.
- `security/res_groups.xml` defines CRM role groups and adjusts CRM, board, dashboard, customer, team, and configuration menu visibility.
- `security/ir.model.access.csv` grants role-based access to regions, CRM leads, CRM tags, sales teams, sales team members, and lead scoring frequency.
- `security/ir_rule.xml` restricts representative and team-leader access to their own leads, teams, or team members.

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

- Leads with `rating >= abc_crm.auto_convert_threshold` are converted to opportunities.
- Leads with `rating < abc_crm.auto_convert_threshold` are marked lost.
- If `abc_crm.auto_convert_threshold` is not configured, the code default is `70.0`.

Converted opportunities are left unassigned by clearing `user_id` and `team_id`. If `abc_crm.group_sales_manager` has users, their partners are subscribed to the opportunity and receive the message `New opportunity requires assignment.`

Team assignment behavior:

- `allowed_user_ids` limits selectable assignees to members of the selected sales team.
- `is_restricted` makes team and user assignment read-only for Marketing and General Manager users.
- The CRM form replaces `state_id` with `region_id`, adds Qualification Sheet and Client Information Sheet tabs, and hides the standard Misc page.

Role and menu behavior:

- `abc_crm.group_crm_own` is the shared own-document restriction group.
- `abc_crm.group_sales_representative` sees own CRM documents and own team membership records.
- `abc_crm.group_sales_team_leader` sees own team leads, teams, and team members.
- `abc_crm.group_sales_manager` has broader sales manager access.
- `abc_crm.group_marketing` has all-leads access and can create/update CRM leads, but assignment fields are restricted in the CRM form.
- `abc_crm.group_general_manager` has read-oriented CRM visibility plus board and spreadsheet dashboard menus.

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
  "email_from": "jane@example.com",
  "phone": "+63 900 000 0000",
  "message": "Website inquiry",
  "project_name": "Warehouse Extension",
  "project_location": "Cebu City",
  "project_type": "Commercial",
  "estimated_project_value": "1250000.50",
  "target_completion_date": "2026-12-31",
  "company_type": "contractor",
  "is_five_storey_up": true,
  "is_ongoing": false,
  "is_aac_user": true,
  "is_open": false,
  "has_aac_needs": true,
  "has_design_specifications": true,
  "utm_source": "Website",
  "utm_medium": "Form",
  "utm_campaign": "June Launch"
}
```

Required text fields:

- `contact_name`
- `partner_name`
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

Accepted boolean values:

- JSON booleans: `true`, `false`
- Integers: `1`, `0`
- Strings: `true`, `false`, `1`, `0`, `yes`, `no`, `y`, `n`

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

The website route is public, uses Odoo CSRF protection, and submits form-encoded data. It accepts the same lead field names and validation rules as `POST /abc_crm/lead`, plus these form-only fields:

- `csrf_token`: Odoo CSRF token.
- `abc_crm_hp`: honeypot field; non-empty values return success without creating a lead.

The snippet sets these hidden UTM defaults:

- `utm_source = Website`
- `utm_medium = Website Form`
- `utm_campaign = Website Inquiry`

The JavaScript widget handles step navigation, required-field validation, review summary rendering, AJAX submission, and success/error alerts.

## CI

CI is defined in `.github/workflows/ci.yml`.

It runs manually through `workflow_dispatch`, and on pushes and pull requests to `main` when Python, XML, CSV, frontend asset, manifest, local tooling, Docker Compose, or workflow files change.

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
- The manifest includes `website`, `sales_team`, `board`, `spreadsheet_dashboard`, `views/website_snippets.xml`, `security/ir_rule.xml`, and frontend assets under `web.assets_frontend`.
- `data/config_parameters.xml` defines `crm.passing_rate`, while `models/crm_lead.py` reads `abc_crm.auto_convert_threshold`; unless the latter is configured in Odoo, the code uses `70.0`.
- `pyproject.toml` is checked in and configures Ruff for Python 3.14.
- `.pre-commit-config.yaml` is checked in and should be used for local quality gates.
- `.github/pull_request_template.md` is checked in and documents expected PR context, Odoo impact, testing, screenshots, migration notes, and review checklist items.
- Docker-based Odoo tests are the expected integration verification path for this addon.
