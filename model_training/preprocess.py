import tensorflow as tf

def normalize_img(image, label):
    """Scale image pixels to [0, 1] range."""
    image = tf.cast(image, tf.float32) / 255.0
    return image, label

def resize_img(image, label, size=(224, 224)):
    """Resize image to the specified size."""
    image = tf.image.resize(image, size)
    return image, label

def preprocess_pipeline(size=(224, 224)):
    """Returns a composed preprocessing pipeline."""
    def _process(image, label):
        image, label = resize_img(image, label, size)
        image, label = normalize_img(image, label)
        return image, label
    return _process