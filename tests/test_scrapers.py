import unittest
import sys
import os
import json
from datetime import datetime
from unittest.mock import patch, Mock
import logging

# Configurar logging básico para tests
logging.basicConfig(level=logging.WARNING)

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scrapers.gatotv_scraper import GatoTVScraper
from Scrapers.ontvtonight_scraper import OnTVTonightScraper

class TestScrapers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Configuración inicial para todos los tests"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                cls.config = json.load(f)
        except Exception as e:
            logging.error(f"Error cargando config.json: {e}")
            cls.config = {
                "settings": {
                    "timezone_offset_hours": 6,
                    "timeout": 15,
                    "headers": {
                        "User-Agent": "Mozilla/5.0"
                    }
                }
            }

    def setUp(self):
        """Configuración para cada test individual"""
        try:
            self.gatotv = GatoTVScraper(self.config)
            self.ontvtonight = OnTVTonightScraper(self.config)
        except Exception as e:
            logging.error(f"Error en setUp: {e}")
            raise

    def test_gatotv_initialization(self):
        """Verifica la inicialización del scraper GatoTV"""
        self.assertIsNotNone(self.gatotv)
        self.assertIsNotNone(self.gatotv.session)
        self.assertEqual(self.gatotv.timeout, self.config['settings']['timeout'])

    @patch('requests.Session.get')
    def test_gatotv_fetch_programs(self, mock_get):
        """Verifica la obtención de programas de GatoTV con mock"""
        # Simular respuesta exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <div class="tbl_EPG_container">
            <table class="tbl_EPG">
                <tr class="tbl_EPG_row">
                    <td class="tbl_EPG_hour">
                        <time datetime="08:00">08:00</time>
                    </td>
                    <td class="tbl_EPG_hour">
                        <time datetime="09:00">09:00</time>
                    </td>
                    <td class="tbl_EPG_container">
                        <div class="tbl_EPG_text">
                            <div class="tbl_EPG_title">
                                <span>Programa Test</span>
                            </div>
                            <div class="hidden-xs">
                                Descripción del programa test
                            </div>
                        </div>
                    </td>
                </tr>
            </table>
        </div>
        '''
        mock_get.return_value = mock_response

        # Usar un canal de prueba basado en la configuración real
        channel = {
            "id": "test.channel",
            "nombre": "Test Channel",
            "scraper": "gatotv",
            "url": "https://www.gatotv.com/canal/test",
            "site_id": "test",
            "timezone_override": 6
        }
        
        try:
            programs = self.gatotv.fetch_programs(channel)
            self.assertIsNotNone(programs)
            self.assertTrue(len(programs) > 0, "No se obtuvieron programas")
            
            if programs:
                program = programs[0]
                self.assertIn('title', program, "El programa no tiene título")
                self.assertIn('start', program, "El programa no tiene hora de inicio")
                self.assertIn('stop', program, "El programa no tiene hora de fin")
                self.assertEqual(program['title'], "Programa Test", "El título no coincide")
        except Exception as e:
            self.fail(f"Error en test_gatotv_fetch_programs: {e}")

if __name__ == '__main__':
    unittest.main()
