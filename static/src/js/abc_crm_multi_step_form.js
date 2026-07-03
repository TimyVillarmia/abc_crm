import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.AbcCrmMultiStepForm = publicWidget.Widget.extend({
    selector: ".s_abc_crm_multi_step_form",
    events: {
        "click .abc-crm-form__next": "_onNextClick",
        "click .abc-crm-form__back": "_onBackClick",
        "submit .abc-crm-form": "_onSubmit",
    },

    start() {
        this.form = this.el.querySelector(".abc-crm-form");
        this.steps = [...this.el.querySelectorAll(".abc-crm-form__step")];
        this.currentStep = 0;
        this._showStep(0);
        return this._super(...arguments);
    },

    _onNextClick() {
        if (!this._validateStep(this.currentStep)) {
            this._showAlert("Please complete the required fields.", "danger");
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

    async _onSubmit(ev) {
        ev.preventDefault();

        if (!this._validateStep(this.currentStep)) {
            this._showAlert("Please complete the required fields.", "danger");
            return;
        }

        const submitButton = this.el.querySelector(".abc-crm-form__submit");
        const formData = new FormData(this.form);
        if (window.odoo?.csrf_token && !formData.get("csrf_token")) {
            formData.append("csrf_token", window.odoo.csrf_token);
        }

        submitButton.disabled = true;
        submitButton.textContent = "Submitting...";
        this._hideAlert();

        try {
            const response = await fetch(this.form.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });
            const body = await response.json();

            if (!response.ok || !body.success) {
                throw new Error(body.error || "Unable to submit the form.");
            }

            this.form.reset();
            this._showStep(0);
            this._showAlert("Thank you. Your inquiry has been submitted.", "success");
        } catch (error) {
            this._showAlert(error.message, "danger");
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Submit";
        }
    },

    _showStep(stepIndex) {
        this.currentStep = stepIndex;
        this.steps.forEach((step, index) => {
            step.classList.toggle("d-none", index !== stepIndex);
        });

        this.el
            .querySelector(".abc-crm-form__back")
            .classList.toggle("d-none", stepIndex === 0);
        this.el
            .querySelector(".abc-crm-form__next")
            .classList.toggle("d-none", stepIndex === this.steps.length - 1);
        this.el
            .querySelector(".abc-crm-form__submit")
            .classList.toggle("d-none", stepIndex !== this.steps.length - 1);

        const progress = this.el.querySelector(".abc-crm-form__progress-bar");
        progress.style.width = `${((stepIndex + 1) / this.steps.length) * 100}%`;

        if (stepIndex === this.steps.length - 1) {
            this._fillReview();
        }
    },

    _validateStep(stepIndex) {
        const step = this.steps[stepIndex];
        const controls = [
            ...step.querySelectorAll("input, select, textarea"),
        ].filter((control) => control.type !== "hidden");

        let isValid = true;
        const radioNames = new Set();

        controls.forEach((control) => {
            control.classList.remove("is-invalid");

            if (!control.required) {
                return;
            }

            if (control.type === "radio") {
                if (radioNames.has(control.name)) {
                    return;
                }
                radioNames.add(control.name);
                const checked = step.querySelector(
                    `input[type="radio"][name="${control.name}"]:checked`
                );
                if (!checked) {
                    isValid = false;
                    step
                        .querySelectorAll(`input[type="radio"][name="${control.name}"]`)
                        .forEach((radio) => radio.classList.add("is-invalid"));
                }
                return;
            }

            if (!control.value.trim()) {
                isValid = false;
                control.classList.add("is-invalid");
            }
        });

        return isValid;
    },

    _fillReview() {
        const formData = new FormData(this.form);
        this.el.querySelectorAll("[data-review]").forEach((node) => {
            node.textContent = formData.get(node.dataset.review) || "-";
        });
    },

    _showAlert(message, type) {
        const alert = this.el.querySelector(".abc-crm-form__alert");
        alert.className = `abc-crm-form__alert alert alert-${type}`;
        alert.textContent = message;
    },

    _hideAlert() {
        const alert = this.el.querySelector(".abc-crm-form__alert");
        alert.className = "abc-crm-form__alert alert d-none";
        alert.textContent = "";
    },
});
