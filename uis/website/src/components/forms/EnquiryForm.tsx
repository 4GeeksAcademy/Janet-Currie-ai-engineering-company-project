"use client";

import { useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { clinics } from "@/lib/locations";
import {
  emptyEnquiryForm,
  shouldWarnEvening,
  validateEnquiryField,
  validateEnquiryForm,
  type EnquiryFormValues,
} from "@/lib/enquiryValidation";

const fieldClass =
  "w-full min-h-12 rounded-md border border-slate-300 bg-white px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-blue-400";

export function EnquiryForm() {
  const [values, setValues] = useState<EnquiryFormValues>(emptyEnquiryForm);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);

  const eveningWarning = useMemo(() => shouldWarnEvening(values), [values]);

  const updateField = <K extends keyof EnquiryFormValues>(
    key: K,
    value: EnquiryFormValues[K]
  ) => {
    setValues((prev) => {
      const next = { ...prev, [key]: value };
      setErrors((prevErrors) => ({
        ...prevErrors,
        [key]: validateEnquiryField(key, next),
      }));
      return next;
    });
    setSuccess(false);
  };

  const onTextChange =
    (key: keyof EnquiryFormValues) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      updateField(key, event.target.value as EnquiryFormValues[typeof key]);
    };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    const nextErrors = validateEnquiryForm(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    setSuccess(true);
    setValues(emptyEnquiryForm);
  };

  return (
    <form className="space-y-7" noValidate onSubmit={onSubmit}>
      {success ? (
        <div
          className="rounded-xl border border-green-200 bg-green-50 p-4 text-green-900 whitespace-pre-line"
          role="status"
        >
          {`Thank you for reaching out to HealthCore.
We have received your enquiry. A member of our front desk team will contact you within 1 business day to confirm your appointment details and answer any questions.
If you need urgent assistance, please call your preferred clinic directly using the numbers listed on our website.
We look forward to caring for you.`}
        </div>
      ) : null}

      <fieldset className="space-y-4">
        <legend className="text-xl font-semibold text-blue-800">Contact details</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            id="first_name"
            label="First name"
            error={errors.first_name}
            value={values.first_name}
            onChange={onTextChange("first_name")}
          />
          <Field
            id="last_name"
            label="Last name"
            error={errors.last_name}
            value={values.last_name}
            onChange={onTextChange("last_name")}
          />
          <Field
            id="date_of_birth"
            label="Date of birth"
            type="date"
            error={errors.date_of_birth}
            value={values.date_of_birth}
            onChange={onTextChange("date_of_birth")}
          />
          <Field
            id="email"
            label="Email address"
            type="email"
            error={errors.email}
            value={values.email}
            onChange={onTextChange("email")}
          />
        </div>
        <Field
          id="phone"
          label="Phone number"
          type="tel"
          error={errors.phone}
          value={values.phone}
          onChange={onTextChange("phone")}
          placeholder="e.g. +1 305 555 0191"
        />
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="text-xl font-semibold text-blue-800">Visit preferences</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            id="preferred_language"
            label="Preferred language"
            error={errors.preferred_language}
            value={values.preferred_language}
            onChange={onTextChange("preferred_language")}
            options={["English", "Spanish"]}
          />
          <SelectField
            id="preferred_clinic"
            label="Preferred clinic"
            error={errors.preferred_clinic}
            value={values.preferred_clinic}
            onChange={onTextChange("preferred_clinic")}
            options={clinics.map((c) => c.name)}
          />
          <Field
            id="preferred_date"
            label="Preferred date"
            type="date"
            error={errors.preferred_date}
            value={values.preferred_date}
            onChange={onTextChange("preferred_date")}
          />
          <div>
            <SelectField
              id="preferred_time"
              label="Preferred time of day"
              error={errors.preferred_time}
              value={values.preferred_time}
              onChange={onTextChange("preferred_time")}
              options={["Morning", "Afternoon", "Evening"]}
              optionLabels={{
                Morning: "Morning (7am-12pm)",
                Afternoon: "Afternoon (12pm-5pm)",
                Evening: "Evening (5pm-8pm)",
              }}
            />
            {eveningWarning ? (
              <p className="mt-1 text-sm text-amber-700">
                Evening appointments may be limited at this clinic. Our team will confirm the
                nearest available slot.
              </p>
            ) : null}
          </div>
        </div>
        <SelectField
          id="service_type"
          label="Service needed"
          error={errors.service_type}
          value={values.service_type}
          onChange={onTextChange("service_type")}
          options={[
            "Primary Care",
            "Chronic Disease Management",
            "Specialist Consultation",
            "Preventive Health",
            "Women's Health",
            "Paediatric Care",
            "Mental Health",
          ]}
        />
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="text-xl font-semibold text-blue-800">History and insurance</legend>
        <RadioGroup
          legend="Is this your first visit to HealthCore?"
          name="new_patient"
          value={values.new_patient}
          error={errors.new_patient}
          onChange={(value) => updateField("new_patient", value)}
        />
        {values.new_patient === "No" ? (
          <Field
            id="patient_id"
            label="Patient ID (if returning)"
            error={errors.patient_id}
            value={values.patient_id}
            onChange={onTextChange("patient_id")}
            placeholder="e.g. HC-A3F291"
          />
        ) : null}
        <RadioGroup
          legend="Do you have health insurance?"
          name="has_insurance"
          value={values.has_insurance}
          error={errors.has_insurance}
          onChange={(value) => updateField("has_insurance", value)}
        />
        {values.has_insurance === "Yes" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              id="insurance_provider"
              label="Insurance provider"
              error={errors.insurance_provider}
              value={values.insurance_provider}
              onChange={onTextChange("insurance_provider")}
            />
            <Field
              id="insurance_member_id"
              label="Member ID"
              error={errors.insurance_member_id}
              value={values.insurance_member_id}
              onChange={onTextChange("insurance_member_id")}
            />
          </div>
        ) : null}
        <div>
          <label htmlFor="health_concern" className="mb-1 block font-semibold">
            Brief description of your health concern
          </label>
          <textarea
            id="health_concern"
            name="health_concern"
            rows={4}
            maxLength={500}
            className={fieldClass}
            value={values.health_concern}
            onChange={onTextChange("health_concern")}
          />
          <div className="mt-1 flex justify-between text-sm text-slate-600">
            <span className="text-red-600">{errors.health_concern}</span>
            <span>{values.health_concern.length}/500</span>
          </div>
        </div>
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            name="contact_consent"
            checked={values.contact_consent}
            onChange={(event) => updateField("contact_consent", event.target.checked)}
            className="mt-1"
          />
          <span>I consent to HealthCore contacting me about this enquiry</span>
        </label>
        {errors.contact_consent ? (
          <p className="text-sm text-red-600">{errors.contact_consent}</p>
        ) : null}
      </fieldset>

      <div className="flex flex-wrap gap-3">
        <Button type="submit">Submit enquiry</Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setValues(emptyEnquiryForm);
            setErrors({});
            setSuccess(false);
          }}
        >
          Clear
        </Button>
      </div>
    </form>
  );
}

