#!/usr/bin/env python3
import os
import json
import argparse
from PIL import Image
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing import image_dataset_from_directory
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

from preprocess import preprocess_pipeline
from data_augmentation import get_augmentation_pipeline


def convert_images_for_tensorflow(input_dir, img_size, allowed_exts=(".jpg", ".jpeg", ".png", ".webp")):
    """
    Convert images in `input_dir` to RGB JPEGs of size `img_size`, stripping other formats.
    """
    print(f"🔁 Ajustando imágenes en {input_dir} para TensorFlow...")
    for root, _, files in os.walk(input_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in allowed_exts:
                continue
            src_path = os.path.join(root, fname)
            try:
                img = Image.open(src_path).convert("RGB")
                img = img.resize(img_size, Image.LANCZOS)
                # Guarda en JPEG
                new_name = os.path.splitext(fname)[0] + ".jpg"
                dst_path = os.path.join(root, new_name)
                img.save(dst_path, format="JPEG", quality=95)
                # Elimina el original si cambió la extensión
                if src_path != dst_path:
                    os.remove(src_path)
            except Exception as e:
                print(f"⚠️ Error procesando {src_path}: {e}")


# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True, help="Path to config JSON")
args = parser.parse_args()

# Load config
with open(args.config, "r", encoding="utf-8") as f:
    config = json.load(f)

params = config["training_parameters"]
paths = config["paths"]
img_size = tuple(config["image_settings"]["input_size"])

dataset_path = paths["dataset"]
train_path = os.path.join(dataset_path, paths["train_data"])
val_path = os.path.join(dataset_path, paths["validation_data"])
model_path = paths["model_output"]

# Ajuste de imágenes al formato y tamaño adecuado
convert_images_for_tensorflow(train_path, img_size)
convert_images_for_tensorflow(val_path, img_size)

# Carga de datasets
batch_size = params["batch_size"]
train_ds = image_dataset_from_directory(train_path, image_size=img_size, batch_size=batch_size)
val_ds = image_dataset_from_directory(val_path, image_size=img_size, batch_size=batch_size)
class_names = train_ds.class_names
print("Classes:", class_names)

# Preprocesado
train_ds = train_ds.map(preprocess_pipeline(size=img_size))
val_ds = val_ds.map(preprocess_pipeline(size=img_size))

# Optimización de datos
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

# Modelo base
base_model = MobileNetV2(input_shape=img_size + (3,), include_top=False, weights="imagenet")
base_model.trainable = True
for layer in base_model.layers[:params["fine_tuning"]["frozen_layers"]]:
    layer.trainable = False

# Construcción del modelo
model = models.Sequential([
    get_augmentation_pipeline(),
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.BatchNormalization(),
    layers.Dense(128, activation="relu"),
    layers.Dropout(0.3),
    layers.Dense(len(class_names), activation="softmax")
])

# Compilación
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=params["learning_rate"]),
    loss=params["loss_function"],
    metrics=["accuracy"]
)

# Callbacks
early_stopping = EarlyStopping(**params["callbacks"]["early_stopping"])
reduce_lr = ReduceLROnPlateau(**params["callbacks"]["reduce_lr_on_plateau"])

# Entrenamiento
model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=params["num_epochs"],
    callbacks=[early_stopping, reduce_lr]
)

# Guardado
model.save(model_path)
print(f"✅ Model saved at {model_path}")
