import os
import json
import argparse
from datetime import datetime

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

def count_images(folder):
    if not os.path.isdir(folder):
        return 0
    return sum(
        1
        for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
    )

def classify_train(count, thresholds):
    if count < thresholds['baseline_model']:
        return 'Weak'
    elif count < thresholds['high_accuracy']:
        return 'Acceptable'
    elif count < thresholds['maximum_accuracy']:
        return 'Strong'
    else:
        return 'Excellent'

def classify_validation(count, thresholds):
    if count < thresholds['minimal_test']:
        return 'Weak'
    else:
        return 'Strong'

def extract_version_from_filename(filename):
    # ejemplo: dataset_report_v1_20250512.json → v1
    name = os.path.basename(filename)
    parts = name.replace(".json", "").split("_")
    return parts[2] if len(parts) >= 3 else "unknown"

def update_report_index(index_path, version, report_name):
    if os.path.exists(index_path):
        index = load_json(index_path)
    else:
        index = {}

    if version not in index:
        index[version] = []

    if report_name not in index[version]:
        index[version].append(report_name)

    # ordenar de más reciente a más antiguo
    index[version].sort(reverse=True)
    save_json(index, index_path)

def main():
    parser = argparse.ArgumentParser(description='Generate dataset report')
    parser.add_argument('--dataset_path', required=True,
                        help='Ruta base del dataset (contiene train_data/ y validation_data/)')
    parser.add_argument('--targets', required=True,
                        help='Archivo JSON con objetivos image_targets_per_class')
    parser.add_argument('--output', required=True,
                        help='Archivo JSON de salida del reporte')
    args = parser.parse_args()

    train_base = os.path.join(args.dataset_path, 'train_data')
    val_base   = os.path.join(args.dataset_path, 'validation_data')
    targets    = load_json(args.targets)

    report = []
    for entry in targets:
        cls = entry['class_name']
        th  = entry['targets']
        train_folder = os.path.join(train_base, cls)
        val_folder   = os.path.join(val_base, cls)

        train_count = count_images(train_folder)
        val_count   = count_images(val_folder)

        train_status = classify_train(train_count, th)
        val_status   = classify_validation(val_count, th)

        report.append({
            'class': cls,
            'train_count': train_count,
            'train_status': train_status,
            'validation_count': val_count,
            'validation_status': val_status,
        })

    # Guardar reporte
    create_folder(os.path.dirname(args.output))
    save_json(report, args.output)
    print(f"📊 Dataset report saved to {args.output}")

    # Actualizar índice
    version = extract_version_from_filename(args.output)
    report_name = os.path.basename(args.output)
    index_path = os.path.join(os.path.dirname(args.output), '..', 'index.json')
    update_report_index(index_path, version, report_name)
    print(f"🗂 Index updated: {index_path}")

    for r in report:
        print(f"{r['class']}: train={r['train_count']} ({r['train_status']}), "
              f"validation={r['validation_count']} ({r['validation_status']})")

if __name__ == '__main__':
    main()