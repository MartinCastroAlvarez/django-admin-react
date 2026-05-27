// Workspace-wide ESLint flat config (ESLint v9).
//
// Replaces the legacy `.eslintrc.cjs` (which v9 ignored — see #261, the
// gate was silently non-functional). Layers:
//   - `@eslint/js` recommended (core correctness),
//   - typescript-eslint recommended (TS-aware rules),
//   - eslint-plugin-react-hooks (rules-of-hooks + exhaustive-deps),
//   - the `@dar/api` import-boundary rule (CLAUDE.md §7),
//   - eslint-config-prettier last (formatting is Prettier's job).

import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: [
      '**/dist/**',
      '**/node_modules/**',
      '**/*.config.{js,cjs,mjs,ts}',
      'vitest.setup.ts',
      '.eslintrc.cjs',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // `Any` is used deliberately at wire boundaries (parsed JSON,
      // Django-shaped signatures) — mirrors the Python side keeping
      // `Any`. Tightening the tractable cases is tracked separately.
      '@typescript-eslint/no-explicit-any': 'off',
      // Align with tsconfig's `noUnusedParameters` underscore convention.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
    },
  },
  // Data-flow boundary (CLAUDE.md §7): UI packages import only @dar/data
  // (+ @dar/ui / siblings) — never @dar/api. @dar/data is the sole legal
  // consumer of @dar/api, so it is exempt.
  {
    files: [
      'apps/**/*.{ts,tsx}',
      'packages/list/**/*.{ts,tsx}',
      'packages/details/**/*.{ts,tsx}',
      'packages/form/**/*.{ts,tsx}',
      'packages/history/**/*.{ts,tsx}',
      'packages/models/**/*.{ts,tsx}',
      'packages/search/**/*.{ts,tsx}',
      'packages/sidebar/**/*.{ts,tsx}',
      'packages/settings/**/*.{ts,tsx}',
      'packages/ui/**/*.{ts,tsx}',
    ],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@dar/api',
              message:
                'Page packages MUST NOT import @dar/api directly — go through @dar/data instead. See CLAUDE.md §7.',
            },
          ],
          patterns: [
            {
              group: ['@dar/api/*'],
              message:
                'Page packages MUST NOT import @dar/api submodules — go through @dar/data instead.',
            },
          ],
        },
      ],
    },
  },
  // Node tooling scripts (e.g. the dark-mode coverage guard) run under
  // Node, not the browser — give them Node globals so `process`/`console`
  // aren't flagged as undefined.
  {
    files: ['scripts/**/*.{js,mjs}'],
    languageOptions: { globals: { ...globals.node } },
  },
  prettier,
);
