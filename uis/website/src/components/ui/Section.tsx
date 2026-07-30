import type { ReactNode } from "react";

type SectionProps = {
  id: string;
  title: string;
  children: ReactNode;
  className?: string;
  narrow?: boolean;
};

export function Section({
  id,
  title,
  children,
  className = "",
  narrow = false,
}: SectionProps) {
  return (
    <section
      id={id}
      className={`mx-auto flex min-h-screen flex-col justify-center px-4 py-16 md:py-24 ${
        narrow ? "max-w-4xl" : "max-w-6xl"
      } ${className}`}
    >
      <h2 className="relative z-0 mx-auto mb-8 inline-block px-4 text-center text-2xl font-bold text-blue-800 md:text-3xl before:absolute before:left-1/2 before:top-1/2 before:-z-10 before:h-[1.65em] before:w-[calc(100%+2.2rem)] before:-translate-x-1/2 before:-translate-y-1/2 before:rounded-full before:bg-blue-500/20 md:before:h-[1.8em] md:before:w-[clamp(220px,calc(100%+4.5rem),760px)]">
        {title}
      </h2>
      {children}
    </section>
  );
}
