import { describe, expect, it, vi } from 'vitest';

import type { ApiClient } from '@dar/api';

import { createObject, deleteObject, fetchDeletePreview, updateObject } from './mutations';

// A stub ApiClient — the write helpers are thin pass-throughs, so the
// contract under test is "delegates to the right client method with the
// right args". Cast through `unknown` since we only stub the methods used.
function stubClient() {
  return {
    create: vi.fn().mockResolvedValue({ pk: 1, label: 'x' }),
    update: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue(undefined),
    deletePreview: vi.fn().mockResolvedValue({ can_delete: true }),
  };
}

describe('mutation helpers', () => {
  it('createObject → client.create(app, model, payload)', () => {
    const client = stubClient();
    void createObject({
      client: client as unknown as ApiClient,
      appLabel: 'crm',
      modelName: 'company',
      payload: { name: 'Acme' },
    });
    expect(client.create).toHaveBeenCalledWith('crm', 'company', { name: 'Acme' });
  });

  it('updateObject → client.update(app, model, pk, payload)', () => {
    const client = stubClient();
    void updateObject({
      client: client as unknown as ApiClient,
      appLabel: 'crm',
      modelName: 'company',
      pk: 7,
      payload: { name: 'Beta' },
    });
    expect(client.update).toHaveBeenCalledWith('crm', 'company', 7, { name: 'Beta' });
  });

  it('deleteObject → client.delete(app, model, pk)', () => {
    const client = stubClient();
    void deleteObject({
      client: client as unknown as ApiClient,
      appLabel: 'crm',
      modelName: 'company',
      pk: 'abc',
    });
    expect(client.delete).toHaveBeenCalledWith('crm', 'company', 'abc');
  });

  it('fetchDeletePreview → client.deletePreview(app, model, pk)', () => {
    const client = stubClient();
    void fetchDeletePreview({
      client: client as unknown as ApiClient,
      appLabel: 'crm',
      modelName: 'company',
      pk: 7,
    });
    expect(client.deletePreview).toHaveBeenCalledWith('crm', 'company', 7);
  });
});
