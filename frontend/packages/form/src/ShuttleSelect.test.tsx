// ShuttleSelect — locks the two-pane render + selection behaviour
// (#627): which items live in which pane, click-to-move, search
// filter per pane, "Choose all" / "Remove all" buttons, order
// preservation when moving items in and out of Chosen.
import '@testing-library/jest-dom/vitest';

import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { FieldChoice } from '@dar/data';

import { ShuttleSelect } from './ShuttleSelect';

const CHOICES: FieldChoice[] = [
  { value: 1, label: 'Engineering' },
  { value: 2, label: 'Marketing' },
  { value: 3, label: 'Finance' },
  { value: 4, label: 'Operations' },
];

function paneByTitle(title: string): HTMLElement {
  // Each Pane renders an `<ul role="listbox" aria-labelledby="...">`
  // pointing to a `<div>` carrying the title text.
  return screen.getByRole('listbox', { name: title });
}

describe('ShuttleSelect (#627)', () => {
  it('renders two panes: Available (unselected) + Chosen (selected)', () => {
    render(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[2]}
        orientation="h"
        label="departments"
        onChange={() => {}}
      />,
    );
    const avail = paneByTitle('Available departments');
    const chosen = paneByTitle('Chosen departments');
    expect(within(avail).getByText('Engineering')).toBeInTheDocument();
    expect(within(avail).getByText('Finance')).toBeInTheDocument();
    expect(within(avail).getByText('Operations')).toBeInTheDocument();
    expect(within(avail).queryByText('Marketing')).not.toBeInTheDocument();
    expect(within(chosen).getByText('Marketing')).toBeInTheDocument();
  });

  it('clicking an Available item appends it to Chosen (preserves order)', () => {
    const onChange = vi.fn();
    render(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[2]}
        orientation="h"
        label="departments"
        onChange={onChange}
      />,
    );
    fireEvent.click(within(paneByTitle('Available departments')).getByText('Finance'));
    expect(onChange).toHaveBeenCalledWith([2, 3]);
  });

  it('clicking a Chosen item removes it', () => {
    const onChange = vi.fn();
    render(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[1, 2, 3]}
        orientation="h"
        label="departments"
        onChange={onChange}
      />,
    );
    fireEvent.click(within(paneByTitle('Chosen departments')).getByText('Marketing'));
    expect(onChange).toHaveBeenCalledWith([1, 3]);
  });

  it('search filters items within a pane (case-insensitive)', () => {
    render(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[]}
        orientation="h"
        label="departments"
        onChange={() => {}}
      />,
    );
    const availSearch = screen.getByLabelText('Filter Available departments');
    fireEvent.change(availSearch, { target: { value: 'fin' } });
    const avail = paneByTitle('Available departments');
    expect(within(avail).getByText('Finance')).toBeInTheDocument();
    expect(within(avail).queryByText('Engineering')).not.toBeInTheDocument();
  });

  it('Choose all moves every FILTERED Available item to Chosen', () => {
    const onChange = vi.fn();
    render(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[]}
        orientation="h"
        label="departments"
        onChange={onChange}
      />,
    );
    // Narrow the visible set to Engineering + Operations (anything with `o`).
    const availSearch = screen.getByLabelText('Filter Available departments');
    fireEvent.change(availSearch, { target: { value: 'O' } });
    fireEvent.click(screen.getByRole('button', { name: 'Choose all' }));
    // Marketing matches "O" too (mArketing has no O — but "ratiOns" /
    // "engineering" / "operatiOns" do). Be explicit.
    const want = CHOICES.filter((c) => c.label.toLowerCase().includes('o')).map((c) => c.value);
    expect(onChange).toHaveBeenCalledWith(want);
  });

  it('Remove all clears every FILTERED Chosen item', () => {
    const onChange = vi.fn();
    render(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[1, 2, 3, 4]}
        orientation="h"
        label="departments"
        onChange={onChange}
      />,
    );
    // Filter Chosen by "ing" — matches Engineering + Marketing only
    // (Finance + Operations have no "ing"). Removes those two; the
    // surviving Chosen set is [3, 4] in order.
    const chosenSearch = screen.getByLabelText('Filter Chosen departments');
    fireEvent.change(chosenSearch, { target: { value: 'ing' } });
    fireEvent.click(screen.getByRole('button', { name: 'Remove all' }));
    expect(onChange).toHaveBeenCalledWith([3, 4]);
  });

  it('horizontal vs vertical orientation toggles the grid layout', () => {
    const { container, rerender } = render(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[]}
        orientation="h"
        label="departments"
        onChange={() => {}}
      />,
    );
    const hRoot = container.firstChild as HTMLElement;
    expect(hRoot.className).toContain('sm:grid-cols-[1fr_1fr]');
    rerender(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[]}
        orientation="v"
        label="departments"
        onChange={() => {}}
      />,
    );
    const vRoot = container.firstChild as HTMLElement;
    expect(vRoot.className).not.toContain('sm:grid-cols-[1fr_1fr]');
  });

  it('round-trips numeric pks as numbers (not strings) on emit', () => {
    const onChange = vi.fn();
    render(
      <ShuttleSelect
        id="t"
        choices={CHOICES}
        value={[1]}
        orientation="h"
        label="departments"
        onChange={onChange}
      />,
    );
    fireEvent.click(within(paneByTitle('Available departments')).getByText('Finance'));
    const [emitted] = onChange.mock.calls[0] as [Array<string | number>];
    expect(emitted).toEqual([1, 3]);
    for (const v of emitted) expect(typeof v).toBe('number');
  });
});
