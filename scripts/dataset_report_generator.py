import os
import json
import argparse

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
        if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))
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

def main():
    parser = argparse.ArgumentParser(description='Generate dataset report')
    parser.add_argument('--dataset_path', required=True,
                        help='Ruta base del dataset (contiene train_data/ y validation_data/)')
    parser.add_argument('--targets', required=True,
                        help='Archivo JSON con objetivos image_targets_per_class')
    parser.add_argument('--output', default='dataset_report.json',
                        help='Archivo JSON de salida del reporte')
    args = parser.parse_args()

    train_base = os.path.join(args.dataset_path, 'train_data')
    val_base   = os.path.join(args.dataset_path, 'validation_data')

    targets = load_json(args.targets)

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

    create_folder(os.path.dirname(args.output))
    save_json(report, args.output)

    print(f"📊 Dataset report saved to {args.output}")
    for r in report:
        print(f"{r['class']}: train={r['train_count']} ({r['train_status']}), "
              f"validation={r['validation_count']} ({r['validation_status']})")

if __name__ == '__main__':
    main()
