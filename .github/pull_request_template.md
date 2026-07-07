## Summary

<!-- What changed, why it changed, and the user/business impact. -->

## Change Type

<!-- Check all that apply. -->

- [ ] Bug fix
- [ ] Feature
- [ ] Refactor
- [ ] Performance
- [ ] Tests
- [ ] Documentation
- [ ] CI / tooling
- [ ] Data / security / manifest

## Odoo Impact

<!-- Check all areas touched by this PR. -->

- [ ] Python models, controllers, or business logic
- [ ] XML views, website snippets, data, or security records
- [ ] Website frontend assets: JS / SCSS / templates
- [ ] Manifest, dependencies, or asset bundles
- [ ] Tests, CI, docs, or tooling only
- [ ] No Odoo runtime impact

## Testing

<!-- Mark what was run. Explain any skipped checks. -->

- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `python3 -m compileall .`
- [ ] XML syntax parse check
- [ ] Docker/Odoo tests with `--test-tags=/abc_crm`
- [ ] Manual website form flow checked
- [ ] Not applicable

### Manual Steps

<!-- Required for UI, website form, workflow, or behavior changes. Delete if not applicable. -->

1.
2.
3.

## Screenshots / UI Evidence

<!-- Add screenshots or recordings for website/UI changes. Write "N/A" if not applicable. -->

N/A

## Deployment / Migration Notes

<!-- Mention module upgrades, data changes, config parameters, permissions, or rollout risk. Write "None" if not applicable. -->

None

## Reviewer Notes

<!-- Call out risky files, intentional tradeoffs, or areas that need close review. -->

## Checklist

- [ ] I reviewed the diff before requesting review.
- [ ] I preserved existing API, controller, and website form field names where relevant.
- [ ] I updated tests or explained why tests were not needed.
- [ ] I updated README or developer docs for user-facing, API, CI, or operational changes.
- [ ] I verified no secrets, real `odoo.conf`, `.env`, or local-only files were committed.
- [ ] I considered module upgrade, migration, and security implications for data/XML/manifest changes.
