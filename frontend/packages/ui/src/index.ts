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

export { EmptyState } from './EmptyState';
export type { EmptyStateProps } from './EmptyState';

export { Table } from './Table';
export type { TableColumn, TableProps } from './Table';

export { Input } from './Input';
export type { InputProps } from './Input';
