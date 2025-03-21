A) Pasos para preparar ambiente.
1. Crear un env (Ejecutar)
   python3 -m venv modelenv
2. Activar el env
   source modelenv/bin/activate

B) Pasos para crear un modelo
1. Ejecutar el train model file
   python trainmodel.py
1.1 Si lanza un error es porque hay que agregar las librerías (Solo al ejecutar por primera vez)

C) Pasos para ejecutar un modelo existente
1. Ejecutar el train model file (En la linea 42 del archivo loadmodel.py se define la ruta del modelo a ejecutar)
   python loadmodel.py

Nota: Para salir de la cámara se debe presionar 'q'.
