import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urlparse

class GatoTVScraper:
    def __init__(self, config):
        self.headers = config.get("headers", {"User-Agent": "Mozilla/5.0"})
        self.config = config
        self.timeout = config.get("timeout", 15)
        
        # Configuración de días a scrapear
        if config.get("is_full_week_mode", False):
            self.days_to_scrape = 7
            logging.info("[GatoTV] INFO: MODO PRUEBA: Configurado para SEMANA COMPLETA")
        elif config.get("is_weekend_mode", False):
            self.days_to_scrape = config.get("days_to_scrape", 2)
            logging.info("[GatoTV] Configurado en modo FIN DE SEMANA")
        else:
            self.days_to_scrape = config.get("days_to_scrape", 1)
            logging.info(f"[GatoTV] Configurado en modo NORMAL - {self.days_to_scrape} día(s)")

        # Configuración de sesión HTTP con reintentos
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def validate_site_structure(self, soup, url):
        """Valida que la estructura del sitio no haya cambiado"""
        expected_elements = [
            "table.tbl_EPG",
            "tr.tbl_EPG_row, tr.tbl_EPG_rowAlternate, tr.tbl_EPG_row_selected"
        ]
        
        for element in expected_elements:
            if not soup.select(element):
                logging.error(f"[GatoTV] Estructura del sitio cambió - No se encontró: {element}")
                logging.error(f"[GatoTV] URL: {url}")
                return False
        return True

    def parse_title(self, row):
        """Extrae el título usando múltiples selectores"""
        selectors = [
            'td:nth-child(4) > div > div > a > span',
            'td:nth-child(3) > div > div > span', 
            'td:nth-child(3) > div > div > a > span',
            'td:nth-child(3) span',
        ]
        
        for selector in selectors:
            title_elem = row.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                return title_elem.get_text(strip=True)
        
        spans = row.select('td:nth-child(3) span, td:nth-child(4) span')
        for span in spans:
            text = span.get_text(strip=True)
            if text and len(text) > 2:
                return text
                
        return "Sin título"

    def parse_description(self, row):
        """Extrae descripción con limpieza mejorada"""
        desc_selectors = [
            'td:nth-child(4) > div > div.hidden-xs',
            'td:nth-child(3) > div > div.hidden-xs',
            'td:nth-child(4) div.hidden-xs',
            'td:nth-child(3) div.hidden-xs'
        ]
        
        for selector in desc_selectors:
            desc_elem = row.select_one(selector)
            if desc_elem:
                desc = desc_elem.get_text(strip=True)
                if desc:
                    return desc.replace('\n', ' ').strip()
        
        return ""

    def parse_image(self, row):
        """Extrae URL de imagen del programa si está disponible"""
        try:
            img_elem = row.select_one('td:nth-child(3) > a > img')
            if img_elem and img_elem.get('src'):
                return img_elem['src']
        except Exception as e:
            logging.warning(f"[GatoTV] Error extrayendo imagen: {e}")
        return ""

    def parse_time_with_validation(self, time_elem, fecha_local, column_name):
        """Parsea tiempo con validación mejorada"""
        if not time_elem:
            logging.warning(f"[GatoTV] No se encontró elemento time en {column_name}")
            return None
            
        datetime_attr = time_elem.get("datetime")
        if not datetime_attr:
            time_text = time_elem.get_text(strip=True)
            if re.match(r'^\d{2}:\d{2}', time_text):
                datetime_attr = time_text
            else:
                logging.error(f"[GatoTV] Formato de tiempo inválido: {time_text}")
                return None
        
        try:
            time_local = datetime.strptime(datetime_attr, "%H:%M")
            return datetime.combine(fecha_local, time_local.time())
        except ValueError as e:
            logging.error(f"[GatoTV] Error parseando tiempo '{datetime_attr}' en {column_name}: {e}")
            return None

    def handle_day_transitions(self, programs_list):
        """Maneja transiciones de día"""
        if not programs_list:
            return programs_list
            
        for i, prog in enumerate(programs_list):
            start_dt = prog['start_dt']
            stop_dt = prog['stop_dt']
            
            if stop_dt < start_dt:
                # El programa termina al día siguiente
                stop_dt = stop_dt + timedelta(days=1)
                prog['stop_dt'] = stop_dt
                prog['stop'] = stop_dt.strftime("%Y%m%d%H%M%S")
        
        return programs_list

    def validate_url(self, url):
        """Valida que una URL sea válida"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def fetch_programs(self, channel_config):
        """Obtiene la programación de un canal específico"""
        url_base = channel_config["url"]
        if not self.validate_url(url_base):
            logging.error(f"[GatoTV] URL inválida: {url_base}")
            return []

        programas = []
        
        # Configuración de zona horaria
        tz_override = channel_config.get("timezone_override")
        global_offset_hours = self.config.get("timezone_offset_hours", 6)

        if tz_override is not None:
            offset_hours = tz_override
            logging.info(f"[GatoTV] Usando zona horaria específica del canal: UTC-{offset_hours}")
        else:
            offset_hours = global_offset_hours
            logging.info(f"[GatoTV] Usando zona horaria global: UTC-{offset_hours}")
        
        timezone_offset = timedelta(hours=offset_hours)
        
        # Cálculo de fechas
        today_local = (datetime.now(timezone.utc) - timezone_offset).date()
        current_weekday = today_local.weekday()
        
        if hasattr(self, 'days_to_scrape') and self.days_to_scrape == 7:
            monday_this_week = today_local - timedelta(days=current_weekday)
            start_date = monday_this_week
            logging.info(f"[GatoTV] Modo semana completa: iniciando desde lunes {start_date}")
        else:
            start_date = today_local

        # Procesar cada día
        for i in range(self.days_to_scrape):
            fecha_local = start_date + timedelta(days=i)
            url = f"{url_base}/{fecha_local.strftime('%Y-%m-%d')}"
            
            try:
                response = self.session.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                if not self.validate_site_structure(soup, url):
                    continue
                
                rows = soup.select("tr.tbl_EPG_row, tr.tbl_EPG_rowAlternate, tr.tbl_EPG_row_selected")
                daily_programs = []
                
                for row in rows:
                    start_time = self.parse_time_with_validation(
                        row.select_one("td:nth-child(2) time"),
                        fecha_local,
                        "inicio"
                    )
                    stop_time = self.parse_time_with_validation(
                        row.select_one("td:nth-child(3) time"),
                        fecha_local,
                        "fin"
                    )
                    
                    if not all([start_time, stop_time]):
                        continue
                    
                    program = {
                        'start_dt': start_time,
                        'stop_dt': stop_time,
                        'start': start_time.strftime("%Y%m%d%H%M%S"),
                        'stop': stop_time.strftime("%Y%m%d%H%M%S"),
                        'title': self.parse_title(row),
                        'description': self.parse_description(row),
                        'image': self.parse_image(row)
                    }
                    
                    daily_programs.append(program)
                
                # Manejar transiciones de día y añadir programas
                daily_programs = self.handle_day_transitions(daily_programs)
                programas.extend(daily_programs)
                
                logging.info(f"[GatoTV] Procesados {len(daily_programs)} programas para {fecha_local}")
                
            except requests.RequestException as e:
                logging.error(f"[GatoTV] Error descargando {url}: {e}")
            except Exception as e:
                logging.error(f"[GatoTV] Error procesando {url}: {e}")
                
        return programas