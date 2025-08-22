import unittest
import sys
import os
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scrapers.gatotv_scraper import GatoTVScraper
from Scrapers.ontvtonight_scraper import OnTVTonightScraper

class TestScrapers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Configuración inicial para todos los tests"""
        with open('config.json', 'r', encoding='utf-8') as f:
            cls.config = json.load(f)
        cls.gatotv_channel = next(ch for ch in cls.config['channels'] 
                                if ch['scraper'] == 'gatotv')
        cls.ontvtonight_channel = next(ch for ch in cls.config['channels'] 
                                     if ch['scraper'] == 'ontvtonight')

    def setUp(self):
        """Configuración para cada test individual"""
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

    def test_gatotv_fetch_programs(self):
        """Verifica la obtención de programas de GatoTV"""
        programs = self.gatotv.fetch_programs(self.gatotv_channel)
        self.assertIsNotNone(programs)
        self.assertTrue(len(programs) > 0)
        
        # Verificar estructura de programa
        program = programs[0]
        required_fields = ['start', 'stop', 'title']
        for field in required_fields:
            self.assertIn(field, program)

    def test_ontvtonight_fetch_programs(self):
        """Verifica la obtención de programas de OnTVTonight"""
        programs = self.ontvtonight.fetch_programs(self.ontvtonight_channel)
        self.assertIsNotNone(programs)
        self.assertTrue(len(programs) > 0)
        
        # Verificar estructura de programa
        program = programs[0]
        required_fields = ['start', 'stop', 'title']
        for field in required_fields:
            self.assertIn(field, program)

    def test_program_date_format(self):
        """Verifica el formato de fechas en los programas"""
        programs = self.gatotv.fetch_programs(self.gatotv_channel)
        if programs:
            program = programs[0]
            # Verificar formato YYYYMMDDHHMMSS
            self.assertTrue(len(program['start']) == 14)
            self.assertTrue(len(program['stop']) == 14)
            # Verificar que las fechas sean válidas
            datetime.strptime(program['start'], '%Y%m%d%H%M%S')
            datetime.strptime(program['stop'], '%Y%m%d%H%M%S')

    def test_program_time_sequence(self):
        """Verifica que los tiempos sean secuenciales"""
        programs = self.gatotv.fetch_programs(self.gatotv_channel)
        if len(programs) > 1:
            for i in range(len(programs) - 1):
                current = datetime.strptime(programs[i]['start'], '%Y%m%d%H%M%S')
                next_prog = datetime.strptime(programs[i + 1]['start'], '%Y%m%d%H%M%S')
                self.assertLessEqual(current, next_prog)

    def test_url_validation(self):
        """Verifica la validación de URLs"""
        invalid_urls = [
            "not_a_url",
            "http:/invalid.com",
            "ftp://invalid.com",
            ""
        ]
        for url in invalid_urls:
            self.assertFalse(self.gatotv.validate_url(url))
            self.assertFalse(self.ontvtonight.validate_url(url))

    def test_timezone_handling(self):
        """Verifica el manejo de zonas horarias"""
        programs = self.gatotv.fetch_programs(self.gatotv_channel)
        if programs:
            program = programs[0]
            start_dt = datetime.strptime(program['start'], '%Y%m%d%H%M%S')
            stop_dt = datetime.strptime(program['stop'], '%Y%m%d%H%M%S')
            # Verificar que stop sea después de start
            self.assertGreater(stop_dt, start_dt)
            # Verificar que la diferencia no sea mayor a 24 horas
            self.assertLess(stop_dt - start_dt, timedelta(hours=24))

    def test_error_handling(self):
        """Verifica el manejo de errores"""
        invalid_channel = {
            "url": "https://www.gatotv.com/canal/invalid_channel",
            "site_id": "invalid"
        }
        # No debería lanzar excepción, sino retornar lista vacía
        programs = self.gatotv.fetch_programs(invalid_channel)
        self.assertEqual(programs, [])

if __name__ == '__main__':
    unittest.main()
