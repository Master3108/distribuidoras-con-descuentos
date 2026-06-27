-- El publicador registra por canal el resultado (ok) y el motivo/error (detalle).
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS ok BOOLEAN;
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS detalle TEXT;

-- Bucket público para las imágenes de marca / frames de los posts.
INSERT INTO storage.buckets (id, name, public)
VALUES ('datazos-frames', 'datazos-frames', true)
ON CONFLICT (id) DO NOTHING;
