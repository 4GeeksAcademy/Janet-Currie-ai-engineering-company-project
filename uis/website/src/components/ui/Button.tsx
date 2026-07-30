import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  children: ReactNode;
};

const variantClass: Record<ButtonVariant, string> = {
  primary:
    "bg-gradient-to-r from-blue-700 to-blue-500 text-white shadow-lg hover:scale-[1.02] hover:shadow-xl focus:ring-blue-300",
  secondary:
    "border border-blue-700 bg-blue-50 text-blue-700 hover:bg-blue-100 focus:ring-blue-400",
  ghost:
    "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 focus:ring-blue-400",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-base font-semibold transition focus:outline-none focus:ring-4 disabled:opacity-60 ${variantClass[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
