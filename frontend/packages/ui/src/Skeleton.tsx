// Generic shimmer placeholder for loading states. Model-agnostic: the
// caller sizes/shapes it with `className` (width, height, rounding) and
// composes blocks/rows. Used while a foreground fetch is in flight so
// the UI signals "loading" instead of sitting on stale (or empty)
// content. Decorative — hidden from the accessibility tree; callers own
// the `aria-busy` / status announcement on the surrounding region.

export interface SkeletonProps {
  /** Tailwind classes that size/shape the block. Defaults to a text-line bar. */
  className?: string;
}

export function Skeleton({ className = 'h-4 w-full' }: SkeletonProps) {
  return (
    <span aria-hidden="true" className={`block animate-pulse rounded bg-gray-200 ${className}`} />
  );
}
