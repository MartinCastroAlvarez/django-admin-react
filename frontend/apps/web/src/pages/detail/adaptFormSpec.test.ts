import { describe, expect, it } from 'vitest';

import type {
  DetailResponse,
  FormSpecField,
  FormSpecResponse,
  WidgetHint,
  WidgetKind,
} from '@dar/data';

import { detailFromFormSpec, formSpecFieldToDescriptor } from './adaptFormSpec';

function fsField(overrides: Partial<FormSpecField> = {}): FormSpecField {
  return {
    label: 'Name',
    help_text: '',
    required: true,
    readonly: false,
    type: 'string',
    widget: { kind: 'text', attrs: {} },
    initial: '',
    errors: [],
    ...overrides,
  };
}

describe('formSpecFieldToDescriptor (#659)', () => {
  it('maps the closed widget.kind enum onto the existing WidgetHint controls', () => {
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'password', attrs: {} } })).widget).toBe('password');
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'radio', attrs: {} } })).widget).toBe('radio');
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'raw-id', attrs: {} } })).widget).toBe('raw_id');
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'shuttle', attrs: {} } })).widget).toBe('shuttle_h');
  });

  it('leaves widget undefined for kinds the FieldType already implies (select/date/…)', () => {
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'select', attrs: {} } })).widget).toBeUndefined();
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'date', attrs: {} } })).widget).toBeUndefined();
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'text', attrs: {} } })).widget).toBeUndefined();
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'number', attrs: {} } })).widget).toBeUndefined();
  });

  it('maps the kinds that need a control FieldType would NOT pick (#664)', () => {
    const hintFor = (kind: WidgetKind): WidgetHint | undefined =>
      formSpecFieldToDescriptor(fsField({ widget: { kind, attrs: {} } })).widget;
    expect(hintFor('hidden')).toBe('hidden');
    expect(hintFor('split-datetime')).toBe('split_datetime');
    expect(hintFor('select-date')).toBe('select_date');
    expect(hintFor('checkbox-multiple')).toBe('checkbox_multiple');
    expect(hintFor('select-multiple')).toBe('select_multiple');
    expect(hintFor('autocomplete')).toBe('autocomplete');
    expect(hintFor('autocomplete-multiple')).toBe('autocomplete_multiple');
    expect(hintFor('file')).toBe('file');
  });

  it('maps EVERY declared WidgetKind to something sensible — no silent no-op (#664)', () => {
    // The full closed enum from the contract. If a kind is added to the
    // wire without a mapping, this list (and the exhaustive `KIND_TO_HINT`
    // record) must be updated — keeping the SPA honest about every kind.
    const ALL_KINDS: WidgetKind[] = [
      'text',
      'textarea',
      'number',
      'email',
      'url',
      'password',
      'hidden',
      'checkbox',
      'checkbox-multiple',
      'select',
      'select-multiple',
      'radio',
      'date',
      'datetime',
      'time',
      'split-datetime',
      'select-date',
      'file',
      'autocomplete',
      'autocomplete-multiple',
      'raw-id',
      'shuttle',
      'custom',
    ];
    // Kinds whose FieldType-derived control is already faithful → no hint.
    const NO_HINT = new Set<WidgetKind>([
      'text',
      'textarea',
      'number',
      'email',
      'url',
      'checkbox',
      'select',
      'date',
      'datetime',
      'time',
    ]);
    const VALID_HINTS = new Set<WidgetHint>([
      'radio',
      'raw_id',
      'password',
      'shuttle_h',
      'shuttle_v',
      'custom',
      'hidden',
      'split_datetime',
      'select_date',
      'checkbox_multiple',
      'select_multiple',
      'autocomplete',
      'autocomplete_multiple',
      'file',
      'unsupported_widget',
    ]);
    for (const kind of ALL_KINDS) {
      const hint = formSpecFieldToDescriptor(fsField({ widget: { kind, attrs: {} } })).widget;
      if (NO_HINT.has(kind)) {
        expect(hint, `${kind} should defer to FieldType`).toBeUndefined();
      } else {
        expect(hint, `${kind} must map to a real WidgetHint`).toBeDefined();
        expect(VALID_HINTS.has(hint as WidgetHint), `${kind} → ${hint}`).toBe(true);
      }
    }
  });

  it('passes the custom widget_class through so the SPA can dispatch a registered renderer', () => {
    const d = formSpecFieldToDescriptor(
      fsField({
        widget: { kind: 'custom', attrs: {}, widget_class: 'mypkg.widgets.MarkdownEditor' },
      }),
    );
    expect(d.widget).toBe('custom');
    expect(d.widget_class).toBe('mypkg.widgets.MarkdownEditor');
  });

  it('carries readonly through and uses `initial` as the descriptor value', () => {
    const d = formSpecFieldToDescriptor(fsField({ readonly: true, initial: 'editors' }));
    expect(d.readonly).toBe(true);
    expect(d.value).toBe('editors');
  });

  it('derives max_length from widget.attrs.maxlength when not set explicitly', () => {
    const d = formSpecFieldToDescriptor(fsField({ widget: { kind: 'text', attrs: { maxlength: 150 } } }));
    expect(d.max_length).toBe(150);
  });

  it('preserves the FK initial envelope shape ({id,label}) so EditForm derives the pk', () => {
    const d = formSpecFieldToDescriptor(
      fsField({ type: 'foreignkey', initial: { id: 7, label: 'Acme' }, to: { app_label: 'a', model_name: 'b' } }),
    );
    expect(d.value).toEqual({ id: 7, label: 'Acme' });
    expect(d.to).toEqual({ app_label: 'a', model_name: 'b' });
  });
});

describe('detailFromFormSpec (#659)', () => {
  it('sources fields + fieldsets from the spec but keeps inlines / save_options / label from the detail', () => {
    const detail = {
      app_label: 'auth',
      model_name: 'group',
      pk: 1,
      label: 'editors',
      permissions: { view: true, add: true, change: true, delete: true },
      fieldsets: [{ title: null, fields: ['legacy'] }],
      fields: { legacy: { type: 'string', label: 'Legacy', required: false, readonly: false, help_text: '', value: 'x' } },
      inlines: [{ name: 'memberships' }],
      save_options: { show_save: true },
    } as unknown as DetailResponse;
    const spec: FormSpecResponse = {
      renderer: 'form-spec',
      fieldsets: [{ title: 'Identity', fields: ['name'], classes: ['collapse'] }],
      fields: { name: fsField() },
      variant: 'myapp.forms.GroupForm',
    };

    const merged = detailFromFormSpec(detail, spec);
    // fields + fieldsets come from the spec…
    expect(Object.keys(merged.fields)).toEqual(['name']);
    expect(merged.fieldsets[0]?.classes).toEqual(['collapse']);
    // …everything else stays from the detail payload.
    expect(merged.inlines).toEqual([{ name: 'memberships' }]);
    expect(merged.save_options).toEqual({ show_save: true });
    expect(merged.label).toBe('editors');
  });
});
