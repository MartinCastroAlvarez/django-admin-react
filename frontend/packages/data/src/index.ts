// @dar/data — the only consumer of @dar/api.
//
// Page packages (@dar/list, @dar/details, @dar/models, @dar/web)
// import EVERYTHING through this surface. The eslint boundary rule
// in `frontend/.eslintrc.cjs` enforces that other packages may not
// `import "@dar/api"`.

export { ApiProvider, useApiClient } from './api-context';
export type { ApiProviderProps } from './api-context';
export { ApiClient, ApiError } from '@dar/api';
export type {
  ApiClientConfig,
  ColumnDescriptor,
  CreatePayload,
  CreateResponse,
  DetailResponse,
  FieldChoice,
  FieldDescriptor,
  FieldErrorEnvelope,
  FieldType,
  FieldValue,
  FieldsetDescriptor,
  ForeignKeyValue,
  ListResponse,
  ListRow,
  Permissions,
  RegistryAppEntry,
  RegistryModelEntry,
  RegistryResponse,
  RegistryUser,
  UpdatePayload,
} from '@dar/api';

export { RegistryProvider, useRegistry } from './registry-context';
export type { RegistryProviderProps, RegistryState } from './registry-context';

export { useList } from './list-context';
export type { ListState } from './list-context';

export { useDetail } from './detail-context';
export type { DetailState } from './detail-context';

export { createObject, updateObject, deleteObject } from './mutations';
export type { CreateArgs, UpdateArgs, DeleteArgs } from './mutations';

export { renderValue } from './format';

export { useSwrCache } from './swr-cache';
export type { SwrState, UseSwrCacheArgs } from './swr-cache';
