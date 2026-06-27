-- ============================================================
-- Esquema completo "Datazos RM" — pegar en el SQL Editor de Supabase
-- (proyecto nuevo dedicado). Crea las 3 tablas y las políticas RLS.
-- ============================================================

-- 1) Videos crudos (los que encuentra el scraper)
CREATE TABLE IF NOT EXISTS videos_crudos (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    plataforma TEXT NOT NULL CHECK (plataforma IN ('tiktok', 'instagram', 'youtube', 'facebook')),
    cuenta TEXT,
    descripcion TEXT,
    fecha DATE,
    miniatura_url TEXT,
    video_url TEXT,
    fecha_encontrado TIMESTAMPTZ DEFAULT NOW(),
    procesado BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_videos_crudos_procesado ON videos_crudos(procesado);
CREATE INDEX IF NOT EXISTS idx_videos_crudos_plataforma ON videos_crudos(plataforma);
CREATE INDEX IF NOT EXISTS idx_videos_crudos_fecha ON videos_crudos(fecha_encontrado DESC);

-- 2) Datazos (productos en oferta extraídos por el cerebro)
CREATE TABLE IF NOT EXISTS datazos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    producto TEXT NOT NULL,
    precio_dazo INTEGER NOT NULL,
    precio_supermercado INTEGER,
    ahorro_porcentaje INTEGER,
    local TEXT,
    ubicacion_mencionada TEXT,
    foto_producto_url TEXT,
    direccion TEXT,
    telefono TEXT,
    horario TEXT,
    maps_url TEXT,
    foto_local_url TEXT,
    video_crudo_id TEXT REFERENCES videos_crudos(id),
    fuente_url TEXT,
    plataforma TEXT,
    fecha_encontrado DATE,
    estado TEXT DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'publicado', 'incompleto')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_datazos_estado ON datazos(estado);
CREATE INDEX IF NOT EXISTS idx_datazos_fecha ON datazos(fecha_encontrado DESC);
CREATE INDEX IF NOT EXISTS idx_datazos_video ON datazos(video_crudo_id);

-- 3) Publicaciones (registro de qué se publicó y dónde)
CREATE TABLE IF NOT EXISTS publicaciones (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    dazo_id UUID REFERENCES datazos(id),
    canal TEXT NOT NULL,
    ok BOOLEAN NOT NULL,
    detalle TEXT,
    fecha_publicacion TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pub_dazo ON publicaciones(dazo_id);
CREATE INDEX IF NOT EXISTS idx_pub_canal ON publicaciones(canal);

-- ============================================================
-- RLS (seguridad)
-- El pipeline escribe con la SERVICE_ROLE key (ignora RLS).
-- La web lee con la ANON key → necesita poder SELECT en datazos.
-- ============================================================
ALTER TABLE datazos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "lectura publica datazos" ON datazos;
CREATE POLICY "lectura publica datazos" ON datazos
    FOR SELECT TO anon USING (true);

-- videos_crudos y publicaciones: RLS activo SIN políticas → la anon key no puede
-- leerlos (solo el pipeline con service_role). No se exponen en la web.
ALTER TABLE videos_crudos ENABLE ROW LEVEL SECURITY;
ALTER TABLE publicaciones ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Además, en el panel de Supabase → Storage, crea un bucket PÚBLICO
-- llamado 'datazos-frames' (ahí se suben las fotos de productos/posts).
-- ============================================================
