// ColumnLayoutModal (#586) — the list-page "Layout" / Customize modal
// for showing, hiding, REORDERING, and LOCKING (freezing) columns.
//
// Built on @dnd-kit with full keyboard a11y (#586 round 1). Round 2
// adds the lock / freeze feature:
//
//   - The pk column is permanently locked (visible lock icon, no
//     handle, no checkbox toggle).
//   - Non-pk columns get a lock button alongside their drag handle.
//   - Locked columns MUST form a contiguous prefix starting from the
//     pk. Locking the N-th column auto-locks every column above it;
//     unlocking the N-th column auto-unlocks every column below it
//     (since gaps would break the "all-leading sticky cells form one
//     visually-contiguous frozen block" contract on the Table side).
//   - Locked columns have their drag handle disabled — the operator
//     unlocks them first if they want to move them.
//
// Mobile/tablet (RecordCardList stacked layout) renders this modal
// the same way but the lock flag is a no-op at render time — the
// stacked layout has no horizontal scroll and so nothing to freeze.

import { GripVertical, Lock, RotateCcw, Unlock } from 'lucide-react';
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
  /** Which non-pk columns the user has locked / frozen. The pk is
   *  implicitly always locked and is never stored in this set. */
  lockedCols: ReadonlySet<string>;
  /** Count of currently-visible columns — the last visible non-pk
   *  column can't be hidden (the list would have no data column). */
  visibleColumnCount: number;
  /** Toggle a column's visibility. The list page owns the persistence. */
  onToggle: (name: string, visibleCount: number) => void;
  /** Persist the new ordering of the non-pk columns. */
  onReorder: (nextNonPkOrder: string[]) => void;
  /** Persist the new locked-set (after applying the contiguous-prefix
   *  invariant). The modal computes the set; the page just stores it. */
  onSetLocked: (next: Set<string>) => void;
  /** Is the column layout currently customised vs the registered
   *  `ModelAdmin` default? Drives the Reset button's enabled state. */
  isCustomised: boolean;
  /** Discard every per-user reorder / hide / lock preference and fall
   *  back to the registered `ModelAdmin` default (#590, #586). */
  onReset: () => void;
}

// Contiguous-prefix invariant helpers. Pure functions, exported for
// tests + readability — the modal renders fine without them being a
// separate module but the test file imports both.
//
// `lockThrough(orderedNonPkNames, name)` returns the new locked set
// after the user locks `name`: every non-pk name from index 0 to
// indexOf(name) inclusive becomes locked.
export function lockThrough(
  orderedNonPkNames: readonly string[],
  name: string,
): Set<string> {
  const idx = orderedNonPkNames.indexOf(name);
  if (idx === -1) return new Set();
  return new Set(orderedNonPkNames.slice(0, idx + 1));
}

// `unlockFrom(orderedNonPkNames, locked, name)` returns the new locked
// set after the user unlocks `name`: every non-pk name from
// indexOf(name) to the end becomes unlocked (the entries above
// `name` keep their previous lock state, in case the user had
// previously locked through a column further down and we're peeling
// the tail off).
export function unlockFrom(
  orderedNonPkNames: readonly string[],
  locked: ReadonlySet<string>,
  name: string,
): Set<string> {
  const idx = orderedNonPkNames.indexOf(name);
  if (idx === -1) return new Set(locked);
  const next = new Set<string>();
  for (let i = 0; i < idx; i += 1) {
    const n = orderedNonPkNames[i];
    if (n !== undefined && locked.has(n)) next.add(n);
  }
  return next;
}

