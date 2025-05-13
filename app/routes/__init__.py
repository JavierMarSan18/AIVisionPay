import os
import importlib

def register_routes(app, *args):
    # Importar todos los módulos en el directorio routes
    for filename in os.listdir(os.path.dirname(__file__)):
        if filename.endswith('.py') and not filename.startswith('_'):
            module_name = filename[:-3]
            module = importlib.import_module(f'routes.{module_name}')
            if hasattr(module, 'init_route'):
                module.init_route(app, *args)