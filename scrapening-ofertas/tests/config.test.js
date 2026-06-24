import { DEFAULT_HASHTAGS, PLATFORMS, MAX_IDS_PER_PLATFORM } from '../src/config.js';

test('DEFAULT_HASHTAGS tiene entradas para todas las plataformas', () => {
    expect(DEFAULT_HASHTAGS.tiktok.length).toBeGreaterThan(0);
    expect(DEFAULT_HASHTAGS.instagram.length).toBeGreaterThan(0);
    expect(DEFAULT_HASHTAGS.youtube.length).toBeGreaterThan(0);
    expect(DEFAULT_HASHTAGS.facebook.length).toBeGreaterThan(0);
});

test('PLATFORMS contiene las 4 plataformas', () => {
    expect(PLATFORMS).toEqual(['tiktok', 'instagram', 'youtube', 'facebook']);
});

test('MAX_IDS_PER_PLATFORM es número positivo', () => {
    expect(MAX_IDS_PER_PLATFORM).toBeGreaterThan(0);
});
