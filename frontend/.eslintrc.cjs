// Workspace-wide ESLint config.
//
// The single most important rule is the package-boundary rule for
// `@dar/api`: only `@dar/data` may import it. Page packages
// (`@dar/web`, `@dar/list`, `@dar/details`, `@dar/models`) MUST go
// through `@dar/data` so the network layer can be swapped, mocked,
// or instrumented without touching UI code. See CLAUDE.md §7.

module.exports = {
  root: true,
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
  },
  overrides: [
    {
      // The boundary rule applies to every package EXCEPT @dar/data
      // (which is the only legal consumer of @dar/api) and @dar/api
      // itself (which obviously imports from its own subpaths).
      files: [
        "apps/**/*.{ts,tsx,js,jsx}",
        "packages/list/**/*.{ts,tsx,js,jsx}",
        "packages/details/**/*.{ts,tsx,js,jsx}",
        "packages/models/**/*.{ts,tsx,js,jsx}",
        "packages/sidebar/**/*.{ts,tsx,js,jsx}",
        "packages/settings/**/*.{ts,tsx,js,jsx}",
        "packages/ui/**/*.{ts,tsx,js,jsx}",
      ],
      rules: {
        "no-restricted-imports": [
          "error",
          {
            paths: [
              {
                name: "@dar/api",
                message:
                  "Page packages MUST NOT import @dar/api directly — go through @dar/data instead. See CLAUDE.md §7.",
              },
            ],
            patterns: [
              {
                group: ["@dar/api/*"],
                message:
                  "Page packages MUST NOT import @dar/api submodules — go through @dar/data instead.",
              },
            ],
          },
        ],
      },
    },
  ],
};
