import { describe, expect, it } from 'vitest';

import type { DetailResponse, FormSpecField, FormSpecResponse } from '@dar/data';

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

  it('leaves widget undefined for kinds the FieldType already implies (select/date/autocomplete/…)', () => {
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'select', attrs: {} } })).widget).toBeUndefined();
    expect(formSpecFieldToDescriptor(fsField({ widget: { kind: 'date', attrs: {} } })).widget).toBeUndefined();
    expect(
      formSpecFieldToDescriptor(fsField({ widget: { kind: 'autocomplete', attrs: {} } })).widget,
    ).toBeUndefined();
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
