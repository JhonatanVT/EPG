import unittest
import sys
import os
import json
from datetime import datetime
from unittest.mock import patch, Mock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scrapers.gatotv_scraper import GatoTVScraper
from Scrapers.ontvtonight_scraper import OnTVTonightScraper

class TestScrapers(unittest.TestCase):
    # ...existing code...

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

        channel = {
            "id": "test.channel",
            "nombre": "Test Channel",
            "scraper": "gatotv",
            "url": "https://www.gatotv.com/canal/test",
            "site_id": "test",
            "timezone_override": 6
        }
        
        programs = self.gatotv.fetch_programs(channel)
        self.assertTrue(len(programs) > 0, "No se obtuvieron programas")
        if programs:
            program = programs[0]
            self.assertIn('title', program, "El programa no tiene título")
            self.assertIn('start', program, "El programa no tiene hora de inicio")
            self.assertIn('stop', program, "El programa no tiene hora de fin")
            self.assertEqual(program['title'], "Programa Test", "El título no coincide")
            
            # Verificar formato de fechas
            start_time = datetime.strptime(program['start'], '%Y%m%d%H%M%S')
            stop_time = datetime.strptime(program['stop'], '%Y%m%d%H%M%S')
            self.assertLess(start_time, stop_time, "La hora de fin debe ser posterior a la de inicio")

    # ...resto del código...
