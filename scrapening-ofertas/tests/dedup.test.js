import { isNew, markProcessed, trimIds } from '../src/dedup.js';

test('isNew retorna true si el id no existe en la plataforma', () => {
    const ids = { tiktok: ['111', '222'] };
    expect(isNew(ids, 'tiktok', '333')).toBe(true);
});

test('isNew retorna false si el id ya existe', () => {
    const ids = { tiktok: ['111', '222'] };
    expect(isNew(ids, 'tiktok', '111')).toBe(false);
});

test('isNew retorna true para plataforma sin entradas previas', () => {
    const ids = {};
    expect(isNew(ids, 'instagram', 'abc123')).toBe(true);
});

test('markProcessed agrega el id a la plataforma correcta', () => {
    const ids = {};
    const result = markProcessed(ids, 'tiktok', '999');
    expect(result.tiktok).toContain('999');
});

test('markProcessed no modifica otras plataformas', () => {
    const ids = { instagram: ['abc'] };
    const result = markProcessed(ids, 'tiktok', '999');
    expect(result.instagram).toEqual(['abc']);
});

test('trimIds recorta al máximo cuando supera el límite', () => {
    const ids = Array.from({ length: 150 }, (_, i) => String(i));
    const trimmed = trimIds(ids, 100);
    expect(trimmed.length).toBe(100);
    expect(trimmed[0]).toBe('50'); // mantiene los últimos 100
});

test('trimIds no modifica si está bajo el límite', () => {
    const ids = ['a', 'b', 'c'];
    expect(trimIds(ids, 100)).toEqual(['a', 'b', 'c']);
});
