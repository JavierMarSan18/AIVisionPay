# 📌 Configuración y Uso del Modelo

## 🔧 A) Pasos para preparar el ambiente

1. **Crear un entorno virtual**
   ```bash
   python3 -m venv modelenv
   ```
2.1. **Activar el entorno virtual (Mac)**
   ```bash
   source modelenv/bin/activate
   ```

2.2. **Activar el entorno virtual (Windows)**
   ```bash
   modelenv\Scripts\activate
   ```


---

## 🎯 B) Pasos para crear un modelo

1. **Ejecutar el archivo de entrenamiento del modelo**
   ```bash
   python trainmodel.py
   ```
2. **Si lanza un error por falta de librerías**, instalarlas con:
   ```bash
   pip install -r requirements.txt
   ```
   *(Solo es necesario la primera vez o si hay cambios en las dependencias).*

---

## 🚀 C) Pasos para ejecutar un modelo existente

1. **Ejecutar el archivo de carga del modelo**
   ```bash
   python loadmodel.py
   ```
2. 📌 **Nota importante:** La ruta del modelo a ejecutar se define en la línea **42** del archivo `loadmodel.py`.

📸 **Para salir de la cámara, presiona `q`.**
