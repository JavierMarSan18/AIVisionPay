import tensorflow as tf
from tensorflow.keras import layers

def get_augmentation_pipeline():
    """Returns a data augmentation pipeline as a Sequential model."""
    return tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.2),
        layers.RandomBrightness(0.2),
        layers.RandomContrast(0.2)
    ])