import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Source_Sans_3 } from "next/font/google";
import "./globals.css";

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "HealthCore | Outpatient Healthcare Network",
  description:
    "HealthCore: Outpatient healthcare network offering primary care, specialist consultations, chronic disease management, and preventive health programmes.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const jar = await cookies();
  const lang = jar.get("hc_lang")?.value === "es" ? "es" : "en";

  return (
    <html lang={lang}>
      <body className={`${sourceSans.variable} bg-white font-sans text-[18px] leading-relaxed text-gray-900 antialiased`}>
        {children}
      </body>
    </html>
  );
}
