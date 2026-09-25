import { cookies } from "next/headers";
import { HomePage } from "@/components/HomePage";
import { Contact } from "@/components/sections/Contact";
import { Footer, QuickHelpBar } from "@/components/sections/Footer";
import { Locations } from "@/components/sections/Locations";
import { Services } from "@/components/sections/Services";
import { WhyHealthCore } from "@/components/sections/WhyHealthCore";
import type { Lang } from "@/lib/i18n";

function langFromCookie(value: string | undefined): Lang {
  return value === "es" ? "es" : "en";
}

export default async function Page() {
  const jar = await cookies();
  const lang = langFromCookie(jar.get("hc_lang")?.value);

  return (
    <HomePage
      initialLang={lang}
      mainAfterHero={
        <>
          <WhyHealthCore lang={lang} />
          <Services lang={lang} />
          <Locations lang={lang} />
          <Contact lang={lang} />
        </>
      }
      afterMain={
        <>
          <QuickHelpBar lang={lang} />
          <Footer />
        </>
      }
    />
  );
}
