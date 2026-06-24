CREATE TABLE IF NOT EXISTS datazos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Extraído por Claude Vision
    producto TEXT NOT NULL,
    precio_dazo INTEGER NOT NULL,
    precio_supermercado INTEGER,
    ahorro_porcentaje INTEGER,
    local TEXT,
    ubicacion_mencionada TEXT,

    -- Foto del producto (frame capturado o thumbnail)
    foto_producto_url TEXT,

    -- Enriquecimiento web (Plan 3 — vacíos por ahora)
    direccion TEXT,
    telefono TEXT,
    horario TEXT,
    maps_url TEXT,
    foto_local_url TEXT,

    -- Trazabilidad a la fuente
    video_crudo_id TEXT REFERENCES videos_crudos(id),
    fuente_url TEXT,
    plataforma TEXT,
    fecha_encontrado DATE,

    -- Estado del flujo de publicación
    estado TEXT DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'publicado', 'incompleto')),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_datazos_estado ON datazos(estado);
CREATE INDEX IF NOT EXISTS idx_datazos_fecha ON datazos(fecha_encontrado DESC);
CREATE INDEX IF NOT EXISTS idx_datazos_video ON datazos(video_crudo_id);
