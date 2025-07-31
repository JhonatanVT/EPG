from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
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
        """
        Obtiene la programación de un canal específico desde GatoTV.
        """
        url_base = channel_config["url"]
        programas = []
        driver = None

        try:
            # Inicia el navegador Brave
            # Le decimos a webdriver-manager que busque el driver para Brave
            driver = webdriver.Chrome(
                # Esta línea es la que faltaba. Le dice a Selenium dónde está el driver.
                service=ChromeService(ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()),
                options=self.brave_options
            )

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
                
                if not program_rows:
                    # Esta es la línea corregida. Ya no causa un error.
                    logging.warning(f"[GatoTV] No se encontraron programas en {url}. La página podría haber cambiado.")
                    continue

                for row in program_rows:
                    cols = row.find_all("td")
                    if len(cols) < 3: continue
                    
                    hora_inicio = cols[0].find("time")
                    hora_fin = cols[1].find("time")
                    if not hora_inicio or not hora_fin: continue

                    start_local = datetime.strptime(hora_inicio.get("datetime"), "%H:%M")
                    end_local = datetime.strptime(hora_fin.get("datetime"), "%H:%M")
                    start_dt = datetime.combine(fecha_local, start_local.time())
                    end_dt = datetime.combine(fecha_local, end_local.time())
                    if end_dt < start_dt: end_dt += timedelta(days=1)

                    # ¡Aquí está tu idea en acción! Buscamos la descripción.
                    desc_tag = cols[2].find("div", class_="hidden-xs")
                    descripcion = desc_tag.text.strip() if desc_tag else ""

                    programas.append({
                        "title": cols[2].find("span").text.strip() if cols[2].find("span") else "Sin título",
                        "description": descripcion,
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

