(function () {
  "use strict";

  const XSS_PAYLOAD =
    '<img src=x onerror="window.__xssExecuted = true">' +
    "<script>window.__xssExecuted = true</script>";

  function assert(condition, message) {
    if (!condition) {
      throw new Error(message);
    }
  }

  function nextFrame() {
    return new Promise((resolve) => requestAnimationFrame(resolve));
  }

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  async function waitFor(predicate, message) {
    for (let index = 0; index < 80; index++) {
      if (predicate()) {
        return;
      }
      await delay(50);
    }
    throw new Error(message);
  }

  function todayIso() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function form() {
    const node = document.querySelector(".abc-crm-form");
    assert(node, "Expected ABC CRM form to exist");
    return node;
  }

  function alertNode() {
    const node = document.querySelector(".abc-crm-form__alert");
    assert(node, "Expected ABC CRM alert to exist");
    return node;
  }

  function submitButton() {
    const node = form().querySelector(".abc-crm-form__submit");
    assert(node, "Expected ABC CRM submit button to exist");
    return node;
  }

  function setValue(name, value) {
    const control = form().querySelector(`[name="${CSS.escape(name)}"]`);
    assert(control, `Expected control ${name} to exist`);
    control.value = value;
    control.dispatchEvent(new Event("input", { bubbles: true }));
    control.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function checkRadio(name, value) {
    const control = form().querySelector(
      `input[type="radio"][name="${CSS.escape(name)}"][value="${CSS.escape(value)}"]`,
    );
    assert(control, `Expected radio ${name}=${value} to exist`);
    control.checked = true;
    control.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function fillValidForm(overrides = {}) {
    const values = {
      contact_name: "Jane Buyer",
      partner_name: "ABC Construction",
      function: "Purchasing Manager",
      email_from: "jane@example.com",
      phone: "+639170000000",
      message: "Website inquiry for browser security tests",
      project_name: "Warehouse Extension",
      project_location: "Cebu City",
      project_type: "Commercial",
      estimated_project_value: "1250000",
      target_completion_date: todayIso(),
      company_type: "contractor",
      ...overrides,
    };

    for (const [name, value] of Object.entries(values)) {
      setValue(name, value);
    }

    for (const name of [
      "is_five_storey_up",
      "is_ongoing",
      "is_aac_user",
      "is_open",
      "has_aac_needs",
      "has_design_specifications",
    ]) {
      checkRadio(name, "yes");
    }
  }

  async function submitForm() {
    form().dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await nextFrame();
  }

  function resetFormState() {
    form().reset();
    form().setAttribute("action", "/abc_crm/website/lead");
    alertNode().textContent = "";
    alertNode().className = "abc-crm-form__alert alert d-none";
    delete window.__xssExecuted;
  }

  function successResponse() {
    return new Response(JSON.stringify({ success: true, lead: { id: 1 } }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  }

  async function withMockFetch(callback) {
    const originalFetch = window.fetch;
    const calls = [];
    window.fetch = async function (url, options = {}) {
      calls.push({ url, options, formData: options.body });
      return successResponse();
    };

    try {
      await callback(calls);
    } finally {
      window.fetch = originalFetch;
    }
  }

  async function testCurrentCsrfToken() {
    resetFormState();
    fillValidForm();

    await withMockFetch(async (calls) => {
      await submitForm();
      await waitFor(() => calls.length === 1, "Expected one submit request");

      const csrfInput = form().querySelector('[name="csrf_token"]');
      assert(csrfInput, "Expected CSRF input to exist");
      assert(
        csrfInput.value === window.odoo.csrf_token,
        "Expected CSRF input to match window.odoo.csrf_token",
      );
      assert(
        calls[0].formData.get("csrf_token") === window.odoo.csrf_token,
        "Expected submitted FormData to contain the current CSRF token",
      );
      assert(calls[0].options.credentials === "same-origin", "Expected same-origin credentials");
      assert(calls[0].options.redirect === "error", "Expected redirect rejection");
    });
  }

  async function testStaleCsrfReplacement() {
    resetFormState();
    fillValidForm();
    form().querySelector('[name="csrf_token"]').value = "intentionally-stale-token";

    await withMockFetch(async (calls) => {
      await submitForm();
      await waitFor(() => calls.length === 1, "Expected stale-token submit request");
      assert(
        form().querySelector('[name="csrf_token"]').value === window.odoo.csrf_token,
        "Expected stale CSRF token to be overwritten",
      );
      assert(
        calls[0].formData.get("csrf_token") === window.odoo.csrf_token,
        "Expected stale token to be replaced in request payload",
      );
    });
  }

  async function testMissingCsrfInput() {
    resetFormState();
    fillValidForm();
    form().querySelector('[name="csrf_token"]').remove();

    await withMockFetch(async (calls) => {
      await submitForm();
      await waitFor(() => calls.length === 1, "Expected missing-token submit request");
      const csrfInput = form().querySelector('input[name="csrf_token"]');
      assert(csrfInput, "Expected missing CSRF input to be recreated");
      assert(csrfInput.type === "hidden", "Expected recreated CSRF input to be hidden");
      assert(csrfInput.value === window.odoo.csrf_token, "Expected recreated CSRF token value");
    });
  }

  async function testDuplicateSubmissionProtection() {
    resetFormState();
    fillValidForm();

    const originalFetch = window.fetch;
    let resolveFetch;
    const calls = [];
    window.fetch = function (url, options = {}) {
      calls.push({ url, options, formData: options.body });
      return new Promise((resolve) => {
        resolveFetch = () => resolve(successResponse());
      });
    };

    try {
      await submitForm();
      await submitForm();
      assert(calls.length === 1, "Expected duplicate submit to send only one request");
      assert(submitButton().disabled, "Expected submit button to be disabled while pending");
      resolveFetch();
      await waitFor(
        () => !submitButton().disabled,
        "Expected submit button to be restored after request",
      );
    } finally {
      window.fetch = originalFetch;
    }
  }

  async function testCrossOriginActionProtection() {
    resetFormState();
    fillValidForm();
    form().setAttribute("action", "https://example.com/abc_crm/website/lead");

    await withMockFetch(async (calls) => {
      await submitForm();
      await waitFor(
        () => alertNode().textContent.includes("Invalid form submission destination"),
        "Expected safe cross-origin error",
      );
      assert(calls.length === 0, "Expected no request for cross-origin action");
    });
  }

  async function testInvalidJsonResponse() {
    resetFormState();
    fillValidForm();

    const originalFetch = window.fetch;
    window.fetch = async () =>
      new Response("{not json", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });

    try {
      await submitForm();
      await waitFor(
        () => alertNode().textContent.includes("invalid response"),
        "Expected invalid JSON response error",
      );
      assert(!alertNode().innerHTML.includes("{not json"), "Expected raw JSON not to render");
    } finally {
      window.fetch = originalFetch;
    }
  }

  async function testHtmlResponseSafety() {
    resetFormState();
    fillValidForm();
    window.__xssExecuted = false;

    const html =
      '<img src=x onerror="window.__xssExecuted = true">' +
      "<script>window.__xssExecuted = true</script>";
    const originalFetch = window.fetch;
    window.fetch = async () =>
      new Response(html, {
        status: 500,
        headers: { "Content-Type": "text/html" },
      });

    try {
      await submitForm();
      await waitFor(
        () => alertNode().textContent.includes("Server returned 500"),
        "Expected generic HTML response error",
      );
      assert(window.__xssExecuted === false, "Expected returned HTML not to execute");
      assert(!alertNode().querySelector("img, script"), "Expected returned HTML not to render");
    } finally {
      window.fetch = originalFetch;
    }
  }

  async function testXssProtection() {
    resetFormState();
    fillValidForm({ contact_name: XSS_PAYLOAD });
    window.__xssExecuted = false;

    const nextButton = document.querySelector(".abc-crm-form__next");
    assert(nextButton, "Expected next button to exist");
    for (let index = 0; index < 3; index++) {
      nextButton.click();
      await nextFrame();
    }

    const reviewNode = document.querySelector('[data-review="contact_name"]');
    assert(reviewNode.textContent === XSS_PAYLOAD, "Expected review value as text");
    assert(!reviewNode.querySelector("img, script"), "Expected no review HTML injection");
    assert(window.__xssExecuted === false, "Expected review payload not to execute");

    const originalFetch = window.fetch;
    window.fetch = async () =>
      new Response(JSON.stringify({ success: false, error: XSS_PAYLOAD }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });

    try {
      await submitForm();
      await waitFor(
        () => alertNode().textContent.includes("<img"),
        "Expected server error to be displayed as text",
      );
      assert(!alertNode().querySelector("img, script"), "Expected no alert HTML injection");
      assert(window.__xssExecuted === false, "Expected alert payload not to execute");
    } finally {
      window.fetch = originalFetch;
    }
  }

  async function testRequestTimeout() {
    resetFormState();
    fillValidForm();

    const originalFetch = window.fetch;
    const originalSetTimeout = window.setTimeout;
    const originalClearTimeout = window.clearTimeout;
    const calls = [];
    let abortCount = 0;

    window.setTimeout = function (callback) {
      return originalSetTimeout(callback, 0);
    };
    window.clearTimeout = function (timeoutId) {
      return originalClearTimeout(timeoutId);
    };
    window.fetch = function (url, options = {}) {
      calls.push({ url, options, formData: options.body });
      return new Promise((resolve, reject) => {
        options.signal.addEventListener("abort", () => {
          abortCount += 1;
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    };

    try {
      await submitForm();
      await waitFor(
        () => alertNode().textContent.includes("timed out"),
        "Expected timeout error",
      );
      assert(abortCount === 1, "Expected request to be aborted");
      assert(calls.length === 1, "Expected one active timeout request");
      assert(!submitButton().disabled, "Expected submit button to be restored");

      await submitForm();
      await waitFor(() => calls.length === 2, "Expected later submit to be allowed");
      await waitFor(() => abortCount === 2, "Expected later timeout to abort");
      assert(!submitButton().disabled, "Expected submit button to be restored again");
    } finally {
      window.fetch = originalFetch;
      window.setTimeout = originalSetTimeout;
      window.clearTimeout = originalClearTimeout;
    }
  }

  window.abcCrmMultiStepFormSecurityTests = {
    async run() {
      window.odoo = window.odoo || {};
      window.odoo.csrf_token = "current-browser-csrf-token";

      await waitFor(() => form(), "Expected ABC CRM form to be ready");
      await delay(250);

      await testCurrentCsrfToken();
      await testStaleCsrfReplacement();
      await testMissingCsrfInput();
      await testDuplicateSubmissionProtection();
      await testCrossOriginActionProtection();
      await testInvalidJsonResponse();
      await testHtmlResponseSafety();
      await testXssProtection();
      await testRequestTimeout();

      console.log("test successful");
    },
  };
})();
