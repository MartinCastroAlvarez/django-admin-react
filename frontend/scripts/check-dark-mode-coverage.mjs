#!/usr/bin/env node
// Dark-mode coverage guard (#433).
//
// Dark mode is implemented by *remapping* hardcoded light Tailwind
// utilities to dark values under `.dark` in apps/web/src/index.css. That
// list is hand-maintained, so a component using a light color utility
// with no `.dark` remap silently renders light-on-dark (a white block /
// unreadable text on the dark surface). This guard fails the lint gate
// when that happens, so the regression is caught at merge time instead of
// in the pilot. (The proper fix — semantic CSS-variable tokens — is the
// larger follow-up tracked in #433; this stops new regressions now.)

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const INDEX_CSS = join(ROOT, 'apps/web/src/index.css');

// Light utilities that read wrong on the dark surface and therefore need a
// `.dark` remap. Mid/dark shades (bg-*-{300+}, text-*-{<=400}) are
// dark-safe and excluded; so is the always-dark sidebar chrome
// (bg-gray-{700,800,900}, text-gray-{100..400}). A leading `(?<![\w:-])`
// skips variant-prefixed forms (`hover:`, `dark:`, `sm:`, …) — those are
// handled separately (the hover variants have their own `.dark` remaps).
const COLORS = '(?:gray|slate|zinc|neutral|amber|red|green|blue|indigo|yellow|orange|sky|emerald|teal|purple|pink|rose)';
const PATTERNS = [
  new RegExp(`(?<![\\w:-])(bg-white)(?![\\w-])`, 'g'),
  new RegExp(`(?<![\\w:-])(bg-${COLORS}-(?:50|100|200))(?![\\w-])`, 'g'),
  new RegExp(`(?<![\\w:-])(text-(?:gray|slate|zinc|neutral)-(?:500|600|700|800|900))(?![\\w-])`, 'g'),
  new RegExp(`(?<![\\w:-])(text-(?:amber|red|green|blue|indigo|orange)-(?:600|700|800))(?![\\w-])`, 'g'),
  new RegExp(`(?<![\\w:-])(border-(?:gray|slate|zinc|neutral)-(?:100|200|300))(?![\\w-])`, 'g'),
];

function remappedUtilities() {
  const css = readFileSync(INDEX_CSS, 'utf8');
  const set = new Set();
  // `.dark .<class>` selectors — the class may contain CSS-escaped chars
  // (e.g. `hover\:bg-gray-100`). Unescape so it matches the source token.
  const re = /\.dark\s+\.((?:[\w-]|\\.)+)/g;
  let m;
  while ((m = re.exec(css))) set.add(m[1].replace(/\\(.)/g, '$1'));
  return set;
}

function collectFiles(dir, out = []) {
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return out;
  }
  for (const name of entries) {
    if (name === 'node_modules' || name === 'dist') continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) collectFiles(p, out);
    else if (/\.(tsx?|jsx?)$/.test(name) && !/\.(test|spec)\./.test(name)) out.push(p);
  }
  return out;
}

const remapped = remappedUtilities();
const files = [join(ROOT, 'packages'), join(ROOT, 'apps/web/src')].flatMap((r) =>
  collectFiles(r),
);

const seen = new Set();
const violations = [];
for (const file of files) {
  const src = readFileSync(file, 'utf8');
  for (const re of PATTERNS) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(src))) {
      const util = m[1];
      if (remapped.has(util)) continue;
      const rel = file.replace(`${ROOT}/`, '');
      const key = `${rel}::${util}`;
      if (seen.has(key)) continue;
      seen.add(key);
      violations.push({ file: rel, util });
    }
  }
}

if (violations.length) {
  console.error(
    '\n✖ Dark-mode coverage (#433): light color utilities used with no `.dark` remap',
  );
  console.error('  in apps/web/src/index.css — these render light-on-dark:\n');
  for (const v of violations.sort((a, b) => a.file.localeCompare(b.file))) {
    console.error(`    ${v.file}  →  ${v.util}`);
  }
  console.error(
    '\n  Fix: add a `.dark .<utility> { … }` remap in index.css, or use a' +
      '\n  dark-safe utility / the --dar-primary token.\n',
  );
  process.exit(1);
}
console.log('✓ dark-mode coverage: every light color utility is remapped under .dark');
