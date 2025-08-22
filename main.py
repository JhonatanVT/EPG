import json
import gzip
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
import logging
import sys
from Scrapers.gatotv_scraper import GatoTVScraper
from Scrapers.ontvtonight_scraper import OnTVTonightScraper
from Scrapers.channel_discovery import auto_discover_channels_if_needed

def setup_logging():
    """Configura el sistema de logging con rotación de archivos"""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Configurar el manejador de archivos con rotación
    file_handler = RotatingFileHandler(
        'epg_generator.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    
    # Configurar el manejador de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    
    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def load_config():
    """Carga y valida la configuración"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Validar campos requeridos
        required_fields = ["settings", "channels"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Campo requerido '{field}' faltante en config.json")
        
        # Validar configuración de timezone
        if not isinstance(config["settings"].get("timezone_offset_hours"), (int, float)):
            config["settings"]["timezone_offset_hours"] = 6
            logging.warning("Usando timezone_offset_hours por defecto: 6")
            
        return config
        
    except FileNotFoundError:
        logging.error("ERROR: El archivo config.json no se encontró")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"ERROR: El archivo config.json tiene un formato inválido: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"ERROR inesperado cargando configuración: {e}")
        sys.exit(1)

def escapar_xml(texto):
    """Escapa caracteres especiales para que el XML sea válido."""
    if not texto:
        return ""
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

def calculate_days_to_scrape(timezone_offset_hours, settings):
    """Calcula cuántos días scraper basado en el día actual y configuración."""
    if settings.get("force_full_week", False):
        logging.info("INFO: MODO PRUEBA: Scrapeando TODA LA SEMANA (7 días)")
        return 7
    
    local_now = datetime.now(timezone.utc) - timedelta(hours=timezone_offset_hours)
    current_weekday = local_now.weekday()
    day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][current_weekday]
    
    if current_weekday == 5:  # Sábado
        logging.info(f"Es sábado ({local_now.strftime('%Y-%m-%d')}). Modo fin de semana.")
        return 2
    elif current_weekday == 6:  # Domingo
        logging.info(f"Es domingo ({local_now.strftime('%Y-%m-%d')}). Solo domingo.")
        return 1
    else:
        logging.info(f"Es {day_name} ({local_now.strftime('%Y-%m-%d')}). Modo normal.")
        return None

def validate_program_data(programa):
    """Valida que un programa tenga los campos requeridos y formatos correctos"""
    required_fields = ['title', 'start', 'stop', 'channel_id']
    
    # Validar campos requeridos
    for field in required_fields:
        if not programa.get(field):
            return False, f"Campo requerido '{field}' faltante o vacío"
    
    # Validar longitud máxima de título y descripción
    if len(programa['title']) > 200:
        programa['title'] = programa['title'][:197] + "..."
    
    if programa.get('description') and len(programa['description']) > 500:
        programa['description'] = programa['description'][:497] + "..."
    
    # Validar formato de fechas
    try:
        datetime.strptime(programa['start'][:14], "%Y%m%d%H%M%S")
        datetime.strptime(programa['stop'][:14], "%Y%m%d%H%M%S")
    except ValueError as e:
        return False, f"Formato de fecha inválido: {e}"
    
    return True, "OK"

def chunk_programs(programs, chunk_size=1000):
    """Procesa los programas en chunks para mejor manejo de memoria"""
    for i in range(0, len(programs), chunk_size):
        yield programs[i:i + chunk_size]

def generate_xml_structure(channels, all_programs):
    """Genera la estructura XML del EPG con manejo optimizado de memoria"""
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="JhonVT-EPG-Generator">\n'
    
    # Generar canales
    channel_xml = "".join(
        f'  <channel id="{ch["id"]}">\n'
        f'    <display-name>{escapar_xml(ch["nombre"])}</display-name>\n'
        f'    {f"""<icon src="{escapar_xml(ch["logo"])}"/>\n""" if ch.get("logo") else ""}'
        f'  </channel>\n'
        for ch in channels
    )
    
    # Procesar programas en chunks
    program_xml = ""
    valid_programs = 0
    invalid_programs = 0
    
    for chunk in chunk_programs(all_programs):
        for programa in chunk:
            is_valid, error_msg = validate_program_data(programa)
            if not is_valid:
                logging.warning(f"Programa inválido: {error_msg}")
                invalid_programs += 1
                continue
                
            program_xml += (
                f'  <programme start="{programa["start"]}" stop="{programa["stop"]}" '
                f'channel="{programa["channel_id"]}">\n'
                f'    <title lang="es">{escapar_xml(programa["title"])}</title>\n'
            )
            
            if programa.get("description"):
                program_xml += f'    <desc lang="es">{escapar_xml(programa["description"])}</desc>\n'
            if programa.get("image"):
                program_xml += f'    <icon src="{escapar_xml(programa["image"])}"/>\n'
            
            program_xml += '  </programme>\n'
            valid_programs += 1
    
    logging.info(f"Programas procesados - Válidos: {valid_programs}, Inválidos: {invalid_programs}")
    
    return xml_header + channel_xml + program_xml + '</tv>'

def main():
    """Función principal que orquesta la generación del EPG."""
    start_time = datetime.now()
    logger = setup_logging()
    logging.info("="*60)
    logging.info("INICIANDO GENERACIÓN DE EPG")
    logging.info("="*60)
    
    # Cargar configuración
    config = load_config()
    
    # Auto-descubrir canales si es necesario
    try:
        auto_discover_channels_if_needed(min_channels=3)
        config = load_config()  # Recargar configuración
    except Exception as e:
        logging.warning(f"WARNING: Auto-descubrimiento falló: {e}")

    settings = config.get("settings", {})
    timezone_offset_hours = settings.get("timezone_offset_hours", 6)
    
    # Mostrar configuración
    logging.info(f"Configuración actual:")
    logging.info(f"  * Zona horaria: UTC-{timezone_offset_hours}")
    logging.info(f"  * Canales configurados: {len(config.get('channels', []))}")
    logging.info(f"  * Modo semana completa: {settings.get('force_full_week', False)}")
    
    # Calcular días a scrapear
    weekend_days = calculate_days_to_scrape(timezone_offset_hours, settings)
    weekend_settings = settings.copy()
    if weekend_days:
        weekend_settings.update({
            "days_to_scrape": weekend_days,
            "is_weekend_mode": weekend_days == 2,
            "is_full_week_mode": weekend_days == 7
        })
    else:
        weekend_settings.update({
            "is_weekend_mode": False,
            "is_full_week_mode": False
        })
    
    # Inicializar scrapers
    scrapers = {
        "gatotv": GatoTVScraper(weekend_settings),
        "ontvtonight": OnTVTonightScraper(weekend_settings)
    }

    all_programs = []
    processed_channels = []
    failed_channels = []
    channels = config.get("channels", [])
    
    if not channels:
        logging.error("ERROR: No hay canales configurados")
        return
    
    logging.info(f"Procesando {len(channels)} canales...")
    
    # Procesar cada canal
    for i, channel in enumerate(channels, 1):
        channel_id = channel.get("id")
        channel_name = channel.get("nombre")
        scraper_key = channel.get("scraper")

        if not all([channel_id, channel_name, scraper_key]):
            logging.warning(f"Canal {i} inválido: {channel}")
            failed_channels.append(channel_name or f"Canal {i}")
            continue

        processed_channels.append(channel)
        scraper = scrapers.get(scraper_key)
        
        if not scraper:
            logging.error(f"Scraper '{scraper_key}' no encontrado para '{channel_name}'")
            failed_channels.append(channel_name)
            continue
            
        mode_text = "SEMANA COMPLETA" if weekend_settings.get("is_full_week_mode") else \
                   "FIN DE SEMANA" if weekend_settings.get("is_weekend_mode") else "NORMAL"
        
        logging.info(f"[{i}/{len(channels)}] Procesando '{channel_name}' ({mode_text})")
        
        try:
            programas_canal = scraper.fetch_programs(channel)
            
            # Guardar datos crudos para debug
            raw_filename = f"d:\\jhonv\\EPG\\{scraper_key}_{channel_id}_raw.json"
            try:
                with open(raw_filename, "w", encoding="utf-8") as f:
                    json.dump(programas_canal, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.error(f"Error guardando datos crudos: {e}")
            
            # Añadir channel_id a programas
            for prog in programas_canal:
                prog['channel_id'] = channel_id
            
            all_programs.extend(programas_canal)
            logging.info(f"OK - {len(programas_canal)} programas para '{channel_name}'")
            
        except Exception as e:
            logging.error(f"Error en '{channel_name}': {e}")
            failed_channels.append(channel_name)
            continue

    # Generar y guardar XML
    logging.info("Generando EPG...")
    xml_content = generate_xml_structure(processed_channels, all_programs)
    output_file = settings.get("output_file", "epgpersonal.xml.gz")
    
    try:
        with gzip.open(output_file, "wt", encoding="utf-8") as f:
            f.write(xml_content)
        
        # Estadísticas finales
        end_time = datetime.now()
        duration = end_time - start_time
        successful_channels = len(processed_channels) - len(failed_channels)
        
        logging.info("="*60)
        logging.info("GENERACIÓN EPG COMPLETADA")
        logging.info("="*60)
        logging.info(f"Archivo: {output_file}")
        logging.info(f"Modo: {mode_text}")
        logging.info(f"Canales OK: {successful_channels}/{len(channels)}")
        logging.info(f"Programas: {len(all_programs)}")
        logging.info(f"Tiempo: {duration.total_seconds():.2f} segundos")
        
        if failed_channels:
            logging.warning(f"Canales con error ({len(failed_channels)}): {', '.join(failed_channels)}")
        
        logging.info("="*60)
        
    except Exception as e:
        logging.error(f"Error guardando EPG: {e}")

if __name__ == "__main__":
    main()