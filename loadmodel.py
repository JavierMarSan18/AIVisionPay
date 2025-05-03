import kagglehub
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing import image_dataset_from_directory
import numpy as np
import cv2
import os
import pyttsx3

# Download dataset
dataset_path = kagglehub.dataset_download("salmaneunus/mechanical-tools-dataset")
print("Dataset downloaded in:", dataset_path)

# Adjust correct paths
train_path = os.path.join(dataset_path, "train_data_V2", "train_data_V2")  
val_path = os.path.join(dataset_path, "validation_data_V2", "validation_data_V2")  

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

print("Starting camera recognition. Press 'q' to exit...")

model_path = 'iavisionpay_model.keras'
img_size = (224, 224)

model = tf.keras.models.load_model(model_path)
engine = pyttsx3.init()
engine.setProperty('rate', 160)
engine.setProperty('volume', 1.0)
last_prediction = ""

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Preprocessing
    img = cv2.resize(frame, img_size)
    img_array = tf.keras.applications.mobilenet_v2.preprocess_input(np.expand_dims(img, axis=0))

    # Prediction
    predictions = model.predict(img_array, verbose=0)
    predicted_index = np.argmax(predictions)
    predicted_label = class_names[predicted_index]
    confidence = predictions[0][predicted_index]

    # Show prediction
    label_text = f"{predicted_label} ({confidence*100:.1f}%)"
    cv2.putText(frame, label_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Reconocimiento de herramientas", frame)

    # Text to speech with confidence > 85%
    if predicted_label != last_prediction and confidence > 0.90:
        phrase = f"{predicted_label}"
        engine.say(phrase)
        engine.runAndWait()
        last_prediction = predicted_label

    # Exit with 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
