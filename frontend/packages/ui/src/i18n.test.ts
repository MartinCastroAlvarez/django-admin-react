// Lock the SPA chrome i18n behaviour (#630):
//   1. `t(en)` returns the English source string when the catalog
//      has no entry for it (graceful degradation; consumers see
//      legible text mid-migration as keys land).
//   2. `loadCatalog(lang)` swaps the active catalog by exact code,
//      then by language stem (`es-AR` → `es`), then no-ops on
//      unknown codes (keeps English).
//   3. The bundled non-English catalogs actually translate the
//      sample keys we expect — sanity check that the JSON files
//      aren't empty / corrupted in the build pipeline.
import { beforeEach, describe, expect, it } from 'vitest';

import {
  _activeCatalogForTests,
  _setActiveCatalogForTests,
  loadCatalog,
  t,
} from './i18n';

beforeEach(() => {
  // Reset to the bundled English catalog before each test so cases
  // don't leak state through the shared module-level binding.
  loadCatalog('en');
});

describe('t (source-as-key translation lookup)', () => {
  it('returns the English source when the active catalog has no entry', () => {
    _setActiveCatalogForTests({});
    expect(t('Brand new string the catalog has never seen')).toBe(
      'Brand new string the catalog has never seen',
    );
  });

  it('returns the translation when the catalog has an entry', () => {
    _setActiveCatalogForTests({ Add: 'Añadir' });
    expect(t('Add')).toBe('Añadir');
  });

  it('falls back to the English source for a partial catalog', () => {
    _setActiveCatalogForTests({ Add: 'Añadir' });
    expect(t('Add')).toBe('Añadir'); // translated
    expect(t('Search')).toBe('Search'); // not in this fixture → English
  });
});

describe('loadCatalog (language → catalog selection)', () => {
  it('matches an exact language code', () => {
    loadCatalog('es');
    expect(t('Add')).toBe('Añadir');
  });

  it('matches by language stem when the full code is unknown (es-AR → es)', () => {
    loadCatalog('es-AR');
    expect(t('Add')).toBe('Añadir');
  });

  it('matches case-insensitively (ES → es)', () => {
    loadCatalog('ES');
    expect(t('Add')).toBe('Añadir');
  });

  it('matches pt-br to the pt catalog', () => {
    loadCatalog('pt-br');
    expect(t('Save')).toBe('Salvar');
  });

  it('falls back to English (no-op) on unknown codes', () => {
    _setActiveCatalogForTests({ Add: 'Añadir' }); // start non-English
    loadCatalog('zz-ZZ'); // unknown — leaves the previous catalog active
    expect(t('Add')).toBe('Añadir');
  });

  it('is a no-op when language is null / empty', () => {
    loadCatalog('es');
    loadCatalog(null);
    expect(t('Add')).toBe('Añadir'); // still Spanish
    loadCatalog('');
    expect(t('Add')).toBe('Añadir'); // still Spanish
  });
});

describe('bundled catalog sanity (#630 ship-set)', () => {
  it('Spanish translates the common chrome strings', () => {
    loadCatalog('es');
    expect(t('Add')).toBe('Añadir');
    expect(t('Save')).toBe('Guardar');
    expect(t('Cancel')).toBe('Cancelar');
    expect(t('Loading…')).toBe('Cargando…');
  });

  it('Portuguese translates the common chrome strings', () => {
    loadCatalog('pt');
    expect(t('Add')).toBe('Adicionar');
    expect(t('Save')).toBe('Salvar');
    expect(t('Delete')).toBe('Excluir');
  });

  it('French translates the common chrome strings', () => {
    loadCatalog('fr');
    expect(t('Add')).toBe('Ajouter');
    expect(t('Save')).toBe('Enregistrer');
    expect(t('Delete')).toBe('Supprimer');
  });

  it('English keeps the source strings unchanged (source-as-key)', () => {
    loadCatalog('en');
    // The English catalog only has the _comment; every real string
    // round-trips through the source-as-key fallback.
    expect(t('Add')).toBe('Add');
    expect(t('Anything not in the catalog')).toBe('Anything not in the catalog');
  });

  it('exposes the active catalog for debugging tests', () => {
    loadCatalog('es');
    const catalog = _activeCatalogForTests();
    expect(catalog.Add).toBe('Añadir');
  });
});