export default function ColumnLayoutModal({
  onClose,
  orderedDescriptors,
  isPk,
  hiddenCols,
  lockedCols,
  visibleColumnCount,
  onToggle,
  onReorder,
  onSetLocked,
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
  const nonPkNames = nonPk.map((c) => c.name);
  // For DnD: only the UNLOCKED non-pk rows are sortable. Locked rows
  // are rendered above them with no drag listeners (matches the pk's
  // visual locked treatment).
  const sortableIds = nonPkNames.filter((n) => !lockedCols.has(n));

  function handleDragEnd(event: DragEndEvent): void {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    // Reorder operates on the FULL non-pk list (so unlocked-row drag
    // is positioned correctly against the locked prefix). Find the
    // active + over indexes in the full list and move there.
    const from = nonPkNames.indexOf(String(active.id));
    const to = nonPkNames.indexOf(String(over.id));
    if (from === -1 || to === -1) return;
    onReorder(arrayMove(nonPkNames, from, to));
  }

  // Lock / unlock handler builds the next locked set via the
  // contiguous-prefix invariant and hands it back to the page.
  function toggleLock(name: string): void {
    const next = lockedCols.has(name)
      ? unlockFrom(nonPkNames, lockedCols, name)
      : lockThrough(nonPkNames, name);
    onSetLocked(next);
  }

  return (
    <Modal title="Layout" onClose={onClose}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs text-gray-500">
          Toggle to show or hide. Lock to freeze a column to the left
          (frozen columns must be contiguous from the id). Drag the
          handle to reorder (keyboard: Tab to a handle, then Space +
          arrow keys + Space to drop).
        </p>
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
        {/* pk row — permanently locked, visible lock icon, no toggle. */}
        {pkRow ? (
          <LockedRow
            label={pkRow.label}
            tooltip="The primary-key column always shows first and is always frozen."
          />
        ) : null}

        {/* Locked non-pk rows above the sortable block. They sit
            visually between the pk and the sortable rows so the
            "contiguous frozen prefix" is also visually contiguous in
            the modal. No drag handle (would violate the locked rule
            anyway); unlock button is shown so the operator can free
            the column to make it draggable. */}
        {nonPk
          .filter((c) => lockedCols.has(c.name))
          .map((c) => {
            const visible = !hiddenCols.has(c.name);
            const lastVisible = visible && visibleColumnCount <= 1;
            return (
              <LockedRow
                key={c.name}
                label={c.label}
                tooltip="Locked. Unlock to drag or hide this column. Unlocking auto-unlocks every column to its right."
                checked={visible}
                checkboxDisabled={lastVisible}
                onToggle={() => onToggle(c.name, visibleColumnCount)}
                onUnlock={() => toggleLock(c.name)}
              />
            );
          })}

        {/* Sortable / unlocked non-pk rows. */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
            {nonPk
              .filter((c) => !lockedCols.has(c.name))
              .map((c) => {
                const visible = !hiddenCols.has(c.name);
                const lastVisible = visible && visibleColumnCount <= 1;
                return (
                  <SortableRow
                    key={c.name}
                    id={c.name}
                    label={c.label}
                    visible={visible}
                    disabled={lastVisible}
                    onToggle={() => onToggle(c.name, visibleColumnCount)}
                    onLock={() => toggleLock(c.name)}
                  />
                );
              })}
          </SortableContext>
        </DndContext>
      </ul>
    </Modal>
  );
}

interface LockedRowProps {
  label: string;
  tooltip: string;
  /** Visibility (shown when this is a non-pk lockable row). */
  checked?: boolean;
  checkboxDisabled?: boolean;
  onToggle?: () => void;
  /** Click to unlock — shown for non-pk locked rows so the operator
   *  can release them to drag / hide. Absent on the pk row, which is
   *  permanently locked by design. */
  onUnlock?: () => void;
}

function LockedRow({
  label,
  tooltip,
  checked,
  checkboxDisabled,
  onToggle,
  onUnlock,
}: LockedRowProps) {
  return (
    <li
      className="flex items-center gap-2 rounded border border-transparent bg-gray-50 px-1 py-1"
      aria-label={`${label} (locked)`}
    >
      {/* Non-interactive drag-handle placeholder so the locked row's
          checkbox + label align with the sortable rows below
          (which have a real handle button at the start). Matches the
          handle button's exact box: `p-0.5` padding + `h-4 w-4` icon
          = a 20×20 px slot. Rendered faded (text-gray-300) to signal
          "this column would be draggable if it weren't locked"
          without inviting clicks. aria-hidden so screen readers
          skip it. */}
      <span
        aria-hidden
        className="inline-flex h-5 w-5 shrink-0 cursor-not-allowed items-center justify-center p-0.5 text-gray-300"
      >
        <GripVertical className="h-4 w-4" aria-hidden />
      </span>
      {onUnlock ? (
        <button
          type="button"
          onClick={onUnlock}
          aria-label={`Unlock ${label}`}
          title={tooltip}
          className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-500 hover:bg-gray-200 hover:text-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Lock className="h-3.5 w-3.5" aria-hidden />
        </button>
      ) : (
        // The pk row — no button, just an icon, since unlocking is not
        // an option. `title` carries the explanation on hover.
        <span
          className="inline-flex h-5 w-5 shrink-0 items-center justify-center text-gray-400"
          title={tooltip}
        >
          <Lock className="h-3.5 w-3.5" aria-hidden />
        </span>
      )}
      <label
        className={`flex flex-1 items-center gap-2 text-sm ${
          checked === false ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        <Checkbox
          checked={checked ?? true}
          // pk row's checkbox is permanently checked + disabled; a
          // non-pk locked row's checkbox stays toggleable so the user
          // can still hide a locked column from the list (it'll
          // become un-rendered in the table but stay locked in the
          // modal until they explicitly unlock).
          disabled={onToggle === undefined || (checkboxDisabled ?? false)}
          onChange={onToggle ?? (() => {})}
        />
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
  /** Lock this column. Per the contiguous-prefix invariant, this
   *  also locks every column above it. */
  onLock: () => void;
}

function SortableRow({ id, label, visible, disabled, onToggle, onLock }: SortableRowProps) {
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
      {/* Lock toggle (#586): a separate button next to the handle so
          it's reachable without disturbing the drag. Tooltip explains
          the contiguous-prefix rule the click is about to enforce. */}
      <button
        type="button"
        onClick={onLock}
        aria-label={`Lock ${label}`}
        title="Lock to freeze this column to the left. Locked columns must be contiguous, so this also locks every column above it."
        className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <Unlock className="h-3.5 w-3.5" aria-hidden />
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
