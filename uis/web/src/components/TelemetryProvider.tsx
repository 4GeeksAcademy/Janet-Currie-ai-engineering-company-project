"use client";

import { useEffect, type ReactNode } from "react";
import { recordLoadVital, startTelemetry } from "@/lib/telemetry";

export function TelemetryProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    startTelemetry();
    const timer = window.setTimeout(() => {
      recordLoadVital();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  return <>{children}</>;
}
