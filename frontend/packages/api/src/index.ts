// @dar/api — typed REST client for django-admin-react.
//
// Public surface is the ApiClient class + the contract types.
// The single rule that other packages must follow: only @dar/data
// may `import` from here. Other packages import from @dar/data.
// See CLAUDE.md §7.

export { ApiClient, ApiError } from './client';
export type { ApiClientConfig } from './client';
export * from './contract';
