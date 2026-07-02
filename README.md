# ABC CRM Developer Documentation

ABC CRM is an Odoo 19 addon. The addon currently lives at the repository root, so the root directory itself is the `abc_crm` module.

It extends `crm.lead` with project qualification fields, point-based lead rating, automatic lead disposition, sales-manager notification behavior, Philippine region data, and a bearer-authenticated lead intake endpoint.

## Contents

- [Project Layout](#project-layout)
- [Runtime Stack](#runtime-stack)
- [Local Setup](#local-setup)
- [Addon Installation and Upgrade](#addon-installation-and-upgrade)
- [Developer Tooling](#developer-tooling)
- [Testing](#testing)
- [Lead Controller Tests](#lead-controller-tests)
- [Module Behavior](#module-behavior)
- [Lead Intake API](#lead-intake-api)
- [CI Workflow](#ci-workflow)
- [Configuration Notes](#configuration-notes)
- [Known Developer Notes](#known-developer-notes)

## Project Layout

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── lead_controller.py
├── data/
│   ├── config_parameters.xml
│   ├── lost_reason_data.xml
│   └── res.region.csv
├── docker-compose.yaml
├── models/
│   ├── __init__.py
│   ├── crm_lead.py
│   ├── res_city.py
│   └── res_region.py
├── security/
│   ├── ir.model.access.csv
│   └── res_groups.xml
├── tests/
│   ├── __init__.py
│   └── test_lead_controller.py
├── views/
│   └── crm_lead_views.xml
├── skills-lock.json
└── README.md
```

Important files:

- `__manifest__.py`: addon metadata, dependencies, and loaded data files.
- `models/crm_lead.py`: CRM lead fields, rating logic, auto-conversion, lost-lead behavior, and sales-manager notifications.
- `controllers/lead_controller.py`: bearer-authenticated HTTP lead intake endpoint.
- `tests/test_lead_controller.py`: Odoo `HttpCase` tests for the lead intake endpoint.
- `views/crm_lead_views.xml`: CRM form inheritance for client and qualification pages.
- `security/res_groups.xml`: custom `abc_crm.group_sales_manager` group.
- `security/ir.model.access.csv`: read access for `res.region`.

## Runtime Stack

Local development uses:

- Odoo `19.0`
- PostgreSQL `18`
- Docker and Docker Compose
- Python local virtual environment for lint/format tools
- Ruff for Python linting and formatting

Docker Compose services:

- `web`: Odoo service using `odoo:19.0`
- `db`: PostgreSQL service using `postgres:18`

Exposed ports:

- `8069`: Odoo HTTP
- `8072`: Odoo longpolling/gevent

Persistent Docker volumes:

- `abc-crm-web-data`: Odoo data and filestore
- `abc-crm-db-data`: PostgreSQL data

## Local Setup

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

Stop the stack and remove persisted data:

```bash
docker compose down -v
```

Use `docker compose down -v` only when you intentionally want to delete the local database and Odoo filestore.

The local `web` service runs with:

```text
--dev=reload,qweb,xml
```

Python reload helps during development, but database-level module upgrades are still required for manifest, data, view, field, and security changes.

## Addon Installation and Upgrade

The addon technical name is `abc_crm`; the display name is `ABC CRM`.

Install into a local database:

```bash
docker compose run --rm web odoo \
  -d abc_crm_dev \
  --init abc_crm \
  --stop-after-init
```

Upgrade after Python, XML, data, security, or manifest changes:

```bash
docker compose run --rm web odoo \
  -d abc_crm_dev \
  --update abc_crm \
  --stop-after-init
```

Open an Odoo shell:

```bash
docker compose run --rm web odoo shell \
  -d abc_crm_dev
```

## Developer Tooling

Create and activate a local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install ruff
```

Run Ruff linting:

```bash
ruff check .
```

Apply safe Ruff fixes:

```bash
ruff check . --fix
```

Format Python files:

```bash
ruff format .
```

Check formatting without writing changes:

```bash
ruff format --check .
```

Check Python syntax:

```bash
python -m compileall .
```

Recommended pre-commit check:

```bash
ruff check . --fix
ruff format .
ruff check .
ruff format --check .
python -m compileall .
```

## Testing

Start PostgreSQL before running Odoo tests:

```bash
docker compose up -d db
```

Run all `abc_crm` Odoo tests in a fresh test database:

```bash
docker compose exec db dropdb -U admin --if-exists abc_crm_test

docker compose run --rm web odoo \
  -d abc_crm_test \
  --init abc_crm \
  --test-enable \
  --test-tags=/abc_crm \
  --stop-after-init \
  --log-level=test
```

Run only the lead controller test class after the module is installed:

```bash
docker compose run --rm web odoo \
  -d abc_crm_test \
  --update abc_crm \
  --test-enable \
  --test-tags=/abc_crm:TestAbcCrmLeadController \
  --stop-after-init \
  --log-level=test
```

If `abc_crm_test` does not already have the addon installed, use `--init abc_crm` instead of `--update abc_crm`.

## Lead Controller Tests

`tests/test_lead_controller.py` contains one `HttpCase` class:

```text
TestAbcCrmLeadController
```

The test class is tagged:

```text
post_install, -at_install
```

During setup, it generates an Odoo API key for `base.user_admin` and posts JSON payloads to:

```text
POST /abc_crm/lead
```

The tests currently verify:

- Successful lead creation from JSON with whitespace-trimmed text fields.
- `message` becomes both the lead name and HTML description.
- `project_location` is stored on `crm.lead.street` and returned through the computed `project_location`.
- `estimated_project_value` is parsed to a float.
- `target_completion_date` is parsed from `YYYY-MM-DD`.
- Boolean inputs are accepted as strings, integers, and JSON booleans.
- UTM source, medium, and campaign records are created or reused by name.
- The sample valid payload produces rating `65`.
- Missing required text and boolean fields return `400`.
- Unknown fields return `400`.
- Invalid `company_type` returns `400`.
- Invalid boolean values return `400`.
- Invalid `estimated_project_value` returns `400`.
- Invalid `target_completion_date` returns `400`.

## Module Behavior

### Manifest

The addon depends on:

- `crm`
- `base`

The current manifest loads:

- `data/res.region.csv`
- `data/config_parameters.xml`
- `views/crm_lead_views.xml`
- `security/ir.model.access.csv`
- `security/res_groups.xml`

### CRM Lead Extensions

`crm.lead` is extended with:

- Project fields: `project_name`, `project_location`, `project_type`, `estimated_project_value`, `target_completion_date`, `company_type`, `region_id`
- Qualification booleans: `is_five_storey_up`, `is_ongoing`, `is_aac_user`, `is_open`, `has_aac_needs`, `has_design_specifications`
- Computed rating: `rating`

`project_location` is a stored computed field built from `street`, `street2`, `city`, `region_id`, `zip`, and `country_id`.

### Rating Rules

| Field | Points |
| --- | ---: |
| `is_five_storey_up` | 15 |
| `is_ongoing` | 25 |
| `has_aac_needs` | 15 |
| `is_aac_user` | 10 |
| `is_open` | 10 |
| `has_design_specifications` | 25 |

Maximum score: `100`.

### Automatic Lead Disposition

When qualifying fields are provided on create or changed on write:

- Leads with `rating >= abc_crm.auto_convert_threshold` are converted to opportunities.
- Leads with `rating < abc_crm.auto_convert_threshold` are marked lost.
- If no `abc_crm.auto_convert_threshold` parameter exists, the code default is `70.0`.

Converted opportunities are intentionally left unassigned:

- `user_id = False`
- `team_id = False`

After conversion, the addon looks up `abc_crm.group_sales_manager`. If users are assigned to that group, their partners are subscribed to the opportunity and receive a notification message:

```text
New opportunity requires assignment.
```

When a lead is marked lost, the code attempts to use XML ID `abc_crm.lost_reason_unqualified` as the default lost reason.

### Region Data

The addon defines a custom `res.region` model and loads three Philippine regions:

- Luzon
- Visayas
- Mindanao

Internal users have read-only access to `res.region`.

## Lead Intake API

Endpoint:

```text
POST /abc_crm/lead
```

Authentication:

```text
Authorization: bearer <odoo-api-key>
Content-Type: application/json
```

The authenticated user must be allowed to create:

- `crm.lead`
- `utm.source`
- `utm.medium`
- `utm.campaign`, when `utm_campaign` is provided

### Request Body

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

`target_completion_date` must use `YYYY-MM-DD`.

Unknown request fields are rejected with `400 Bad Request`.

### Lead Mapping

The controller maps payload fields as follows:

| Payload field | Odoo field |
| --- | --- |
| `message` | `crm.lead.name` and `crm.lead.description` |
| `project_location` | `crm.lead.street` |
| `utm_source` | `crm.lead.source_id` |
| `utm_medium` | `crm.lead.medium_id` |
| `utm_campaign` | `crm.lead.campaign_id` |

UTM records are reused by exact name when found, otherwise they are created.

### Success Response

Status:

```text
201 Created
```

Example:

```json
{
  "success": true,
  "lead": {
    "id": 1,
    "name": "Website inquiry",
    "type": "lead",
    "active": true,
    "contact_name": "Jane Buyer",
    "partner_name": "ABC Construction",
    "email_from": "jane@example.com",
    "phone": "+63 900 000 0000",
    "project_name": "Warehouse Extension",
    "project_location": "Cebu City",
    "project_type": "Commercial",
    "estimated_project_value": 1250000.5,
    "target_completion_date": "2026-12-31",
    "company_type": "contractor",
    "rating": 65,
    "utm_source": "Website",
    "utm_medium": "Form",
    "utm_campaign": "June Launch"
  }
}
```

Error response shape:

```json
{
  "success": false,
  "error": "Error message"
}
```

## CI Workflow

CI is defined in:

```text
.github/workflows/ci.yml
```

The workflow runs on pushes and pull requests to `main` when Python, XML, CSV, manifest, `pyproject.toml`, or workflow files change.

Jobs:

- `lint`: installs Ruff, Pylint, and `pylint-odoo`; runs `ruff check .`, `ruff format --check .`, `python -m compileall .`, and non-blocking Odoo lint.
- `test`: starts PostgreSQL `18`, mounts the repository as `/mnt/extra-addons/abc_crm:ro` inside `odoo:19.0`, installs `abc_crm`, and runs Odoo tests.
- `security`: runs only on pushes to `main`; performs Gitleaks secret scanning.

CI uses Python `3.14` for tooling.

## Configuration Notes

The local Docker Compose file does not mount a custom `odoo.conf`. It relies on Odoo image defaults plus these environment variables:

- `HOST = db`
- `USER = admin`
- `PASSWORD = admin`

Do not commit local runtime data, database dumps, filestore contents, API keys, or secrets. The `.gitignore` excludes common Python, Docker, Odoo, IDE, cache, and secret artifacts.

## Known Developer Notes

- This repository is now shaped as the `abc_crm` addon itself. Commands and CI should mount the repository as `/mnt/extra-addons/abc_crm`, not as a `custom_addons` parent tree.
- `docker-compose.yaml` currently mounts `../abc_crm` to `/mnt/extra-addons`. Because Odoo addon paths normally contain addon directories, local module discovery may require mounting the repo to `/mnt/extra-addons/abc_crm` or mounting the parent directory as `/mnt/extra-addons`.
- `data/lost_reason_data.xml` exists and defines `abc_crm.lost_reason_unqualified`, but it is not currently listed in `__manifest__.py`. Without loading it, the fallback lost reason lookup returns nothing.
- `data/config_parameters.xml` defines `crm.passing_rate`, while `models/crm_lead.py` reads `abc_crm.auto_convert_threshold`. Unless the expected key is added in Odoo, automatic lead disposition uses the code default of `70.0`.
- There is no checked-in `pyproject.toml` at the moment. Ruff uses its defaults unless local configuration is added later.
