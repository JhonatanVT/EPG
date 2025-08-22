"""
Test suite para el generador de EPG
--------------------------------

Este paquete contiene las pruebas unitarias para:
- Scrapers (GatoTV, OnTVTonight)
- Configuración
- Funcionalidades principales
"""

import os
import sys

# Añadir el directorio raíz al PYTHONPATH para poder importar los módulos
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Configuración básica para los tests
TEST_CONFIG = {
    "test_channels": {
        "gatotv": "Repretel6.cr",
        "ontvtonight": "Telemundo.us"
    },
    "timeout": 30,  # Timeout más largo para tests
    "retry_attempts": 2
}
