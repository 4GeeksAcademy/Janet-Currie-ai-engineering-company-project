import Link from "next/link";

export default function WelcomePage() {
  return (
    <div className="mx-auto max-w-3xl">
      <p className="text-sm font-semibold uppercase tracking-wide text-sky-700">Welcome</p>
      <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl">
        HealthCore Digital backoffice
      </h2>
      <p className="mt-4 text-lg leading-relaxed text-slate-600">
        This internal workspace hosts company operations tooling. Milestone 2 business logic is
        imported from the shared <code className="rounded bg-slate-200 px-1.5 py-0.5 text-sm">src/</code>{" "}
        modules and rendered in the operations analytics view — not only in the console.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="font-semibold text-slate-900">What you can do</h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-600">
            <li>Review claim denial and no-show analytics</li>
            <li>Search sample claims and clinicians</li>
            <li>Run CME and validation checks</li>
          </ul>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="font-semibold text-slate-900">Get started</h3>
          <p className="mt-3 text-slate-600">
            Open operations analytics to exercise the imported TypeScript utilities against sample
            HealthCore data.
          </p>
          <Link
            href="/operations"
            className="mt-4 inline-flex rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800"
          >
            Open operations analytics
          </Link>
        </div>
      </div>
    </div>
  );
}
