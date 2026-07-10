import publicWidget from "@web/legacy/js/public/public_widget";

const EMAIL_PATTERN = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}$/;
const PHONE_PATTERN = /^\+?[0-9\s().-]+$/;

const PHONE_MIN_DIGITS = 7;
const PHONE_MAX_DIGITS = 15;

const INQUIRY_MIN_LENGTH = 10;
const INQUIRY_MAX_LENGTH = 1000;

const REQUEST_TIMEOUT_MS = 15_000;
const MAX_SERVER_ERROR_LENGTH = 300;

publicWidget.registry.AbcCrmMultiStepForm = publicWidget.Widget.extend({
  selector: ".s_abc_crm_multi_step_form",

  events: {
    "click .abc-crm-form__next": "_onNextClick",
    "click .abc-crm-form__back": "_onBackClick",
    "submit .abc-crm-form": "_onSubmit",

    "input .abc-crm-form input": "_onFieldChanged",
    "input .abc-crm-form textarea": "_onFieldChanged",
    "change .abc-crm-form select": "_onFieldChanged",
    "change .abc-crm-form input[type='radio']": "_onFieldChanged",
  },

  start() {
    this.form = this.el.querySelector(".abc-crm-form");

    if (!this.form) {
      return this._super(...arguments);
    }

    this.steps = [...this.el.querySelectorAll(".abc-crm-form__step")];
    this.currentStep = 0;
    this.isSubmitting = false;

    this.messageInput = this.form.querySelector('[name="message"]');
    this.characterCounter = this.el.querySelector(
      ".abc-crm-form__character-counter",
    );
    this.targetCompletionInput = this.form.querySelector(
      '[name="target_completion_date"]',
    );

    this._setTargetCompletionMin();
    this._updateInquiryCounter();
    this._showStep(0);

    return this._super(...arguments);
  },

  // =====================================================
  // Navigation
  // =====================================================

  _onNextClick() {
    const validation = this._validateStep(this.currentStep);

    if (!validation.isValid) {
      this._showAlert(validation.message, "danger");
      this._focusInvalidControl(validation.firstInvalid);
      return;
    }

    this._hideAlert();

    if (this.currentStep < this.steps.length - 1) {
      this._showStep(this.currentStep + 1);
    }
  },

  _onBackClick() {
    this._hideAlert();

    if (this.currentStep > 0) {
      this._showStep(this.currentStep - 1);
    }
  },

  // =====================================================
  // Submit
  // =====================================================

  async _onSubmit(ev) {
    ev.preventDefault();

    if (this.isSubmitting || !this.form) {
      return;
    }

    const validation = this._validateAllSteps();

    if (!validation.isValid) {
      this._showStep(validation.stepIndex);
      this._showAlert(validation.message, "danger");
      this._focusInvalidControl(validation.firstInvalid);
      return;
    }

    const submitButton = this.form.querySelector(".abc-crm-form__submit");

    if (!submitButton) {
      this._showAlert("Unable to submit the form.", "danger");
      return;
    }

    const originalButtonText = submitButton.textContent;
    const abortController = new AbortController();

    const timeoutId = window.setTimeout(() => {
      abortController.abort();
    }, REQUEST_TIMEOUT_MS);

    this.isSubmitting = true;
    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";

    this._hideAlert();

    try {
      const actionUrl = this._getSafeActionUrl();
      const csrfToken = this._getCurrentCsrfToken();

      this._setCsrfToken(csrfToken);

      // Create FormData only after replacing the stale CSRF token.
      const formData = new FormData(this.form);

      const response = await fetch(actionUrl, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        cache: "no-store",
        redirect: "error",
        referrerPolicy: "same-origin",
        signal: abortController.signal,
        headers: {
          Accept: "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      const body = await this._readResponse(response);

      if (!response.ok || body.success !== true) {
        throw new Error(
          this._getSafeServerError(body) || "Unable to submit the form.",
        );
      }

      this.form.reset();

      this._clearValidationState();
      this._updateInquiryCounter();
      this._setTargetCompletionMin();
      this._showStep(0);

      this._showAlert("Thank you. Your inquiry has been submitted.", "success");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        this._showAlert("The request timed out. Please try again.", "danger");
      } else {
        this._showAlert(
          error instanceof Error ? error.message : "Unable to submit the form.",
          "danger",
        );
      }
    } finally {
      window.clearTimeout(timeoutId);

      this.isSubmitting = false;
      submitButton.disabled = false;
      submitButton.textContent = originalButtonText;
    }
  },

  _getCurrentCsrfToken() {
    const token = window.odoo?.csrf_token;

    if (typeof token !== "string" || !token.trim()) {
      throw new Error(
        "Your session could not be verified. Please refresh the page.",
      );
    }

    return token.trim();
  },

  _setCsrfToken(token) {
    let csrfInput = this.form.querySelector('input[name="csrf_token"]');

    if (!csrfInput) {
      csrfInput = document.createElement("input");
      csrfInput.type = "hidden";
      csrfInput.name = "csrf_token";
      this.form.appendChild(csrfInput);
    }

    // Always overwrite the value because a website snippet can contain
    // a token saved from an older editing or browser session.
    csrfInput.value = token;
  },

  _getSafeActionUrl() {
    const action = this.form.getAttribute("action");

    if (!action) {
      throw new Error("The form submission URL is missing.");
    }

    const url = new URL(action, window.location.origin);

    if (url.origin !== window.location.origin) {
      throw new Error("Invalid form submission destination.");
    }

    if (url.protocol !== "http:" && url.protocol !== "https:") {
      throw new Error("Invalid form submission destination.");
    }

    return url.toString();
  },

  async _readResponse(response) {
    const contentType = response.headers.get("content-type") || "";

    if (!contentType.toLowerCase().includes("application/json")) {
      // Consume the response without placing returned HTML in the DOM.
      await response.text();

      return {
        success: false,
        error: `Server returned ${response.status}.`,
      };
    }

    try {
      const body = await response.json();

      if (!body || typeof body !== "object" || Array.isArray(body)) {
        return {
          success: false,
          error: "The server returned an invalid response.",
        };
      }

      return body;
    } catch {
      return {
        success: false,
        error: "The server returned an invalid response.",
      };
    }
  },

  _getSafeServerError(body) {
    if (!body || typeof body.error !== "string") {
      return null;
    }

    const error = body.error
      .replace(/[\u0000-\u001F\u007F]/g, " ")
      .trim()
      .slice(0, MAX_SERVER_ERROR_LENGTH);

    return error || null;
  },

  // =====================================================
  // Validation
  // =====================================================

  _validateAllSteps() {
    for (let stepIndex = 0; stepIndex < this.steps.length; stepIndex++) {
      const result = this._validateStep(stepIndex);

      if (!result.isValid) {
        return {
          ...result,
          stepIndex,
        };
      }
    }

    return {
      isValid: true,
    };
  },

  _validateStep(stepIndex) {
    const step = this.steps[stepIndex];

    if (!step) {
      return {
        isValid: false,
        message: "The form could not be validated.",
        firstInvalid: null,
      };
    }

    const controls = [
      ...step.querySelectorAll("input, select, textarea"),
    ].filter((control) => control.type !== "hidden" && !control.disabled);

    let isValid = true;
    let message = null;
    let firstInvalid = null;

    const radioNames = new Set();

    controls.forEach((control) => {
      control.classList.remove("is-invalid");

      if (control.type === "radio") {
        if (!control.name || radioNames.has(control.name)) {
          return;
        }

        radioNames.add(control.name);

        if (!control.required) {
          return;
        }

        const escapedName = CSS.escape(control.name);

        const radios = [
          ...step.querySelectorAll(
            `input[type="radio"][name="${escapedName}"]`,
          ),
        ];

        const checked = radios.some((radio) => radio.checked);

        if (!checked) {
          isValid = false;
          message ??= "Please answer all project assessment questions.";
          firstInvalid ??= radios[0] || control;

          radios.forEach((radio) => {
            radio.classList.add("is-invalid");
          });
        }

        return;
      }

      const value =
        typeof control.value === "string" ? control.value.trim() : "";

      if (control.required && !value) {
        isValid = false;
        message ??= "Please complete the required fields.";
        firstInvalid ??= control;

        control.classList.add("is-invalid");
        return;
      }

      if (!value) {
        return;
      }

      const validationMessage = this._getControlValidationMessage(
        control,
        value,
      );

      if (validationMessage) {
        isValid = false;
        message ??= validationMessage;
        firstInvalid ??= control;

        control.classList.add("is-invalid");
      }
    });

    return {
      isValid,
      message,
      firstInvalid,
    };
  },

  _getControlValidationMessage(control, value) {
    if (control.name === "message") {
      if (value.length < INQUIRY_MIN_LENGTH) {
        return `Inquiry must be at least ${INQUIRY_MIN_LENGTH} characters.`;
      }

      if (value.length > INQUIRY_MAX_LENGTH) {
        return `Inquiry cannot exceed ${INQUIRY_MAX_LENGTH} characters.`;
      }
    }

    if (control.name === "email_from" && !this._isValidEmailShape(value)) {
      return "Please enter a valid email address.";
    }

    if (control.name === "phone" && !this._isValidPhoneShape(value)) {
      return "Please enter a valid phone or landline number.";
    }

    if (!control.checkValidity()) {
      switch (control.name) {
        case "email_from":
          return "Please enter a valid email address.";

        case "estimated_project_value":
          return "Estimated Project Value must not be negative.";

        case "target_completion_date":
          return "Target Completion Date cannot be in the past.";

        default:
          return "Please check the highlighted fields.";
      }
    }

    return null;
  },

  _isValidEmailShape(value) {
    return EMAIL_PATTERN.test(value.trim());
  },

  _isValidPhoneShape(value) {
    const phone = value.trim();

    if (!PHONE_PATTERN.test(phone)) {
      return false;
    }

    const digits = phone.replace(/\D/g, "");

    return (
      digits.length >= PHONE_MIN_DIGITS && digits.length <= PHONE_MAX_DIGITS
    );
  },

  // =====================================================
  // Field interaction
  // =====================================================

  _onFieldChanged(ev) {
    const control = ev.target;

    if (
      !(control instanceof HTMLInputElement) &&
      !(control instanceof HTMLSelectElement) &&
      !(control instanceof HTMLTextAreaElement)
    ) {
      return;
    }

    if (control.type === "radio" && control.name) {
      const escapedName = CSS.escape(control.name);

      this.form
        .querySelectorAll(`input[type="radio"][name="${escapedName}"]`)
        .forEach((radio) => {
          radio.classList.remove("is-invalid");
        });
    } else {
      control.classList.remove("is-invalid");
    }

    if (control.name === "message") {
      this._updateInquiryCounter();
    }

    this._hideAlert();
  },

  // =====================================================
  // Inquiry counter
  // =====================================================

  _updateInquiryCounter() {
    if (!this.messageInput || !this.characterCounter) {
      return;
    }

    const length = this.messageInput.value.length;

    this.characterCounter.textContent = `${length} / ${INQUIRY_MAX_LENGTH}`;

    this.characterCounter.classList.toggle(
      "text-danger",
      length > 0 && length < INQUIRY_MIN_LENGTH,
    );
  },

  // =====================================================
  // Date minimum
  // =====================================================

  _setTargetCompletionMin() {
    if (!this.targetCompletionInput) {
      return;
    }

    const today = new Date();

    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");

    this.targetCompletionInput.min = `${year}-${month}-${day}`;
  },

  // =====================================================
  // UI
  // =====================================================

  _showStep(stepIndex) {
    if (
      !Number.isInteger(stepIndex) ||
      stepIndex < 0 ||
      stepIndex >= this.steps.length
    ) {
      return;
    }

    this.currentStep = stepIndex;

    this.steps.forEach((step, index) => {
      step.classList.toggle("d-none", index !== stepIndex);
    });

    this.el
      .querySelector(".abc-crm-form__back")
      ?.classList.toggle("d-none", stepIndex === 0);

    this.el
      .querySelector(".abc-crm-form__next")
      ?.classList.toggle("d-none", stepIndex === this.steps.length - 1);

    this.el
      .querySelector(".abc-crm-form__submit")
      ?.classList.toggle("d-none", stepIndex !== this.steps.length - 1);

    const progress = this.el.querySelector(".abc-crm-form__progress");
    const progressBar = this.el.querySelector(".abc-crm-form__progress-bar");

    if (progress && progressBar) {
      const percentage = ((stepIndex + 1) / this.steps.length) * 100;

      progressBar.style.width = `${percentage}%`;
      progress.setAttribute("aria-valuenow", String(stepIndex + 1));
    }

    if (stepIndex === this.steps.length - 1) {
      this._fillReview();
    }
  },

  _fillReview() {
    const formData = new FormData(this.form);

    this.el.querySelectorAll("[data-review]").forEach((node) => {
      const fieldName = node.dataset.review;

      if (!fieldName) {
        node.textContent = "-";
        return;
      }

      let value = formData.get(fieldName);

      if (typeof value !== "string" || !value.trim()) {
        value = "-";
      } else {
        value = value.trim();
      }

      if (value === "yes") {
        value = "Yes";
      } else if (value === "no") {
        value = "No";
      }

      // textContent avoids HTML injection from user-entered values.
      node.textContent = value;
    });
  },

  _focusInvalidControl(control) {
    if (!(control instanceof HTMLElement)) {
      return;
    }

    requestAnimationFrame(() => {
      control.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });

      control.focus({
        preventScroll: true,
      });
    });
  },

  _clearValidationState() {
    this.form.querySelectorAll(".is-invalid").forEach((control) => {
      control.classList.remove("is-invalid");
    });

    this._hideAlert();
  },

  _showAlert(message, type) {
    const alert = this.el.querySelector(".abc-crm-form__alert");

    if (!alert) {
      return;
    }

    const safeType = type === "success" ? "success" : "danger";

    alert.className = `abc-crm-form__alert alert alert-${safeType}`;

    // textContent avoids rendering server-controlled HTML.
    alert.textContent =
      typeof message === "string"
        ? message.slice(0, MAX_SERVER_ERROR_LENGTH)
        : "Unable to submit the form.";

    alert.setAttribute("role", safeType === "danger" ? "alert" : "status");
  },

  _hideAlert() {
    const alert = this.el.querySelector(".abc-crm-form__alert");

    if (!alert) {
      return;
    }

    alert.className = "abc-crm-form__alert alert d-none";
    alert.textContent = "";
  },
});
