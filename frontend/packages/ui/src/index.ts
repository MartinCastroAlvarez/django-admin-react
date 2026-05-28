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
