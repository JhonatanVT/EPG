import unittest
import sys
import os
import json
from datetime import datetime
from unittest.mock import patch
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
        self.test_date = "2025-08-22"  # Fecha fija para tests

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
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <table class="tbl_EPG">
            <tr class="tbl_EPG_row">
                <td><time datetime="08:00">08:00</time></td>
                <td><time datetime="09:00">09:00</time></td>
                <td><span>Programa Test</span></td>
            </tr>
        </table>
        """
        mock_get.return_value = mock_response

        channel = next(ch for ch in self.config['channels'] if ch['scraper'] == 'gatotv')
        programs = self.gatotv.fetch_programs(channel)
        
        self.assertTrue(len(programs) > 0)
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
            None
        ]
        for url in invalid_urls:
            self.assertFalse(self.gatotv.validate_url(url))
            self.assertFalse(self.ontvtonight.validate_url(url))

    def test_program_time_sequence(self):
        """Verifica que los tiempos sean secuenciales usando mock"""
        with patch('requests.Session.get') as mock_get:
            mock_response = unittest.mock.Mock()
            mock_response.status_code = 200
            mock_response.text = """
            <table class="tbl_EPG">
                <tr class="tbl_EPG_row">
                    <td><time datetime="08:00">08:00</time></td>
                    <td><time datetime="09:00">09:00</time></td>
                    <td><span>Programa 1</span></td>
                </tr>
                <tr class="tbl_EPG_row">
                    <td><time datetime="09:00">09:00</time></td>
                    <td><time datetime="10:00">10:00</time></td>
                    <td><span>Programa 2</span></td>
                </tr>
            </table>
            """
            mock_get.return_value = mock_response

            channel = next(ch for ch in self.config['channels'] if ch['scraper'] == 'gatotv')
            programs = self.gatotv.fetch_programs(channel)
            
            if len(programs) > 1:
                for i in range(len(programs) - 1):
                    current = datetime.strptime(programs[i]['start'], '%Y%m%d%H%M%S')
                    next_prog = datetime.strptime(programs[i + 1]['start'], '%Y%m%d%H%M%S')
                    self.assertLessEqual(current, next_prog)

if __name__ == '__main__':
    unittest.main()
