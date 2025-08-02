import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re

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
            # MEJORA: Consistencia con GatoTV - usar 1 día por defecto
            self.days_to_scrape = config.get("days_to_scrape", 1)
            logging.info(f"[Mi.TV] Configurado en modo NORMAL - scrapeando {self.days_to_scrape} día(s)")
            
        # MEJORA: Usar configuración consistente de zona horaria
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours", 5))
        logging.info(f"[Mi.TV] Usando zona horaria UTC-{config.get('timezone_offset_hours', 5)}")

    def validate_site_structure(self, soup, url):
        """Valida que la estructura del sitio no haya cambiado"""
        expected_elements = [
            "article.program-item",
            "time",
            "h3"
        ]
        
        for element in expected_elements:
            if not soup.select(element):
                logging.error(f"[Mi.TV] ESTRUCTURA CAMBIADA: No se encontró '{element}' en {url}")
                return False
        return True

    def parse_program_info(self, prog_elem):
        """Extrae información del programa con validación mejorada"""
        try:
            # Extraer hora
            time_tag = prog_elem.find("time")
            if not time_tag:
                logging.debug("[Mi.TV] Programa sin elemento time")
                return None
            
            time_text = time_tag.get_text(strip=True)
            if not re.match(r'^\d{2}:\d{2}$', time_text):
                logging.debug(f"[Mi.TV] Formato de hora inválido: {time_text}")
                return None
            
            # Extraer título
            title_tag = prog_elem.find("h3")
            if not title_tag:
                logging.debug("[Mi.TV] Programa sin elemento h3 (título)")
                return None
            
            title = title_tag.get_text(strip=True)
            if not title:
                logging.debug("[Mi.TV] Programa con título vacío")
                return None
            
            # Extraer descripción si está disponible
            description = ""
            desc_elem = prog_elem.find("p", class_="program-description")
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                # Limpiar espacios extra
                description = re.sub(r'\s+', ' ', description)
            
            # Extraer imagen si está disponible
            image = ""
            img_elem = prog_elem.find("img")
            if img_elem:
                src = img_elem.get('src')
                if src and not src.startswith('http'):
                    # Convertir a URL absoluta
                    src = f"https://mi.tv{src}"
                image = src
            
            return {
                "time": time_text,
                "title": title,
                "description": description,
                "image": image
            }
            
        except Exception as e:
            logging.debug(f"[Mi.TV] Error parseando programa: {e}")
            return None

    def calculate_program_durations(self, programs_temp):
        """Calcula la duración de cada programa basándose en el siguiente"""
        if not programs_temp:
            return []
        
        programas_finales = []
        
        for i, prog in enumerate(programs_temp):
            start_utc = prog['start_dt'] + self.timezone_offset
            
            # Calcular hora de fin
            if i + 1 < len(programs_temp):
                # Usar inicio del siguiente programa como fin
                stop_utc = programs_temp[i + 1]['start_dt'] + self.timezone_offset
            else:
                # Para el último programa, asumir 1 hora de duración
                stop_utc = start_utc + timedelta(hours=1)
            
            # Validar que stop sea después de start
            if stop_utc <= start_utc:
                stop_utc = start_utc + timedelta(hours=1)
                logging.debug(f"[Mi.TV] Ajustada duración para '{prog['title']}' - stop ajustado a +1 hora")
            
            program_data = {
                "title": prog["title"],
                "start": start_utc.strftime("%Y%m%d%H%M%S +0000"),
                "stop": stop_utc.strftime("%Y%m%d%H%M%S +0000")
            }
            
            # Añadir descripción e imagen si están disponibles
            if prog.get("description"):
                program_data["description"] = prog["description"]
            if prog.get("image"):
                program_data["image"] = prog["image"]
            
            programas_finales.append(program_data)
        
        return programas_finales

    def fetch_programs(self, channel_config):
        """
        Obtiene la programación de un canal específico desde mi.tv con mejoras.
        """
        site_id = channel_config["site_id"]
        url_base = f"https://mi.tv/co/canales/{site_id}"
        programas_temp = []
        
        # Obtener la fecha local actual
        today_local = (datetime.utcnow() - self.timezone_offset).date()
        current_weekday = today_local.weekday()
        
        # Si estamos en modo semana completa, empezar desde el lunes de esta semana
        if hasattr(self, 'days_to_scrape') and self.days_to_scrape == 7:
            monday_this_week = today_local - timedelta(days=current_weekday)
            start_date = monday_this_week
            logging.info(f"[Mi.TV] Modo semana completa: iniciando desde lunes {start_date.strftime('%Y-%m-%d')}")
        else:
            start_date = today_local

        for i in range(self.days_to_scrape):
            fecha_local = start_date + timedelta(days=i)
            url = f"{url_base}?fecha={fecha_local.strftime('%Y-%m-%d')}"
            
            day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha_local.weekday()]
            
            try:
                logging.info(f"[Mi.TV] Scrapeando {day_name} {fecha_local.strftime('%Y-%m-%d')} para '{channel_config['nombre']}'")
                
                # MEJORA: Usar headers completos
                res = requests.get(url, headers=self.headers, timeout=15)
                res.raise_for_status()
                res.encoding = 'utf-8'
                soup = BeautifulSoup(res.text, "html.parser")
                
                # MEJORA: Validar estructura antes de procesar
                if not self.validate_site_structure(soup, url):
                    logging.error(f"[Mi.TV] Saltando {day_name} por cambio en estructura del sitio")
                    continue
                
                programs_found = 0
                daily_programs = []
                
                for prog in soup.select("article.program-item"):
                    program_info = self.parse_program_info(prog)
                    if not program_info:
                        continue
                    
                    try:
                        start_local = datetime.strptime(program_info["time"], "%H:%M")
                        start_dt = datetime.combine(fecha_local, start_local.time())
                        
                        daily_programs.append({
                            "title": program_info["title"],
                            "description": program_info["description"],
                            "image": program_info["image"],
                            "start_dt": start_dt,
                            "day": day_name
                        })
                        programs_found += 1
                        
                    except ValueError as e:
                        logging.warning(f"[Mi.TV] Error parseando hora '{program_info['time']}': {e}")
                        continue
                
                # Añadir programas del día a la lista temporal
                programas_temp.extend(daily_programs)
                
                logging.info(f"[Mi.TV] ✓ {programs_found} programas encontrados para {day_name}")
                
            except requests.RequestException as e:
                logging.error(f"[Mi.TV] Error de conexión en '{channel_config['nombre']}' para {day_name}: {e}")
                continue
            except Exception as e:
                logging.error(f"[Mi.TV] Error en '{channel_config['nombre']}' para {day_name} ({url}): {e}")
                continue
        
        # MEJORA: Calcular duraciones de programas
        programas_finales = self.calculate_program_durations(programas_temp)
        
        logging.info(f"[Mi.TV] Total de programas procesados para '{channel_config['nombre']}': {len(programas_finales)}")
        
        return programas_finales