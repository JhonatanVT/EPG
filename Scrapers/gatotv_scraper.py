import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging

class GatoTVScraper:
    def __init__(self, config):
        self.headers = config.get("headers", {"User-Agent": "Mozilla/5.0"})
        self.days_to_scrape = config.get("days_to_scrape", 3)
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours", 6))

            url = f"{url_base}?fecha={fecha_local.strftime('%Y-%m-%d')}"
            
            try:
                res = requests.get(url, headers=self.headers, timeout=15)
                res.raise_for_status()
                res.encoding = 'utf-8'
                soup = BeautifulSoup(res.text, "html.parser")

    def fetch_programs(self, channel_config):
        """
        Obtiene la programación de un canal específico desde GatoTV.
        """
        url_base = channel_config["url"]
        programas = []

        for i in range(self.days_to_scrape):
            fecha_local = (datetime.utcnow() - self.timezone_offset).date() + timedelta(days=i)
            url = f"{url_base}?fecha={fecha_local.strftime('%Y-%m-%d')}"
            
            try:
                res = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=15)
                res.raise_for_status()
                res.encoding = 'utf-8'
                soup = BeautifulSoup(res.text, "html.parser")
                
                program_rows = soup.select("tr.tbl_EPG_row, tr.tbl_EPG_rowAlternate, tr.tbl_EPG_row_selected")
                
                if not program_rows:
                    logging.warning(f"[GatoTV] No se encontraron programas en {url}. La página podría haber cambiado. Contenido (primeros 300 chars): {res.text.strip()[:300]}")
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

                    programas.append({
                        "title": cols[2].find("span").text.strip() if cols[2].find("span") else "Sin título",
                        "start": (start_dt + self.timezone_offset).strftime("%Y%m%d%H%M%S +0000"),
                        "stop": (end_dt + self.timezone_offset).strftime("%Y%m%d%H%M%S +0000")
                    })
            except Exception as e:
                logging.error(f"[GatoTV] Error en '{channel_config['nombre']}' ({url}): {e}")
                continue
        return programas




