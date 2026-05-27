import { defineConfig } from 'vitest/config';

// Single workspace-wide vitest config. Tests live next to the code they
// cover (`*.test.ts(x)` beside the source). jsdom gives DOM globals so
// `@dar/data` (localStorage / window) and future `@testing-library/react`
// component tests run without per-file setup. See the QA tracker (#310).
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['packages/**/src/**/*.test.{ts,tsx}', 'apps/**/src/**/*.test.{ts,tsx}'],
  },
});
