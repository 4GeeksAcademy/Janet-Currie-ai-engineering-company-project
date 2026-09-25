/**
 * Authenticated Lighthouse for uis/web.
 * Injects JWT via Chrome DevTools Protocol. Never prints the token.
 */
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const API = process.env.API_BASE_URL || "http://127.0.0.1:8000";
const EMAIL = process.env.AUTH_SEED_ADMIN_EMAIL || "admin@healthcore.example";
const PASSWORD = process.env.AUTH_SEED_ADMIN_PASSWORD || "HealthCore!dev-admin";
const TARGET = process.argv[2] || "http://127.0.0.1:3001/operations";
const OUTPUT = process.argv[3] || "audit/before/web-operations-desktop-before";
const FORM = process.argv[4] || "desktop";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const DEBUG_PORT = Number(process.env.LH_DEBUG_PORT || 9222);

const login = await fetch(`${API}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ username: EMAIL, password: PASSWORD }),
});
if (!login.ok) {
  throw new Error(`login failed: ${login.status}`);
}
const token = (await login.json()).access_token;
if (!token) throw new Error("login did not return an access token");

const profile = mkdtempSync(path.join(tmpdir(), "hc-lh-"));
const chrome = spawn(
  CHROME,
  [
    "--headless=new",
    "--disable-gpu",
    `--remote-debugging-port=${DEBUG_PORT}`,
    `--user-data-dir=${profile}`,
    "--no-first-run",
    "--no-default-browser-check",
  ],
  { stdio: "ignore" },
);

async function waitJson(url, tries = 40) {
  for (let i = 0; i < tries; i += 1) {
    try {
      const res = await fetch(url);
      if (res.ok) return res.json();
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`timeout waiting for ${url}`);
}

function cdp(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 0;
    const pending = new Map();
    ws.addEventListener("open", () => resolve({
      send(method, params = {}, sessionId) {
        id += 1;
        const msg = { id, method, params };
        if (sessionId) msg.sessionId = sessionId;
        return new Promise((res, rej) => {
          pending.set(id, { res, rej });
          ws.send(JSON.stringify(msg));
        });
      },
      close() {
        ws.close();
      },
    }));
    ws.addEventListener("message", (ev) => {
      const data = JSON.parse(String(ev.data));
      if (data.id && pending.has(data.id)) {
        const { res, rej } = pending.get(data.id);
        pending.delete(data.id);
        if (data.error) rej(new Error(JSON.stringify(data.error)));
        else res(data.result);
      }
    });
    ws.addEventListener("error", () => reject(new Error("cdp websocket error")));
  });
}

try {
  const version = await waitJson(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
  const session = await cdp(version.webSocketDebuggerUrl);
  await session.send("Target.setDiscoverTargets", { discover: true });
  const { targetId } = await session.send("Target.createTarget", {
    url: "http://127.0.0.1:3001/login",
  });
  const attached = await session.send("Target.attachToTarget", {
    targetId,
    flatten: true,
  });
  const sessionId = attached.sessionId;
  const send = (method, params = {}) =>
    session.send(method, params, sessionId);

  await send("Page.enable");
  await send("Runtime.enable");
  await send("Page.navigate", { url: "http://127.0.0.1:3001/login" });
  await new Promise((r) => setTimeout(r, 1500));
  await send("Runtime.evaluate", {
    expression: `localStorage.setItem("healthcore_access_token", ${JSON.stringify(token)})`,
    returnByValue: true,
  });
  await send("Page.navigate", { url: TARGET });
  await new Promise((r) => setTimeout(r, 2500));
  const loc = await send("Runtime.evaluate", {
    expression: "location.pathname",
    returnByValue: true,
  });
  const pathname = loc?.result?.value;
  if (typeof pathname !== "string" || pathname.includes("login")) {
    throw new Error(`expected authenticated page, got ${pathname}`);
  }
  session.close();

  const args = [
    TARGET,
    FORM === "desktop" ? "--preset=desktop" : "--form-factor=mobile",
    "--only-categories=performance,accessibility,best-practices,seo",
    "--output=json,html",
    `--output-path=${OUTPUT}`,
    `--port=${DEBUG_PORT}`,
    "--disable-storage-reset",
    "--quiet",
  ];
  const result = spawnSync("npx", ["--yes", "lighthouse@13.5.0", ...args], {
    stdio: "inherit",
    encoding: "utf8",
  });
  process.exit(result.status ?? 1);
} finally {
  chrome.kill("SIGTERM");
}
