# ABC CRM Developer Documentation

ABC CRM is an Odoo 19 addon. The repository root is the `abc_crm` addon directory and is mounted directly into Odoo as `/mnt/extra-addons/abc_crm`.

The addon extends `crm.lead` with project qualification fields, lead rating, automatic disposition, sales-manager notifications, Philippine region data, and a bearer-authenticated lead intake endpoint.

## Project Layout

```text
.
├── .github/workflows/ci.yml
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
├── security/
│   ├── ir.model.access.csv
│   └── res_groups.xml
├── tests/
│   └── test_lead_controller.py
└── views/
    └── crm_lead_views.xml
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
pip install ruff
```

Run local checks:

```bash
ruff check .
ruff format --check .
python -m compileall .
```

Apply safe Ruff fixes and formatting:

```bash
ruff check . --fix
ruff format .
```

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

- `crm`
- `base`

The current manifest loads:

- `data/res.region.csv`
- `data/config_parameters.xml`
- `data/lost_reason_data.xml`
- `views/crm_lead_views.xml`
- `security/ir.model.access.csv`
- `security/res_groups.xml`

Current data/config notes:

- `data/res.region.csv` loads Luzon, Visayas, and Mindanao.
- `data/config_parameters.xml` defines `crm.passing_rate = 70`.
- `data/lost_reason_data.xml` defines `abc_crm.lost_reason_unqualified`.
- `security/res_groups.xml` defines `abc_crm.group_sales_manager`.
- `security/ir.model.access.csv` grants internal users read-only access to `res.region`.

## CRM Behavior

`models/crm_lead.py` adds these fields to `crm.lead`:

- Project fields: `project_name`, `project_location`, `project_type`, `estimated_project_value`, `target_completion_date`, `company_type`, `region_id`
- Qualification fields: `is_five_storey_up`, `is_ongoing`, `is_aac_user`, `is_open`, `has_aac_needs`, `has_design_specifications`
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

## CI

CI is defined in `.github/workflows/ci.yml`.

It runs on pushes and pull requests to `main` when Python, XML, CSV, manifest, `pyproject.toml`, or CI workflow files change.

Jobs:

- `lint`: runs Ruff, Ruff format check, Python compile, and non-blocking `pylint-odoo`.
- `test`: starts PostgreSQL `18`, mounts the repository as `/mnt/extra-addons/abc_crm:ro` inside `odoo:19.0`, installs `abc_crm`, and runs `--test-tags=/abc_crm`.
- `security`: runs Gitleaks on pushes to `main`.

## Current Notes

- The repository is the addon directory itself; do not document or mount it as `custom_addons/abc_crm`.
- `docker-compose.yaml` correctly mounts the repository to `/mnt/extra-addons/abc_crm`.
- The manifest now includes `data/lost_reason_data.xml`.
- `data/config_parameters.xml` defines `crm.passing_rate`, while `models/crm_lead.py` reads `abc_crm.auto_convert_threshold`; unless the latter is configured in Odoo, the code uses `70.0`.
- There is no checked-in `pyproject.toml`; Ruff currently uses defaults.
- Docker-based test verification was not completed in this session because Docker access approval was interrupted.
