#!/bin/bash

# Rutas a limpiar
TRAIN_DIR="data/Training/v1/train_data"
VAL_DIR="data/Training/v1/validation_data"

echo "🧼 Limpiando metadatos PNG en: $TRAIN_DIR y $VAL_DIR"

# Verifica que ImageMagick esté instalado
if ! command -v mogrify &> /dev/null; then
    echo "❌ Error: ImageMagick no está instalado."
    echo "➡️ Instálalo con: sudo yum install -y ImageMagick (EC2)"
    exit 1
fi

# Limpieza recursiva
for DIR in "$TRAIN_DIR" "$VAL_DIR"; do
  if [ -d "$DIR" ]; then
    find "$DIR" -type f -iname '*.png' -exec mogrify -strip {} \;
    echo "✅ Limpieza completada en: $DIR"
  else
    echo "⚠️ Directorio no encontrado: $DIR"
  fi
done
