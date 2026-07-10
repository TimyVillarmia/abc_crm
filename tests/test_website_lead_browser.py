from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestAbcCrmWebsiteLeadBrowser(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        website = cls.env["website"].search([], limit=1)
        view = (
            cls.env["ir.ui.view"]
            .sudo()
            .create(
                {
                    "name": "ABC CRM Security Test Page",
                    "type": "qweb",
                    "key": "abc_crm.security_test_page",
                    "arch_db": """
                    <t name="ABC CRM Security Test Page">
                        <t t-call="website.layout">
                            <t t-call="abc_crm.s_abc_crm_multi_step_form"/>
                        </t>
                    </t>
                """,
                }
            )
        )
        cls.env["website.page"].sudo().create(
            {
                "name": "ABC CRM Security Test Page",
                "url": "/abc-crm-security-test",
                "view_id": view.id,
                "website_id": website.id if website else False,
                "is_published": True,
            }
        )

    def test_browser_form_csrf_and_response_safety(self):
        lead_model = self.env["crm.lead"].with_context(active_test=False)
        before_count = lead_model.search_count([])

        self.browser_js(
            "/abc-crm-security-test?debug=tests",
            """
                (async () => {
                    await window.abcCrmMultiStepFormSecurityTests.run();
                })();
            """,
            ready=(
                "document.querySelector('.abc-crm-form') && window.abcCrmMultiStepFormSecurityTests"
            ),
            timeout=90,
        )

        self.assertEqual(lead_model.search_count([]), before_count)
