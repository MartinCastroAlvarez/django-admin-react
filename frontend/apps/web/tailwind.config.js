/** @type {import("tailwindcss").Config} */
export default {
  // Class strategy: dark mode is on when <html> has the `dark` class
  // (toggled by src/theme.ts from the user's saved preference). The
  // actual recolouring is done by a scoped `.dark` utility remap in
  // index.css so existing light-utility components go dark without
  // per-component `dark:` variants.
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
    // Scan EVERY workspace package, not a hand-maintained list. When a
    // component is extracted into a new package (e.g. @dar/sidebar,
    // @dar/settings), its Tailwind classes must still be generated — a
    // missing glob silently purges them and the component renders
    // unstyled (the sidebar-overlap regression). A wildcard prevents
    // that class of bug from recurring.
    '../../packages/*/src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
    },
  },
  plugins: [],
};
