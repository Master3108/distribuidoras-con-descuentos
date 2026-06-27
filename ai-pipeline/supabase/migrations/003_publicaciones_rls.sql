-- Tabla de publicaciones: un registro por cada post publicado en cada canal.
CREATE TABLE IF NOT EXISTS publicaciones (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    dazo_id UUID REFERENCES datazos(id) ON DELETE CASCADE,
    canal TEXT NOT NULL,            -- instagram | facebook | tiktok | whatsapp | telegram | web
    fecha_publicacion TIMESTAMPTZ DEFAULT NOW(),
    url_publicacion TEXT
);
CREATE INDEX IF NOT EXISTS idx_publicaciones_dazo ON publicaciones(dazo_id);

-- ── Row Level Security ──────────────────────────────────────────────────────
ALTER TABLE videos_crudos ENABLE ROW LEVEL SECURITY;
ALTER TABLE datazos       ENABLE ROW LEVEL SECURITY;
ALTER TABLE publicaciones ENABLE ROW LEVEL SECURITY;

-- La web pública (publishable/anon key) solo LEE datazos ya publicados.
DROP POLICY IF EXISTS "lectura publica datazos" ON datazos;
CREATE POLICY "lectura publica datazos" ON datazos
    FOR SELECT TO anon
    USING (estado = 'publicado');

-- videos_crudos y publicaciones NO tienen policy para anon: solo el backend
-- (secret key / service_role, que ignora RLS) escribe y lee. Datos internos.
