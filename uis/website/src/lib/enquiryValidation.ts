import { clinics } from "@/lib/locations";

export type EnquiryFormValues = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  email: string;
  phone: string;
  preferred_language: string;
  preferred_clinic: string;
  preferred_date: string;
  preferred_time: string;
  service_type: string;
  new_patient: string;
  has_insurance: string;
  insurance_provider: string;
  insurance_member_id: string;
  patient_id: string;
  health_concern: string;
  contact_consent: boolean;
};

export const emptyEnquiryForm: EnquiryFormValues = {
  first_name: "",
  last_name: "",
  date_of_birth: "",
  email: "",
  phone: "",
  preferred_language: "",
  preferred_clinic: "",
  preferred_date: "",
  preferred_time: "",
  service_type: "",
  new_patient: "",
  has_insurance: "",
  insurance_provider: "",
  insurance_member_id: "",
  patient_id: "",
  health_concern: "",
  contact_consent: false,
};

const namePattern = /^[A-Za-zÁÉÍÓÚÑÜáéíóúñü ]{2,50}$/;
const phonePattern = /^\+\d[\d\s-]{7,}$/;
const memberIdPattern = /^[A-Za-z0-9]{6,20}$/;
const patientIdPattern = /^HC-[A-Za-z0-9]{6}$/;

function addBusinessDays(startDate: Date, days: number): Date {
  const result = new Date(startDate);
  let remaining = days;
  while (remaining > 0) {
    result.setDate(result.getDate() + 1);
    const d = result.getDay();
    if (d !== 0 && d !== 6) remaining -= 1;
  }
  return result;
}

function ageFromDob(dob: string): number {
  const birth = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age -= 1;
  return age;
}

export function validateEnquiryField(
  field: keyof EnquiryFormValues,
  values: EnquiryFormValues
): string {
  const value = values[field];

  switch (field) {
    case "first_name":
      return typeof value === "string" && namePattern.test(value.trim())
        ? ""
        : "First name must contain only letters and be at least 2 characters";
    case "last_name":
      return typeof value === "string" && namePattern.test(value.trim())
        ? ""
        : "Last name must contain only letters and be at least 2 characters";
    case "date_of_birth": {
      if (typeof value !== "string" || !value) {
        return "Enter a valid date of birth. Patient must be between 0 and 120 years old";
      }
      const age = ageFromDob(value);
      if (Number.isNaN(age) || age < 0 || age > 120 || new Date(value) > new Date()) {
        return "Enter a valid date of birth. Patient must be between 0 and 120 years old";
      }
      return "";
    }
    case "email":
      return typeof value === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
        ? ""
        : "Enter a valid email address (example: name@provider.com)";
    case "phone":
      return typeof value === "string" && phonePattern.test(value.trim())
        ? ""
        : "Phone must include a country code (example: +1 305 555 0191)";
    case "preferred_language":
      return value ? "" : "Select your preferred language";
    case "preferred_clinic":
      return value ? "" : "Select the clinic you would like to visit";
    case "preferred_date": {
      if (typeof value !== "string" || !value) {
        return "Select a date at least 1 business day from today and no more than 60 days ahead";
      }
      const selected = new Date(value);
      const min = addBusinessDays(new Date(), 1);
      min.setHours(0, 0, 0, 0);
      const max = new Date();
      max.setDate(max.getDate() + 60);
      max.setHours(23, 59, 59, 999);
      if (selected < min || selected > max) {
        return "Select a date at least 1 business day from today and no more than 60 days ahead";
      }
      return "";
    }
    case "preferred_time":
      return value ? "" : "Select your preferred time of day";
    case "service_type":
      if (!value) return "Select the type of care you are looking for";
      if (value === "Paediatric Care" && values.date_of_birth) {
        const age = ageFromDob(values.date_of_birth);
        if (age >= 18) {
          return "Paediatric Care is available for patients under 18. Please check the date of birth or select a different service.";
        }
      }
      return "";
    case "new_patient":
      return value ? "" : "Please indicate whether this is your first visit to HealthCore";
    case "has_insurance":
      return value ? "" : "Please indicate whether you have health insurance";
    case "insurance_provider":
      if (values.has_insurance !== "Yes") return "";
      return typeof value === "string" && value.trim().length > 0 && value.trim().length <= 100
        ? ""
        : "Please enter your insurance provider name";
    case "insurance_member_id":
      if (values.has_insurance !== "Yes") return "";
      return typeof value === "string" && memberIdPattern.test(value.trim())
        ? ""
        : "Member ID must be between 6 and 20 alphanumeric characters";
    case "patient_id":
      if (values.new_patient !== "No" || !value) return "";
      return typeof value === "string" && patientIdPattern.test(value.trim())
        ? ""
        : "Patient ID must match HC- followed by 6 alphanumeric characters";
    case "health_concern":
      return typeof value === "string" && value.trim().length >= 20 && value.trim().length <= 500
        ? ""
        : "Please describe your health concern (20–500 characters)";
    case "contact_consent":
      return value === true ? "" : "You must consent to being contacted before submitting this form";
    default:
      return "";
  }
}

export function validateEnquiryForm(values: EnquiryFormValues): Record<string, string> {
  const fields: (keyof EnquiryFormValues)[] = [
    "first_name",
    "last_name",
    "date_of_birth",
    "email",
    "phone",
    "preferred_language",
    "preferred_clinic",
    "preferred_date",
    "preferred_time",
    "service_type",
    "new_patient",
    "has_insurance",
    "insurance_provider",
    "insurance_member_id",
    "patient_id",
    "health_concern",
    "contact_consent",
  ];
  const errors: Record<string, string> = {};
  for (const field of fields) {
    const message = validateEnquiryField(field, values);
    if (message) errors[field] = message;
  }
  return errors;
}

export function shouldWarnEvening(values: EnquiryFormValues): boolean {
  if (values.preferred_time !== "Evening" || !values.preferred_clinic) return false;
  const clinic = clinics.find((c) => c.name === values.preferred_clinic);
  return Boolean(clinic && clinic.eveningCloseHour < 20);
}
