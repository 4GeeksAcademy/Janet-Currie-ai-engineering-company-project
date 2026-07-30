import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
  eyebrow?: string;
  title?: string;
};

export function Card({ children, className = "", eyebrow, title }: CardProps) {
  return (
    <article
      className={`rounded-2xl border border-gray-100 bg-white p-8 shadow-lg transition-shadow duration-200 hover:shadow-2xl ${className}`}
    >
      {eyebrow ? (
        <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-blue-600">
          {eyebrow}
        </p>
      ) : null}
      {title ? (
        <h3 className="mb-2 text-xl font-semibold text-blue-700">{title}</h3>
      ) : null}
      {children}
    </article>
  );
}
