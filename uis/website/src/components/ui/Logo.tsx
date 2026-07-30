export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center space-x-3 ${className}`}>
      <span
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-blue-200 bg-blue-100"
        aria-hidden="true"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="10" cy="10" r="9" fill="#2563EB" />
          <path
            d="M10 5V15M5 10H15"
            stroke="white"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </span>
      <span className="text-2xl font-bold text-blue-700 md:text-3xl">HealthCore</span>
    </span>
  );
}
