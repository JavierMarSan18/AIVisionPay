#!/usr/bin/env bash

# Uso: ./run_dataset_report.sh v1

if [ -z "$1" ]; then
  echo "❌ Uso: $0 <versión>  (ej: v1)"
  exit 1
fi

VERSION=$1
DATE=$(date +%Y%m%d%H%M%S)
DATASET_PATH="./data/Training/${VERSION}"
TARGETS_FILE="./config/${VERSION}/image_targets_per_class.json"
OUTPUT_DIR="./reports/${VERSION}"
OUTPUT_FILE="${OUTPUT_DIR}/dataset_report_${VERSION}_${DATE}.json"

# Crear carpeta de reportes si no existe
mkdir -p "$OUTPUT_DIR"

echo "🏷  Generando reporte para versión: $VERSION"
echo "   Fecha  : $DATE"
echo "   Dataset: $DATASET_PATH"
echo "   Targets: $TARGETS_FILE"
echo "   Salida : $OUTPUT_FILE"
echo

python scripts/dataset_report_generator.py \
  --dataset_path "$DATASET_PATH" \
  --targets      "$TARGETS_FILE" \
  --output       "$OUTPUT_FILE"
