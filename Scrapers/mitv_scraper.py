import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging


class MiTVScraper:
    def __init__(self, config):
        self.headers = config.get("headers", {"User-Agent": "Mozilla/5.0"})
        
        # Si estamos en modo semana completa (para pruebas)
        if config.get("is_full_week_mode", False):
            self.days_to_scrape = 7
            logging.info("[Mi.TV] 🔧 MODO PRUEBA: Configurado para SEMANA COMPLETA - scrapeando 7 días")
        # Si estamos en modo fin de semana, usar esa configuración
        elif config.get("is_weekend_mode", False):
            self.days_to_scrape = config.get("days_to_scrape", 2)
            logging.info("[Mi.TV] Configurado en modo FIN DE SEMANA - scrapeando sábado y domingo")
        else:
            self.days_to_scrape = config.get("days_to_scrape", 3)
            logging.info(f"[Mi.TV] Configurado en modo NORMAL - scrapeando {self.days_to_scrape} día(s)")
            
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours", 6))

    def fetch_programs(self, channel_config):
        """
        Obtiene la programación de un canal específico desde mi.tv.
        """
        site_id = channel_config["site_id"]
        url_base = f"https://mi.tv/co/canales/{site_id}"
        programas_temp = []
        
        # Obtener la fecha local actual
        today_local = (datetime.utcnow() - self.timezone_offset).date()
        current_weekday = today_local.weekday()  # 0=Lunes, 6=Domingo
        
        # Si estamos en modo semana completa, empezar desde el lunes de esta semana
        if hasattr(self, 'days_to_scrape') and self.days_to_scrape == 7:
            # Calcular el lunes de esta semana
            monday_this_week = today_local - timedelta(days=current_weekday)
            start_date = monday_this_week
            logging.info(f"[Mi.TV] Modo semana completa: iniciando desde lunes {start_date.strftime('%Y-%m-%d')}")
        else:
            # Modo normal: empezar desde hoy
            start_date = today_local

        for i in range(self.days_to_scrape):
            fecha_local = start_date + timedelta(days=i)
            url = f"{url_base}?fecha={fecha_local.strftime('%Y-%m-%d')}"
            
            # Determinar qué día estamos scrapeando para el log
            day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha_local.weekday()]
            
            try:
                logging.info(f"[Mi.TV] Scrapeando {day_name} {fecha_local.strftime('%Y-%m-%d')} para '{channel_config['nombre']}'")
                
                # FIX: Usar self.headers["User-Agent"] en lugar de self.user_agent
                res = requests.get(url, headers={"User-Agent": self.headers["User-Agent"]}, timeout=15)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                
                programs_found = 0
                for prog in soup.select("article.program-item"):
                    time_tag = prog.find("time")
                    title_tag = prog.find("h3")
                    if not time_tag or not title_tag: continue

                    start_local = datetime.strptime(time_tag.text.strip(), "%H:%M")
                    start_dt = datetime.combine(fecha_local, start_local.time())
                    
                    programas_temp.append({
                        "title": title_tag.text.strip(),
                        "start_dt": start_dt,
                        "day": day_name
                    })
                    programs_found += 1
                
                logging.info(f"[Mi.TV] ✓ {programs_found} programas encontrados para {day_name}")
                
            except Exception as e:
                logging.error(f"[Mi.TV] Error en '{channel_config['nombre']}' para {day_name} ({url}): {e}")
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