import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging

class GatoTVScraper:
    def __init__(self, config):
        self.headers = config.get("headers", {"User-Agent": "Mozilla/5.0"})
        
        # Si estamos en modo semana completa (para pruebas)
        if config.get("is_full_week_mode", False):
            self.days_to_scrape = 7
            logging.info("[GatoTV] 🔧 MODO PRUEBA: Configurado para SEMANA COMPLETA - scrapeando 7 días")
        # Si estamos en modo fin de semana, usar esa configuración
        elif config.get("is_weekend_mode", False):
            self.days_to_scrape = config.get("days_to_scrape", 2)
            logging.info("[GatoTV] Configurado en modo FIN DE SEMANA - scrapeando sábado y domingo")
        else:
            self.days_to_scrape = config.get("days_to_scrape", 1)
            logging.info(f"[GatoTV] Configurado en modo NORMAL - scrapeando {self.days_to_scrape} día(s)")
            
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours", 6))

    def fetch_programs(self, channel_config):
        """
        Obtiene la programación de un canal específico desde GatoTV.
        """
        url_base = channel_config["url"]
        programas = []
        
        # Obtener la fecha local actual
        today_local = (datetime.utcnow() - self.timezone_offset).date()
        current_weekday = today_local.weekday()  # 0=Lunes, 6=Domingo
        
        # Si estamos en modo semana completa, empezar desde el lunes de esta semana
        if hasattr(self, 'days_to_scrape') and self.days_to_scrape == 7:
            # Calcular el lunes de esta semana
            monday_this_week = today_local - timedelta(days=current_weekday)
            start_date = monday_this_week
            logging.info(f"[GatoTV] Modo semana completa: iniciando desde lunes {start_date.strftime('%Y-%m-%d')}")
        else:
            # Modo normal: empezar desde hoy
            start_date = today_local

        for i in range(self.days_to_scrape):
            fecha_local = start_date + timedelta(days=i)
            url = f"{url_base}?fecha={fecha_local.strftime('%Y-%m-%d')}"
            
            # Determinar qué día estamos scrapeando para el log
            day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha_local.weekday()]
            
            try:
                logging.info(f"[GatoTV] Scrapeando {day_name} {fecha_local.strftime('%Y-%m-%d')} para '{channel_config['nombre']}'")
                
                res = requests.get(url, headers=self.headers, timeout=15)
                res.raise_for_status()
                res.encoding = 'utf-8'
                soup = BeautifulSoup(res.text, "html.parser")

                # CLAVE: Buscamos la tabla principal primero, como hace iptv-org
                epg_table = soup.find("table", class_="tbl_EPG")
                
                if not epg_table:
                    logging.warning(f"[GatoTV] No se encontró la tabla principal de EPG en {url}. La estructura de la página pudo haber cambiado.")
                    continue
                
                # Ahora buscamos las filas dentro de esa tabla específica
                program_rows = epg_table.select("tr.tbl_EPG_row, tr.tbl_EPG_rowAlternate, tr.tbl_EPG_row_selected")
                
                if not program_rows:
                    logging.warning(f"[GatoTV] Se encontró la tabla EPG, pero no contenía programas en {url}.")
                    continue

                programs_found = 0
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

                    desc_tag = cols[2].find("div", class_="hidden-xs")
                    descripcion = desc_tag.text.strip() if desc_tag else ""

                    programas.append({
                        "title": cols[2].find("span").text.strip() if cols[2].find("span") else "Sin título",
                        "description": descripcion,
                        "start": (start_dt + self.timezone_offset).strftime("%Y%m%d%H%M%S +0000"),
                        "stop": (end_dt + self.timezone_offset).strftime("%Y%m%d%H%M%S +0000")
                    })
                    programs_found += 1
                
                logging.info(f"[GatoTV] ✓ {programs_found} programas encontrados para {day_name}")
                
            except Exception as e:
                logging.error(f"[GatoTV] Error en '{channel_config['nombre']}' para {day_name} ({url}): {e}")
                continue
                
        return programas