function Field({
  id,
  label,
  error,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  id: string;
  label: string;
  error?: string;
  value: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block font-semibold">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        className={fieldClass}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
      />
      {error ? <span className="mt-1 block text-sm text-red-600">{error}</span> : null}
    </div>
  );
}

function SelectField({
  id,
  label,
  error,
  value,
  onChange,
  options,
  optionLabels,
}: {
  id: string;
  label: string;
  error?: string;
  value: string;
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void;
  options: string[];
  optionLabels?: Record<string, string>;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block font-semibold">
        {label}
      </label>
      <select id={id} name={id} className={fieldClass} value={value} onChange={onChange}>
        <option value="" disabled>
          Select
        </option>
        {options.map((option) => (
          <option key={option} value={option}>
            {optionLabels?.[option] ?? option}
          </option>
        ))}
      </select>
      {error ? <span className="mt-1 block text-sm text-red-600">{error}</span> : null}
    </div>
  );
}

function RadioGroup({
  legend,
  name,
  value,
  error,
  onChange,
}: {
  legend: string;
  name: string;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <span className="mb-1 block font-semibold">{legend}</span>
      <div className="flex flex-wrap items-center gap-6">
        {["Yes", "No"].map((option) => (
          <label key={option} className="inline-flex items-center gap-2">
            <input
              type="radio"
              name={name}
              value={option}
              checked={value === option}
              onChange={() => onChange(option)}
            />
            <span>{option}</span>
          </label>
        ))}
      </div>
      {error ? <span className="mt-1 block text-sm text-red-600">{error}</span> : null}
    </div>
  );
}
