import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re

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
            
        # Usar la zona horaria definida en la configuración principal
        self.timezone_offset = timedelta(hours=config.get("timezone_offset_hours"))
        logging.info(f"[GatoTV] Usando zona horaria UTC-{config.get('timezone_offset_hours')} definida en la configuración")

    def validate_site_structure(self, soup, url):
        """Valida que la estructura del sitio no haya cambiado"""
        expected_elements = [
            "table.tbl_EPG",
            "tr.tbl_EPG_row, tr.tbl_EPG_rowAlternate, tr.tbl_EPG_row_selected"
        ]
        
        for element in expected_elements:
            if not soup.select(element):
                logging.error(f"[GatoTV] ESTRUCTURA CAMBIADA: No se encontró '{element}' en {url}")
                return False
        return True

    def parse_title(self, row):
        """Extrae el título usando múltiples selectores como iptv-org"""
        # Selectores múltiples basados en la implementación de referencia
        selectors = [
            'td:nth-child(4) > div > div > a > span',
            'td:nth-child(3) > div > div > span', 
            'td:nth-child(3) > div > div > a > span',
            'td:nth-child(3) span',  # Fallback más simple
        ]
        
        for selector in selectors:
            title_elem = row.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                return title_elem.get_text(strip=True)
        
        # Último recurso: buscar cualquier span en las columnas de contenido
        spans = row.select('td:nth-child(3) span, td:nth-child(4) span')
        for span in spans:
            text = span.get_text(strip=True)
            if text and len(text) > 2:  # Evitar spans vacíos o muy cortos
                return text
                
        return "Sin título"

    def parse_description(self, row):
        """Extrae descripción con limpieza mejorada"""
        # Buscar en la columna de descripción
        desc_selectors = [
            'td:nth-child(4) > div > div.hidden-xs',
            'td:nth-child(3) > div > div.hidden-xs',
            'td:nth-child(4) div.hidden-xs',
            'td:nth-child(3) div.hidden-xs'
        ]
        
        for selector in desc_selectors:
            desc_elem = row.select_one(selector)
            if desc_elem:
                # Limpiar texto de descripciones
                desc_text = desc_elem.get_text(strip=True)
                desc_text = re.sub(r'\s+', ' ', desc_text)  # Normalizar espacios
                if desc_text and len(desc_text) > 10:  # Solo descripciones con contenido
                    return desc_text
        
        return ""

    def parse_image(self, row):
        """Extrae URL de imagen del programa si está disponible"""
        try:
            img_elem = row.select_one('td:nth-child(3) > a > img')
            if img_elem:
                src = img_elem.get('src')
                if src and not src.startswith('http'):
                    # Convertir a URL absoluta
                    src = f"https://www.gatotv.com{src}"
                return src
        except:
            pass
        return ""

    def parse_time_with_validation(self, time_elem, fecha_local, column_name):
        """Parsea tiempo con validación mejorada"""
        if not time_elem:
            logging.warning(f"[GatoTV] No se encontró elemento time en {column_name}")
            return None
            
        datetime_attr = time_elem.get("datetime")
        if not datetime_attr:
            # Intentar extraer de texto si no hay atributo datetime
            time_text = time_elem.get_text(strip=True)
            if re.match(r'^\d{2}:\d{2}', time_text):
                datetime_attr = time_text
            else:
                logging.warning(f"[GatoTV] Formato de tiempo inválido en {column_name}: {time_text}")
                return None
        
        try:
            time_local = datetime.strptime(datetime_attr, "%H:%M")
            return datetime.combine(fecha_local, time_local.time())
        except ValueError as e:
            logging.error(f"[GatoTV] Error parseando tiempo '{datetime_attr}' en {column_name}: {e}")
            return None

    def handle_day_transitions(self, programs_list):
        """Maneja transiciones de día como en iptv-org"""
        if not programs_list:
            return programs_list
            
        for i, prog in enumerate(programs_list):
            start_dt = prog['start_dt']
            stop_dt = prog['stop_dt']
            
            # Si stop es menor que start, mover stop al día siguiente
            if stop_dt < start_dt:
                stop_dt = stop_dt + timedelta(days=1)
                prog['stop_dt'] = stop_dt
                logging.debug(f"[GatoTV] Hora fin movida al día siguiente para '{prog['title']}'")
        
        return programs_list

    def fetch_programs(self, channel_config):
        """
        Obtiene la programación de un canal específico desde GatoTV con mejoras basadas en iptv-org.
        """
        url_base = channel_config["url"]
        programas = []
        
        # Obtener la fecha local actual
        today_local = (datetime.utcnow() - self.timezone_offset).date()
        current_weekday = today_local.weekday()
        
        # Si estamos en modo semana completa, empezar desde el lunes de esta semana
        if hasattr(self, 'days_to_scrape') and self.days_to_scrape == 7:
            monday_this_week = today_local - timedelta(days=current_weekday)
            start_date = monday_this_week
            logging.info(f"[GatoTV] Modo semana completa: iniciando desde lunes {start_date.strftime('%Y-%m-%d')}")
        else:
            start_date = today_local

        for i in range(self.days_to_scrape):
            fecha_local = start_date + timedelta(days=i)
            # MEJORA: Usar formato de URL compatible con iptv-org
            url = f"{url_base}/{fecha_local.strftime('%Y-%m-%d')}"
            
            day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha_local.weekday()]
            
            try:
                logging.info(f"[GatoTV] Scrapeando {day_name} {fecha_local.strftime('%Y-%m-%d')} para '{channel_config['nombre']}'")
                
                res = requests.get(url, headers=self.headers, timeout=15)
                res.raise_for_status()
                res.encoding = 'utf-8'
                soup = BeautifulSoup(res.text, "html.parser")

                # MEJORA: Validar estructura antes de procesar
                if not self.validate_site_structure(soup, url):
                    logging.error(f"[GatoTV] Saltando {day_name} por cambio en estructura del sitio")
                    continue

                # Buscar tabla EPG con selector más específico como iptv-org
                epg_table = soup.select_one('body div.div_content table.tbl_EPG')
                if not epg_table:
                    # Fallback al método original
                    epg_table = soup.find("table", class_="tbl_EPG")
                
                if not epg_table:
                    logging.warning(f"[GatoTV] No se encontró la tabla principal de EPG en {url}")
                    continue
                
                # Buscar filas de programas
                program_rows = epg_table.select("tr.tbl_EPG_row, tr.tbl_EPG_rowAlternate, tr.tbl_EPG_row_selected")
                
                if not program_rows:
                    logging.warning(f"[GatoTV] Tabla EPG vacía en {url}")
                    continue

                daily_programs = []
                programs_found = 0
                
                for row in program_rows:
                    cols = row.find_all("td")
                    if len(cols) < 3:
                        continue

                    # MEJORA: Parsing más robusto de horarios
                    hora_inicio = cols[0].find("time")
                    hora_fin = cols[1].find("time")
                    
                    start_dt = self.parse_time_with_validation(hora_inicio, fecha_local, "inicio")
                    end_dt = self.parse_time_with_validation(hora_fin, fecha_local, "fin")
                    
                    if not start_dt or not end_dt:
                        logging.debug(f"[GatoTV] Saltando programa por horarios inválidos")
                        continue

                    # MEJORA: Parsing mejorado de título y descripción
                    title = self.parse_title(row)
                    description = self.parse_description(row)
                    image = self.parse_image(row)

                    daily_programs.append({
                        "title": title,
                        "description": description,
                        "image": image,
                        "start_dt": start_dt,
                        "stop_dt": end_dt
                    })
                    programs_found += 1
                
                # MEJORA: Manejar transiciones de día
                daily_programs = self.handle_day_transitions(daily_programs)
                
                # >>> INICIO DE LA MODIFICACIÓN <<<
                # Filtrar programas que ya han terminado en el día actual
                if fecha_local == today_local:
                    now_local = datetime.utcnow() - self.timezone_offset
                    
                    programas_futuros = []
                    for prog in daily_programs:
                        # Mantener programas cuya hora de finalización es posterior a la hora actual
                        if prog['stop_dt'] > now_local:
                            programas_futuros.append(prog)
                    
                    programas_filtrados = len(daily_programs) - len(programas_futuros)
                    if programas_filtrados > 0:
                        logging.info(f"[GatoTV] Filtrando {programas_filtrados} programas pasados.")
                    
                    daily_programs = programas_futuros
                # >>> FIN DE LA MODIFICACIÓN <<<

                # Convertir a formato final con UTC
                for prog in daily_programs:
                    start_utc = prog['start_dt'] - self.timezone_offset
                    stop_utc = prog['stop_dt'] - self.timezone_offset
                    
                    program_data = {
                        "title": prog["title"],
                        "description": prog["description"],
                        "start": start_utc.strftime("%Y%m%d%H%M%S +0000"),
                        "stop": stop_utc.strftime("%Y%m%d%H%M%S +0000")
                    }
                    
                    # Añadir imagen si está disponible
                    if prog["image"]:
                        program_data["image"] = prog["image"]
                    
                    programas.append(program_data)
                
                logging.info(f"[GatoTV] ✓ {programs_found} programas encontrados para {day_name}")
                
            except Exception as e:
                logging.error(f"[GatoTV] Error en '{channel_config['nombre']}' para {day_name} ({url}): {e}")
                continue
                
        return programas