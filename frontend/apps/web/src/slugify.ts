// Slugify — approximates Django's `slugify` for the SPA's
// prepopulated_fields behaviour (#245): strip accents, lowercase, drop
// non-word characters, and collapse runs of whitespace/hyphens into a
// single hyphen, with no leading/trailing hyphen.
export function slugify(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/[\s-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
