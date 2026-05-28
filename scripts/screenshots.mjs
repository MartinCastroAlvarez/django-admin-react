#!/usr/bin/env node
//
// scripts/screenshots.mjs — Playwright capture for docs/screenshots/.
//
// Boots a long-running Django dev server elsewhere; this script only
// captures URLs. The caller (scripts/screenshots.sh) is responsible
// for the dev server lifecycle.
//
// The capture set is split between light + dark, desktop + mobile,
// and read + edit views so the README's PyPI page shows the SPA's
// actual surface area rather than one repeated grid.

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const BASE = process.env.DAR_BASE_URL || "http://127.0.0.1:8765";
const OUT = resolve(process.cwd(), "docs/screenshots");
const USER = process.env.DAR_USER || "screenshots";
const PASS = process.env.DAR_PASS || "screenshots-only-do-not-reuse";

mkdirSync(OUT, { recursive: true });

// Dark-mode capture: the SPA's source of truth is localStorage[`dar:theme`]
// (see `@dar/customization`'s `resolveTheme` — explicit choice wins over
// the system pref). The `dar-theme` cookie only controls the server-side
// no-flash repaint. We need BOTH to make the SPA render dark:
//
// 1. Cookie: SpaIndexView reads it to add `class="dark"` to <html> at
//    first paint, so there's no light→dark flash mid-capture.
// 2. localStorage init script: the SPA's `initTheme()` then resolves
//    that same dark preference and keeps the class on.
//
// Without (2), the SPA boots and immediately rewrites `<html>` to light
// because localStorage is empty + headless Chrome's prefers-color-scheme
// defaults to light. The cookie gets overruled mid-boot.
function darkCookie() {
  return {
    name: "dar-theme",
    value: "dark",
    domain: "127.0.0.1",
    path: "/",
    httpOnly: false,
    secure: false,
  };
}

const DARK_INIT_SCRIPT = `
  try {
    window.localStorage.setItem('dar:theme', 'dark');
  } catch (_) {}
`;

// Capture the django-admin-react SPA (mounted at /admin-react/), NOT
// the legacy admin (/admin/legacy/). The legacy login is used only to
// establish the shared session cookie; every captured page below is the
// React SPA or its API. `spa` captures wait for React to render past
// network-idle.
const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };
const DSF = 2;

const captures = [
  // 01 — Login page (light). The package's own LoginView, branded.
  {
    name: "01-spa-login.png",
    viewport: DESKTOP,
    deviceScaleFactor: DSF,
    theme: "light",
    setup: null,
    spa: false,
    path: "/admin-react/login/?next=/admin-react/",
  },
  // 02 — Registry / home in DARK mode. Hero shot: shows the multi-app
  // structure + the dark theme support (one of the SPA's headline
  // features, #84). Replaces the prior light registry as the most
  // dramatic landing-page tile.
  {
    name: "02-spa-registry.png",
    viewport: DESKTOP,
    deviceScaleFactor: DSF,
    theme: "dark",
    setup: "login",
    spa: true,
    path: "/admin-react/",
  },
  // 03 — List view (light) on the richest example admin (fintech
  // transactions): list_display + list_filter + date_hierarchy +
  // autocomplete + admin.display labels all visible.
  {
    name: "03-spa-list.png",
    viewport: DESKTOP,
    deviceScaleFactor: DSF,
    theme: "light",
    setup: "login",
    spa: true,
    path: "/admin-react/fintech/transaction/",
  },
  // 04 — Mobile list (light): the stacked RecordCardList renderer
  // that the SPA falls back to on phone widths (#421).
  {
    name: "04-spa-list-mobile.png",
    viewport: MOBILE,
    deviceScaleFactor: DSF,
    theme: "light",
    setup: "login",
    spa: true,
    path: "/admin-react/fintech/account/",
  },
  // 05 — Detail view (light): readonly fieldsets, FK chips, per-object
  // history + edit + delete chrome.
  {
    name: "05-spa-detail.png",
    viewport: DESKTOP,
    deviceScaleFactor: DSF,
    theme: "light",
    setup: "login",
    spa: true,
    path: "/admin-react/fintech/account/1/",
  },
  // 06 — Raw registry API JSON. The "machine readable" pitch — same
  // wire format powers the SPA, the docs, and the MCP layer.
  {
    name: "06-registry-api-json.png",
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: DSF,
    theme: "light",
    setup: "login",
    spa: false,
    path: "/admin-react/api/v1/registry/",
  },
  // 07 — List view in DARK. Same model as #03, different theme. Sells
  // the dark mode support visually for landing-page scanners.
  {
    name: "07-spa-list-dark.png",
    viewport: DESKTOP,
    deviceScaleFactor: DSF,
    theme: "dark",
    setup: "login",
    spa: true,
    path: "/admin-react/fintech/transaction/",
  },
  // 08 — Detail view in DARK. Pairs with #05 to show the full theme
  // coverage (registry, list, detail).
  {
    name: "08-spa-detail-dark.png",
    viewport: DESKTOP,
    deviceScaleFactor: DSF,
    theme: "dark",
    setup: "login",
    spa: true,
    path: "/admin-react/fintech/account/1/",
  },
  // 09 — Mobile detail (light): the responsive card / fieldset stack
  // on phone widths.
  {
    name: "09-spa-detail-mobile.png",
    viewport: MOBILE,
    deviceScaleFactor: DSF,
    theme: "light",
    setup: "login",
    spa: true,
    path: "/admin-react/fintech/account/1/",
  },
];

async function login(context) {
  const page = await context.newPage();
  await page.goto(`${BASE}/admin/legacy/login/?next=/admin/legacy/`, {
    waitUntil: "domcontentloaded",
  });
  await page.waitForSelector("#id_username", { timeout: 10000 });
  await page.fill("#id_username", USER);
  await page.fill("#id_password", PASS);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.endsWith("/login/"), {
      timeout: 10000,
    }),
    page.click('input[type="submit"]'),
  ]);
  await page.close();
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  let failed = 0;
  for (const c of captures) {
    const context = await browser.newContext({
      viewport: c.viewport,
      deviceScaleFactor: c.deviceScaleFactor,
    });
    if (c.theme === "dark") {
      await context.addCookies([darkCookie()]);
      await context.addInitScript(DARK_INIT_SCRIPT);
    }
    if (c.setup === "login") {
      await login(context);
    }
    const page = await context.newPage();
    try {
      await page.goto(`${BASE}${c.path}`, { waitUntil: "networkidle" });
      // The SPA fetches the registry / list / detail after first paint;
      // give React a beat to render past network-idle before capturing.
      if (c.spa) {
        await page.waitForTimeout(1500);
      }
      await page.screenshot({ path: resolve(OUT, c.name), fullPage: false });
      console.log(`✓ ${c.name}`);
    } catch (err) {
      console.error(`✗ ${c.name}: ${err.message}`);
      failed += 1;
    } finally {
      await context.close();
    }
  }
  await browser.close();
  if (failed > 0) {
    console.error(`${failed} capture(s) failed.`);
    process.exit(1);
  }
  console.log(`\nWrote ${captures.length} screenshots to ${OUT}/`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
