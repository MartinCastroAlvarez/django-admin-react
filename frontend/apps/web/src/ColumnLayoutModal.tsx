// ColumnLayoutModal (#586) — the list-page "Layout" / Customize modal
// for showing, hiding, and reordering columns.
//
// Replaces the v1.x hand-rolled HTML5 drag-and-drop (which had no
// keyboard a11y, no drop-target indicator, no announcements, and
// inconsistent commit behaviour) with @dnd-kit. The keyboard sensor
// alone makes this the first reorder UI in the SPA that works without
// a pointer:
//
//   1. Tab onto a non-locked row's drag handle.
//   2. Press Space to "pick up" — the row lifts; @dnd-kit announces
//      "Picked up X. Use arrow keys to move."
//   3. Arrow up / down to move; @dnd-kit announces each step.
//   4. Space to drop, or Escape to cancel and snap back.
//
// The primary-key (pk) column is locked above the sortable group:
// rendered without a handle, with a small lock icon and a title=
// tooltip, so the operator can see WHY it's not draggable.

import { GripVertical, Lock, RotateCcw } from 'lucide-react';
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { Checkbox, Modal, ResetButton } from '@dar/ui';

export interface ColumnLayoutDescriptor {
  name: string;
  label: string;
}

export interface ColumnLayoutModalProps {
  onClose: () => void;
  /** Columns in their current display order (pk first if present). */
  orderedDescriptors: readonly ColumnLayoutDescriptor[];
  /** Tag: which column is the (locked) primary key. */
  isPk: (name: string) => boolean;
  /** Which columns are currently hidden (the pk is never in here). */
  hiddenCols: ReadonlySet<string>;
  /** Count of currently-visible columns — the last visible non-pk
   *  column can't be hidden (the list would have no data column). */
  visibleColumnCount: number;
  /** Toggle a column's visibility. The list page owns the persistence. */
  onToggle: (name: string, visibleCount: number) => void;
  /** Persist the new ordering of the non-pk columns. */
  onReorder: (nextNonPkOrder: string[]) => void;
  /** Is the column layout currently customised vs the registered
   *  `ModelAdmin` default? Drives the Reset button's enabled state. */
  isCustomised: boolean;
  /** Discard any per-user reorder + hide preferences and fall back to
   *  the registered `ModelAdmin` default (#590). */
  onReset: () => void;
}

// Default export to make `React.lazy(() => import('./ColumnLayoutModal'))`
// a one-liner at the call site. Named export kept for tests + named
// imports that don't want the lazy split.
export default function ColumnLayoutModal({
  onClose,
  orderedDescriptors,
  isPk,
  hiddenCols,
  visibleColumnCount,
  onToggle,
  onReorder,
  isCustomised,
  onReset,
}: ColumnLayoutModalProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      // Small distance threshold so a click on the handle (e.g. to
      // focus it for keyboard mode) doesn't start a drag.
      activationConstraint: { distance: 4 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const pkRow = orderedDescriptors.find((c) => isPk(c.name));
  const nonPk = orderedDescriptors.filter((c) => !isPk(c.name));
  const nonPkIds = nonPk.map((c) => c.name);

  function handleDragEnd(event: DragEndEvent): void {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const from = nonPkIds.indexOf(String(active.id));
    const to = nonPkIds.indexOf(String(over.id));
    if (from === -1 || to === -1) return;
    onReorder(arrayMove(nonPkIds, from, to));
  }

  return (
    <Modal title="Layout" onClose={onClose}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs text-gray-500">
          Toggle to show or hide. Drag the handle to reorder (keyboard:
          Tab to a handle, then Space + arrow keys + Space to drop).
        </p>
        {/* Reset (#590): discards the per-user layout and falls back
            to the registered ModelAdmin default. Disabled when the
            layout is already at default — the tooltip explains why
            so the affordance stays discoverable. */}
        <ResetButton
          isDirty={isCustomised}
          onReset={onReset}
          label="Reset"
          disabledHint="Layout is already at default"
          icon={<RotateCcw className="h-4 w-4" aria-hidden />}
          title="Reset to the default layout"
        />
      </div>
      <ul className="space-y-1">
        {pkRow ? (
          <LockedRow
            label={pkRow.label}
            tooltip="The primary-key column always shows first."
          />
        ) : null}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={nonPkIds} strategy={verticalListSortingStrategy}>
            {nonPk.map((c) => {
              const visible = !hiddenCols.has(c.name);
              // The last visible non-pk column can't be hidden — its
              // checkbox is disabled so the list never has zero data
              // columns. (The pk is always visible regardless.)
              const lastVisible = visible && visibleColumnCount <= 1;
              return (
                <SortableRow
                  key={c.name}
                  id={c.name}
                  label={c.label}
                  visible={visible}
                  disabled={lastVisible}
                  onToggle={() => onToggle(c.name, visibleColumnCount)}
                />
              );
            })}
          </SortableContext>
        </DndContext>
      </ul>
    </Modal>
  );
}

function LockedRow({ label, tooltip }: { label: string; tooltip: string }) {
  return (
    <li
      // Visually distinguished from the sortable rows: a faint gray
      // surface + a lock icon in the handle slot. No drag listeners.
      className="flex items-center gap-2 rounded border border-transparent bg-gray-50 px-1 py-1"
      aria-label={`${label} (locked first)`}
    >
      <span
        className="inline-flex h-4 w-4 shrink-0 items-center justify-center text-gray-400"
        title={tooltip}
      >
        <Lock className="h-3.5 w-3.5" aria-hidden />
      </span>
      <label className="flex flex-1 items-center gap-2 text-sm text-gray-500">
        {/* The pk is always visible; show a checked + disabled box for
            shape parity with the sortable rows below. */}
        <Checkbox checked disabled onChange={() => {}} />
        <span title={tooltip}>{label}</span>
      </label>
    </li>
  );
}

interface SortableRowProps {
  id: string;
  label: string;
  visible: boolean;
  /** Hide the checkbox's interactive state when this is the last
   *  visible column (can't be hidden without breaking the table). */
  disabled: boolean;
  onToggle: () => void;
}

function SortableRow({ id, label, visible, disabled, onToggle }: SortableRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={[
        'flex items-center gap-2 rounded border px-1 py-1',
        isDragging
          ? 'z-10 border-blue-300 bg-white shadow-lg'
          : 'border-transparent hover:border-gray-200',
      ].join(' ')}
    >
      {/* Drag handle — a real <button> so it's focusable + Enter/Space
          activate keyboard pickup. setActivatorNodeRef + listeners make
          this the drag-initiating element (not the whole row). */}
      <button
        ref={setActivatorNodeRef}
        type="button"
        aria-label={`Reorder ${label}`}
        title={`Drag to reorder ${label}`}
        className="cursor-grab touch-none rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 active:cursor-grabbing"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4 shrink-0" aria-hidden />
      </button>
      <label
        className={`flex flex-1 items-center gap-2 text-sm ${
          disabled ? 'text-gray-400' : 'text-gray-800'
        }`}
      >
        <Checkbox checked={visible} disabled={disabled} onChange={onToggle} />
        {label}
      </label>
    </li>
  );
}
