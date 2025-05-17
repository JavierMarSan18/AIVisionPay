import os
import json
import argparse
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing import image_dataset_from_directory
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

from preprocess import preprocess_pipeline
from data_augmentation import get_augmentation_pipeline

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

# Dataset
batch_size = params["batch_size"]
train_ds = image_dataset_from_directory(train_path, image_size=img_size, batch_size=batch_size)
val_ds = image_dataset_from_directory(val_path, image_size=img_size, batch_size=batch_size)
class_names = train_ds.class_names
print("Classes:", class_names)

# Apply preprocessing
train_ds = train_ds.map(preprocess_pipeline(size=img_size))
val_ds = val_ds.map(preprocess_pipeline(size=img_size))

# Apply data optimization
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

# Load base model
base_model = MobileNetV2(input_shape=img_size + (3,), include_top=False, weights="imagenet")
base_model.trainable = True
for layer in base_model.layers[:params["fine_tuning"]["frozen_layers"]]:
    layer.trainable = False

# Build model
model = models.Sequential([
    get_augmentation_pipeline(),
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.BatchNormalization(),
    layers.Dense(128, activation="relu"),
    layers.Dropout(0.3),
    layers.Dense(len(class_names), activation="softmax")
])

# Compile
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=params["learning_rate"]),
    loss=params["loss_function"],
    metrics=["accuracy"]
)

# Callbacks
early_stopping = EarlyStopping(**params["callbacks"]["early_stopping"])
reduce_lr = ReduceLROnPlateau(**params["callbacks"]["reduce_lr_on_plateau"])

# Train
model.fit(train_ds, validation_data=val_ds, epochs=params["num_epochs"], callbacks=[early_stopping, reduce_lr])

# Save
model.save(model_path)
print(f"✅ Model saved at {model_path}")