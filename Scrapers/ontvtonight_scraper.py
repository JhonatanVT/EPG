import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time
import logging
import re

class OnTVTonightScraper:
    def __init__(self, config):
        self.headers = config.get("headers", {"User-Agent": "Mozilla/5.0"})
        self.days_to_scrape = config.get("days_to_scrape", 1)
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours", 5))
        
        if self.days_to_scrape > 1:
            logging.warning("[OnTVTonight] Este scraper solo soporta 1 día de EPG. Se usará solo el día actual.")
            self.days_to_scrape = 1
            
        logging.info(f"[OnTVTonight] Configurado en modo NORMAL - scrapeando {self.days_to_scrape} día(s)")
        logging.info(f"[OnTVTonight] Usando zona horaria UTC-{config.get('timezone_offset_hours', 5)}")

    def fetch_programs(self, channel_config):
        url = channel_config["url"]
        all_programs = []
        
        today_local = (datetime.utcnow() - self.timezone_offset).date()
        day_name = today_local.strftime('%A')
        
        try:
            logging.info(f"[OnTVTonight] Scrapeando {day_name} para '{channel_config['nombre']}' desde {url}")
            res = requests.get(url, headers=self.headers, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            # MEJORA: Selector más específico para la tabla de programación
            schedule_table = soup.select_one("table.table-striped")
            if not schedule_table:
                logging.warning(f"[OnTVTonight] No se encontró la tabla de programación en {url}")
                return []

            programs_for_day = []
            for row in schedule_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) == 2:
                    time_str = cells[0].get_text(strip=True)
                    title = cells[1].get_text(strip=True)
                    
                    try:
                        parsed_time = datetime.strptime(time_str, "%I:%M %p").time()
                    except ValueError:
                        logging.debug(f"[OnTVTonight] No se pudo parsear la hora: {time_str}")
                        continue
                        
                    start_dt = datetime.combine(today_local, parsed_time)
                    
                    programs_for_day.append({
                        "title": title,
                        "description": "", # No description available
                        "start_dt": start_dt
                    })

            if programs_for_day:
                all_programs.extend(self.calculate_program_durations(programs_for_day, today_local))

        except Exception as e:
            logging.error(f"[OnTVTonight] Error en '{channel_config['nombre']}' para {day_name}: {e}")
        
        return all_programs

    def calculate_program_durations(self, daily_programs, current_date):
        processed_programs = []
        
        # Handle day transitions for start times
        for i in range(len(daily_programs) - 1):
            if daily_programs[i+1]['start_dt'] < daily_programs[i]['start_dt']:
                daily_programs[i+1]['start_dt'] += timedelta(days=1)

        for i, prog in enumerate(daily_programs):
            start_dt_local = prog['start_dt']
            
            if i + 1 < len(daily_programs):
                stop_dt_local = daily_programs[i+1]['start_dt']
            else:
                # For the last program, assume a 1-hour duration
                stop_dt_local = start_dt_local + timedelta(hours=1)
                logging.debug(f"[OnTVTonight] Duración del último programa ('{prog['title']}') asumida en 1 hora.")

            start_utc = start_dt_local + self.timezone_offset
            stop_utc = stop_dt_local + self.timezone_offset

            program_data = {
                "title": prog["title"],
                "description": prog["description"],
                "start": start_utc.strftime("%Y%m%d%H%M%S +0000"),
                "stop": stop_utc.strftime("%Y%m%d%H%M%S +0000")
            }
            processed_programs.append(program_data)
            
        return processed_programs
