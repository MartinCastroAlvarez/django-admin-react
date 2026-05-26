// TypeScript types for the v1 API wire contract.
//
// Mirrors `docs/api-contract.md`. Keep this file in lockstep with the
// backend; changes here without the matching contract change are a
// review blocker (see CLAUDE.md §2 rule 1).

export type FieldType =
  | 'string'
  | 'text'
  | 'email'
  | 'url'
  | 'slug'
  | 'integer'
  | 'float'
  | 'decimal'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'time'
  | 'uuid'
  | 'choice'
  | 'foreignkey'
  | 'unsupported';

export interface Permissions {
  view: boolean;
  add: boolean;
  change: boolean;
  delete: boolean;
}

export interface RegistryUser {
  id: number;
  username: string;
  is_staff: boolean;
  is_superuser: boolean;
  display_name: string;
}

export interface RegistryModelEntry {
  app_label: string;
  model_name: string;
  object_name: string;
  verbose_name: string;
  verbose_name_plural: string;
  permissions: Permissions;
}

export interface RegistryAppEntry {
  app_label: string;
  verbose_name: string;
  models: RegistryModelEntry[];
}

export interface RegistryResponse {
  mount: string;
  user: RegistryUser;
  apps: RegistryAppEntry[];
}

export interface ColumnDescriptor {
  name: string;
  label: string;
  sortable: boolean;
}

export interface ForeignKeyValue {
  id: number | string;
  label: string;
}

export type FieldValue = string | number | boolean | null | ForeignKeyValue | ForeignKeyValue[];

export interface ListRow {
  pk: number | string;
  label: string;
  fields: Record<string, FieldValue>;
}

export interface ListResponse {
  app_label: string;
  model_name: string;
  permissions: Permissions;
  columns: ColumnDescriptor[];
  search_fields: string[];
  page: number;
  page_size: number;
  total: number;
  results: ListRow[];
}

export interface FieldChoice {
  value: string | number | boolean | null;
  label: string;
}

export interface FieldDescriptor {
  type: FieldType;
  label: string;
  required: boolean;
  readonly: boolean;
  help_text: string;
  value: FieldValue;
  max_length?: number;
  decimal_places?: number;
  choices?: FieldChoice[];
  to?: { app_label: string; model_name: string };
}

export interface FieldsetDescriptor {
  title: string | null;
  fields: string[];
}

export interface DetailResponse {
  app_label: string;
  model_name: string;
  pk: number | string;
  label: string;
  permissions: Permissions;
  fieldsets: FieldsetDescriptor[];
  fields: Record<string, FieldDescriptor>;
}

export interface CreateResponse {
  pk: number | string;
  label: string;
  redirect: string;
}

export interface FieldErrorEnvelope {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string[]>;
  };
}

/**
 * Wire-shape for a single field value on POST / PATCH.
 *
 * Contract §5.1: FK values are sent as the bare related-pk
 * (``number | string``). The backend ALSO accepts the read
 * envelope ``{id, label}`` for ergonomics, but clients should send
 * the bare pk to stay on the documented contract.
 */
export type WriteValue = string | number | boolean | null;

export type CreatePayload = Record<string, WriteValue>;
export type UpdatePayload = Record<string, WriteValue>;
