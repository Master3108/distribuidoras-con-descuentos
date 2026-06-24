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
