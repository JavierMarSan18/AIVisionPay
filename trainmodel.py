import kagglehub
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing import image_dataset_from_directory
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.callbacks import ReduceLROnPlateau
import numpy as np
import os

# Download dataset
# dataset_path = kagglehub.dataset_download("salmaneunus/mechanical-tools-dataset")
# print("Dataset downloaded in:", dataset_path)

dataset_path = "../Training/v3"

# Adjust correct paths
train_path = os.path.join(dataset_path, "train_data")  
val_path = os.path.join(dataset_path, "validation_data")  

if not os.path.exists(train_path) or not os.path.exists(val_path):
    raise Exception(f"⚠️ The correct folders were not found. Verify that {train_path} and {val_path} exist.")

# Prepare dataset
img_size = (224, 224)
batch_size = 32

train_ds = image_dataset_from_directory(
    train_path,
    image_size=img_size,
    batch_size=batch_size
)

val_ds = image_dataset_from_directory(
    val_path,
    image_size=img_size,
    batch_size=batch_size
)

class_names = train_ds.class_names
print("Classes detected:", class_names)

# Use data augmentation to improve model
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.3),
    layers.RandomZoom(0.3),
    layers.RandomBrightness(0.3),
    layers.RandomContrast(0.3),
    layers.RandomTranslation(height_factor=0.2, width_factor=0.2),
    layers.RandomWidth(0.2),
    layers.RandomHeight(0.2) 
])

# Optimize dataset
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

# Create base model
base_model = MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights='imagenet')
base_model.trainable = True

# Freeze first 100 layers
for layer in base_model.layers[:100]:
    layer.trainable = False

# Create model
model = models.Sequential([
    data_augmentation,
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.BatchNormalization(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(len(class_names), activation='softmax')
])

# Compile model
model.compile(optimizer=tf.keras.optimizers.Adam(1e-4), 
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

# Callbacks to avoid overfitting
early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)

# Train model
# print("Entrenando el modelo con fine-tuning parcial...")
print("Training model with partial fine-tuning")
model.fit(train_ds, validation_data=val_ds, epochs=50, callbacks=[early_stopping, reduce_lr])

# Save model
model_path = "../model_version/iavisionpay_modelv4.keras"
model.save(model_path)
print(f"Model save in {model_path}")