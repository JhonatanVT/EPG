import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging


class MiTVScraper:
    def __init__(self, config):
        self.headers = config.get("headers", {"User-Agent": "Mozilla/5.0"})
        self.days_to_scrape = config.get("days_to_scrape", 3)
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours", 6))

    def fetch_programs(self, channel_config):
        """
        Obtiene la programación de un canal específico desde mi.tv.
        """
        site_id = channel_config["site_id"]
        url_base = f"https://mi.tv/co/canales/{site_id}"
        programas_temp = []

        for i in range(self.days_to_scrape):
            fecha_local = (datetime.utcnow() - self.timezone_offset).date() + timedelta(days=i)
            url = f"{url_base}?fecha={fecha_local.strftime('%Y-%m-%d')}"
            try:
                res = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=15)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                for prog in soup.select("article.program-item"):
                    time_tag = prog.find("time")
                    title_tag = prog.find("h3")
                    if not time_tag or not title_tag: continue

                    start_local = datetime.strptime(time_tag.text.strip(), "%H:%M")
                    start_dt = datetime.combine(fecha_local, start_local.time())
                    
                    programas_temp.append({
                        "title": title_tag.text.strip(),
                        "start_dt": start_dt
                    })
            except Exception as e:
                logging.error(f"[Mi.TV] Error en '{channel_config['nombre']}' ({url}): {e}")
                continue
        
        # Calcular la hora de fin para cada programa
        programas_finales = []
        for i, prog in enumerate(programas_temp):
            start_utc = prog['start_dt'] + self.timezone_offset
            stop_utc = (programas_temp[i+1]['start_dt'] + self.timezone_offset) if i + 1 < len(programas_temp) else (start_utc + timedelta(hours=1))
            programas_finales.append({
                "title": prog["title"],
                "start": start_utc.strftime("%Y%m%d%H%M%S +0000"),
                "stop": stop_utc.strftime("%Y%m%d%H%M%S +0000")
            })
        return programas_finales

