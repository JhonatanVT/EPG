from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class GatoTVScraper:
    def __init__(self, config):
        self.days_to_scrape = config.get("days_to_scrape", 3)
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours", 6))
        
        # Configuración para que Selenium funcione en GitHub Actions
        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument("--headless") # No abrir una ventana visible del navegador
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


    def fetch_programs(self, channel_config):
        """
        """
        url_base = channel_config["url"]
        programas = []
        driver = None

        try:
            # Inicia el navegador
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.chrome_options)

            for i in range(self.days_to_scrape):
                fecha_local = (datetime.utcnow() - self.timezone_offset).date() + timedelta(days=i)
                url = f"{url_base}?fecha={fecha_local.strftime('%Y-%m-%d')}"
                
                driver.get(url)
                
                # Espera hasta 10 segundos a que la tabla de programas aparezca
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tr.tbl_EPG_row, tr.tbl_EPG_rowAlternate"))
                )

                # Ahora que la página está cargada, obtenemos el HTML y lo procesamos
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                program_rows = soup.select("tr.tbl_EPG_row, tr.tbl_EPG_rowAlternate, tr.tbl_EPG_row_selected")
                
                        "start": (start_dt + self.timezone_offset).strftime("%Y%m%d%H%M%S +0000"),
                        "stop": (end_dt + self.timezone_offset).strftime("%Y%m%d%H%M%S +0000")
                    })
        except Exception as e:
            logging.error(f"[GatoTV] Error procesando '{channel_config['nombre']}': {e}")
        finally:
            # Asegúrate de que el navegador siempre se cierre
            if driver:
                driver.quit()

        return programas



