import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urlparse, urljoin

class OnTVTonightScraper:
    def __init__(self, config):
        self.base_url = "https://www.ontvtonight.com"
        self.headers = config.get("headers", {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
        self.config = config
        self.timeout = config.get("timeout", 15)
        
        # Configuración de días
        self.days_to_scrape = self._get_days_to_scrape(config)
        
        # Configurar sesión HTTP con reintentos
        self.session = self._setup_session()

    def _get_days_to_scrape(self, config):
        """Determina los días a scrapear basado en la configuración"""
        if config.get("is_full_week_mode", False):
            logging.info("[OnTVTonight] Modo semana completa (7 días)")
            return 7
        elif config.get("is_weekend_mode", False):
            days = config.get("days_to_scrape", 2)
            logging.info(f"[OnTVTonight] Modo fin de semana ({days} días)")
            return days
        else:
            days = config.get("days_to_scrape", 1)
            logging.info(f"[OnTVTonight] Modo normal ({days} día(s))")
            return days

    def _setup_session(self):
        """Configura la sesión HTTP con reintentos"""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def validate_url(self, url):
        """Valida que una URL sea válida"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def validate_page_structure(self, soup, url):
        """Valida que la estructura de la página sea correcta"""
        required_elements = [
            ".schedule-grid",
            ".schedule-entry"
        ]
        
        for selector in required_elements:
            if not soup.select(selector):
                logging.error(f"[OnTVTonight] Estructura inválida - No se encontró: {selector}")
                logging.error(f"[OnTVTonight] URL: {url}")
                return False
        return True

    def parse_time(self, time_str, fecha_local):
        """Parsea tiempo con manejo de errores mejorado"""
        try:
            # Formato esperado: "8:00 PM" o "11:30 AM"
            time_obj = datetime.strptime(time_str.strip(), "%I:%M %p")
            return datetime.combine(fecha_local, time_obj.time())
        except ValueError as e:
            logging.error(f"[OnTVTonight] Error parseando tiempo '{time_str}': {e}")
            return None

    def parse_program_details(self, entry):
        """Extrae detalles del programa con validación mejorada"""
        title = entry.select_one(".show-title")
        desc = entry.select_one(".show-description")
        img = entry.select_one("img")
        
        return {
            'title': title.get_text(strip=True) if title else "Sin título",
            'description': desc.get_text(strip=True) if desc else "",
            'image': urljoin(self.base_url, img['src']) if img and img.get('src') else ""
        }

    def handle_day_transition(self, programs):
        """Maneja transiciones entre días"""
        if not programs:
            return programs
            
        for i in range(len(programs)-1):
            current = programs[i]
            next_prog = programs[i+1]
            
            if next_prog['start_dt'] < current['stop_dt']:
                next_prog['start_dt'] += timedelta(days=1)
                next_prog['stop_dt'] += timedelta(days=1)
                next_prog['start'] = next_prog['start_dt'].strftime("%Y%m%d%H%M%S")
                next_prog['stop'] = next_prog['stop_dt'].strftime("%Y%m%d%H%M%S")
        
        return programs

    def fetch_programs(self, channel_config):
        """Obtiene la programación de un canal específico"""
        url_base = channel_config.get("url")
        if not self.validate_url(url_base):
            logging.error(f"[OnTVTonight] URL inválida: {url_base}")
            return []

        all_programs = []
        
        # Configuración de zona horaria
        tz_override = channel_config.get("timezone_override")
        offset_hours = tz_override if tz_override is not None else self.config.get("timezone_offset_hours", 6)
        timezone_offset = timedelta(hours=offset_hours)
        
        today_local = (datetime.now(timezone.utc) - timezone_offset).date()
        
        for day_offset in range(self.days_to_scrape):
            fecha_local = today_local + timedelta(days=day_offset)
            url = f"{url_base}/{fecha_local.strftime('%Y-%m-%d')}"
            
            try:
                response = self.session.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                if not self.validate_page_structure(soup, url):
                    continue
                
                daily_programs = []
                entries = soup.select(".schedule-entry")
                
                for entry in entries:
                    time_elem = entry.select_one(".schedule-time")
                    duration_elem = entry.select_one(".duration")
                    
                    if not time_elem or not duration_elem:
                        continue
                        
                    start_time = self.parse_time(time_elem.get_text(), fecha_local)
                    if not start_time:
                        continue
                    
                    # Extraer duración en minutos
                    duration_match = re.search(r'(\d+)\s*min', duration_elem.get_text())
                    if not duration_match:
                        continue
                    
                    duration = int(duration_match.group(1))
                    stop_time = start_time + timedelta(minutes=duration)
                    
                    program_details = self.parse_program_details(entry)
                    program = {
                        'start_dt': start_time,
                        'stop_dt': stop_time,
                        'start': start_time.strftime("%Y%m%d%H%M%S"),
                        'stop': stop_time.strftime("%Y%m%d%H%M%S"),
                        **program_details
                    }
                    
                    daily_programs.append(program)
                
                # Manejar transiciones de día
                daily_programs = self.handle_day_transition(daily_programs)
                all_programs.extend(daily_programs)
                
                logging.info(f"[OnTVTonight] Procesados {len(daily_programs)} programas para {fecha_local}")
                
            except requests.RequestException as e:
                logging.error(f"[OnTVTonight] Error de red en {url}: {e}")
            except Exception as e:
                logging.error(f"[OnTVTonight] Error procesando {url}: {e}")
        
        return all_programs
