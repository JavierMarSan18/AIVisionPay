import argparse
import json
from app import create_app

def main():
    parser = argparse.ArgumentParser(description="IAVisionPay API")
    parser.add_argument("--config", required=True, help="Ruta del archivo de configuración JSON")
    args = parser.parse_args()

    # Cargar configuración desde el archivo proporcionado
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Crear la aplicación con la configuración
    app = create_app(config)

    # Ejecutar servidor Flask
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()