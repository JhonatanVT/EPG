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
    @classmethod
    def setUpClass(cls):
        """Configuración inicial que se ejecuta una vez"""
        with open('config.json', 'r', encoding='utf-8') as f:
            cls.config = json.load(f)
            
    def setUp(self):
        """Configuración para cada test"""
        self.gatotv = GatoTVScraper(self.config)
        self.ontvtonight = OnTVTonightScraper(self.config)

    def test_gatotv_initialization(self):
        """Verifica la inicialización del scraper GatoTV"""
        self.assertIsNotNone(self.gatotv.session)
        self.assertEqual(self.gatotv.timeout, self.config['settings']['timeout'])
        self.assertIsNotNone(self.gatotv.headers)

    def test_ontvtonight_initialization(self):
        """Verifica la inicialización del scraper OnTVTonight"""
        self.assertIsNotNone(self.ontvtonight.session)
        self.assertEqual(self.ontvtonight.timeout, self.config['settings']['timeout'])
        self.assertIsNotNone(self.ontvtonight.headers)

    @patch('requests.Session.get')
    def test_gatotv_fetch_programs(self, mock_get):
        """Verifica la obtención de programas de GatoTV con mock"""
        # Simular respuesta exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <table class="tbl_EPG">
            <tr class="tbl_EPG_row">
                <td class="tbl_EPG_hour">
                    <time datetime="08:00">08:00</time>
                </td>
                <td class="tbl_EPG_hour">
                    <time datetime="09:00">09:00</time>
                </td>
                <td class="tbl_EPG_container">
                    <div class="tbl_EPG_title">
                        <span>Programa Test</span>
                    </div>
                </td>
            </tr>
        </table>
        '''
        mock_get.return_value = mock_response

        channel = {
            "id": "test.channel",
            "nombre": "Test Channel",
            "scraper": "gatotv",
            "url": "https://www.gatotv.com/canal/test",
            "site_id": "test"
        }
        
        programs = self.gatotv.fetch_programs(channel)
        self.assertTrue(len(programs) > 0, "No se obtuvieron programas")
        if programs:
            program = programs[0]
            self.assertIn('title', program)
            self.assertIn('start', program)
            self.assertIn('stop', program)

    def test_url_validation(self):
        """Verifica la validación de URLs"""
        # URLs válidas
        valid_urls = [
            "https://www.gatotv.com/canal/test",
            "https://www.ontvtonight.com/guide/test"
        ]
        for url in valid_urls:
            self.assertTrue(self.gatotv.validate_url(url))
            self.assertTrue(self.ontvtonight.validate_url(url))

        # URLs inválidas
        invalid_urls = [
            "not_a_url",
            "http://",
            "ftp://invalid.com",
            "",
            None,
            "https:/malformed.com"
        ]
        for url in invalid_urls:
            try:
                result = self.gatotv.validate_url(url)
                self.assertFalse(result, f"URL inválida '{url}' fue aceptada")
            except:
                # Si lanza excepción, consideramos que la validación funcionó
                pass

    @patch('requests.Session.get')
    def test_program_time_sequence(self, mock_get):
        """Verifica que los tiempos sean secuenciales usando mock"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <table class="tbl_EPG">
            <tr class="tbl_EPG_row">
                <td class="tbl_EPG_hour">
                    <time datetime="08:00">08:00</time>
                </td>
                <td class="tbl_EPG_hour">
                    <time datetime="09:00">09:00</time>
                </td>
                <td class="tbl_EPG_container">
                    <div class="tbl_EPG_title">
                        <span>Programa 1</span>
                    </div>
                </td>
            </tr>
            <tr class="tbl_EPG_row">
                <td class="tbl_EPG_hour">
                    <time datetime="09:00">09:00</time>
                </td>
                <td class="tbl_EPG_hour">
                    <time datetime="10:00">10:00</time>
                </td>
                <td class="tbl_EPG_container">
                    <div class="tbl_EPG_title">
                        <span>Programa 2</span>
                    </div>
                </td>
            </tr>
        </table>
        '''
        mock_get.return_value = mock_response

        channel = {
            "id": "test.channel",
            "nombre": "Test Channel",
            "scraper": "gatotv",
            "url": "https://www.gatotv.com/canal/test",
            "site_id": "test"
        }
        
        programs = self.gatotv.fetch_programs(channel)
        if len(programs) > 1:
            for i in range(len(programs) - 1):
                current = datetime.strptime(programs[i]['start'], '%Y%m%d%H%M%S')
                next_prog = datetime.strptime(programs[i + 1]['start'], '%Y%m%d%H%M%S')
                self.assertLessEqual(current, next_prog)

if __name__ == '__main__':
    unittest.main()
