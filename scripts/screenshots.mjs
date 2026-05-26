#!/usr/bin/env node
//
// scripts/screenshots.mjs — Playwright capture for docs/screenshots/.
//
// Boots a long-running Django dev server elsewhere; this script only
// captures URLs. The caller (scripts/screenshots.sh) is responsible
// for the dev server lifecycle.

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const BASE = process.env.DAR_BASE_URL || "http://127.0.0.1:8765";
const OUT = resolve(process.cwd(), "docs/screenshots");
const USER = process.env.DAR_USER || "screenshots";
const PASS = process.env.DAR_PASS || "screenshots-only-do-not-reuse";

mkdirSync(OUT, { recursive: true });

const captures = [
  {
    name: "01-admin-login.png",
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    setup: null,
    path: "/admin/legacy/login/?next=/admin/legacy/",
  },
  {
    name: "02-admin-index.png",
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    setup: "login",
    path: "/admin/legacy/",
  },
  {
    name: "03-admin-library-list.png",
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    setup: "login",
    path: "/admin/legacy/library/author/",
  },
  {
    name: "04-admin-library-list-mobile.png",
    viewport: { width: 375, height: 812 },
    deviceScaleFactor: 3,
    setup: "login",
    path: "/admin/legacy/library/author/",
  },
  {
    name: "05-admin-library-detail.png",
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    setup: "login",
    path: "/admin/legacy/library/author/1/change/",
  },
  {
    name: "06-registry-api-json.png",
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 2,
    setup: "login",
    path: "/admin-react/api/v1/registry/",
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
    if (c.setup === "login") {
      await login(context);
    }
    const page = await context.newPage();
    try {
      await page.goto(`${BASE}${c.path}`, { waitUntil: "networkidle" });
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
