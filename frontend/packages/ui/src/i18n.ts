// SPA chrome i18n (#630). Minimum-viable message-catalog
// infrastructure so the package's own user-visible strings ("Add",
// "Search", "Save and continue editing", "Loading…") can be
// translated per the request's active locale — not just the
// API-payload `verbose_name` / `help_text` that already comes back
// translated when `LocaleMiddleware` is in the consumer's MIDDLEWARE
// stack.
//
// Design:
//   - Catalog keys are the English source string itself (gettext
//     convention). Removes a layer of indirection: refactoring a
//     string in JSX doesn't require a parallel catalog-key change.
//   - The active catalog is hydrated once at boot from the bundled
//     JSON files keyed by the `dar-language` meta tag the server
//     renders into `index.html`. Missing key → English source
//     string returned (graceful degradation; the operator sees
//     legible text even mid-migration as keys land).
//   - Synchronous API. The catalog is bundled into the SPA JS so
//     there's no fetch / loading state — the first paint already
//     carries the translations.
//
// Adding a new language: drop a JSON file under `src/i18n/` keyed
// by the locale code (matches Django's `LANGUAGE_CODE`), import it
// in `loadCatalog`, ship.

import enCatalog from './i18n/en.json';
import esCatalog from './i18n/es.json';
import ptCatalog from './i18n/pt.json';
import frCatalog from './i18n/fr.json';

type Catalog = Readonly<Record<string, string>>;

const CATALOGS: Readonly<Record<string, Catalog>> = {
  en: enCatalog,
  es: esCatalog,
  pt: ptCatalog,
  'pt-br': ptCatalog,
  fr: frCatalog,
};

let activeCatalog: Catalog = enCatalog;

/**
 * Hydrate the active catalog from the language code the server
 * rendered into ``<meta name="dar-language">``. Falls back to
 * English when the code is unknown / unset / malformed.
 *
 * Matching is exact first, then language-stem only (``es-AR`` →
 * tries ``es-AR``, then ``es``). The fallback chain is one level
 * deep — enough for ``language-region`` codes; over-engineered
 * regional-fallback chains aren't shipped here.
 */
export function loadCatalog(language: string | null | undefined): void {
  if (!language) return;
  const key = language.toLowerCase();
  const exact = CATALOGS[key];
  if (exact) {
    activeCatalog = exact;
    return;
  }
  const stem = key.split('-')[0];
  const fallback = stem ? CATALOGS[stem] : undefined;
  if (fallback) {
    activeCatalog = fallback;
  }
}

/**
 * Translate the English source string ``en`` to the active
 * catalog's translation, falling back to ``en`` itself when the
 * key isn't in the catalog.
 *
 * The English text is BOTH the source and the catalog key
 * (gettext convention). Editing the JSX-side string without
 * updating the catalog gracefully degrades to English; CI lint
 * can grep for keys present in catalogs but not in source to
 * surface dead translations.
 */
export function t(en: string): string {
  return activeCatalog[en] ?? en;
}

/** Test-only: swap the active catalog. Production code calls
 *  ``loadCatalog`` once at boot from ``main.tsx``. */
export function _setActiveCatalogForTests(catalog: Catalog): void {
  activeCatalog = catalog;
}

/** Test-only: read the currently active language's catalog. */
export function _activeCatalogForTests(): Catalog {
  return activeCatalog;
}
