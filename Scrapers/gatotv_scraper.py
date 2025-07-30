from datetime import datetime, timedelta
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# webdriver-manager se encargará de descargar el driver correcto para Brave
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType

class GatoTVScraper:
    def __init__(self, config):
        self.days_to_scrape = config.get("days_to_scrape", 3)
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours", 6))
        
        # Configuración para que Selenium con Brave funcione en GitHub Actions
        self.brave_options = webdriver.ChromeOptions()
        self.brave_options.add_argument("--headless") # No abrir una ventana visible del navegador
        self.brave_options.add_argument("--no-sandbox")
        self.brave_options.add_argument("--disable-dev-shm-usage")
        self.brave_options.add_argument("--disable-gpu")
        self.brave_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


    def fetch_programs(self, channel_config):
        driver = None

        try:
            # Inicia el navegador Brave
            # Le decimos a webdriver-manager que busque el driver para Brave
            driver = webdriver.Chrome(
                options=self.brave_options,
            )

            for i in range(self.days_to_scrape):
                fecha_local = (datetime.utcnow() - self.timezone_offset).date() + timedelta(days=i)

