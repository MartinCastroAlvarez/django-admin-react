// @dar/ui — generic, model-agnostic Tailwind primitives.
//
// Per CLAUDE.md §7, components here MUST NOT know about specific
// example models (Account, Book, etc.). They take typed props and
// render. Business-aware components live in @dar/list, @dar/details,
// or @dar/models.

export { Button } from './Button';
export type { ButtonProps, ButtonVariant } from './Button';

export { Card } from './Card';
export type { CardProps } from './Card';

export { Spinner } from './Spinner';
export type { SpinnerProps } from './Spinner';

export { Skeleton } from './Skeleton';
export type { SkeletonProps } from './Skeleton';

export { EmptyState } from './EmptyState';
export type { EmptyStateProps } from './EmptyState';

export { Table } from './Table';
export type { TableColumn, TableProps } from './Table';

export { RecordCardList } from './RecordCardList';
export type { RecordCardListProps } from './RecordCardList';

export { Pagination } from './Pagination';
export type { PaginationProps } from './Pagination';

export { useMediaQuery } from './useMediaQuery';

export { Input } from './Input';
export type { InputProps } from './Input';

export { Checkbox } from './Checkbox';
export type { CheckboxProps } from './Checkbox';

export { Modal } from './Modal';
export type { ModalProps } from './Modal';

export { Breadcrumb } from './Breadcrumb';
export type { BreadcrumbItem, BreadcrumbProps } from './Breadcrumb';

export { Popover } from './Popover';
export type { PopoverProps } from './Popover';

export { ResetButton } from './ResetButton';
export type { ResetButtonProps } from './ResetButton';

export { RefreshButton } from './RefreshButton';
export type { RefreshButtonProps } from './RefreshButton';

// SPA chrome i18n (#630). Every package can call `t(en)` to translate
// a user-visible English source string to the active locale's catalog
// entry, falling back to the English source when no entry exists.
// The active catalog is hydrated once at boot from
// `<meta name="dar-language">`; see `loadCatalog` in main.tsx.
export { t, loadCatalog } from './i18n';
