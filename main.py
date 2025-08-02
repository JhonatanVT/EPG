import json
import logging
import gzip
from datetime import datetime, timedelta
from logging import FileHandler
from Scrapers.gatotv_scraper import GatoTVScraper
from Scrapers.mitv_scraper import MiTVScraper
from Scrapers.channel_discovery import auto_discover_channels_if_needed

# Configuración del logging para ver qué está pasando
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = 'epg_generator.log'

# Configurar el manejador de archivos para que rote los logs
file_handler = FileHandler(log_file, mode='w') # 'w' para sobrescribir en cada ejecución
file_handler.setFormatter(log_formatter)

# Configurar el manejador de la consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Obtener el logger raíz y añadirle los manejadores
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

def escapar_xml(texto):
    """Escapa caracteres especiales para que el XML sea válido."""
    if not texto:
        return ""
    return (texto.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&apos;"))

def calculate_days_to_scrape(timezone_offset_hours, settings):
    """
    Calcula cuántos días scraper basado en el día actual y configuración.
    Si force_full_week está activado, scrapea toda la semana desde el lunes.
    Si es sábado, scrapea sábado y domingo (2 días).
    Si no, usa la configuración normal.
    """
    # Si está forzado el modo semana completa
    if settings.get("force_full_week", False):
        logging.info("🔧 MODO PRUEBA: Scrapeando TODA LA SEMANA (7 días desde lunes) - force_full_week activado")
        return 7
    
    # Obtener la fecha local basada en el timezone offset
    local_now = datetime.utcnow() - timedelta(hours=timezone_offset_hours)
    current_weekday = local_now.weekday()  # 0=Lunes, 6=Domingo
    day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][current_weekday]
    
    # Si es sábado (weekday = 5)
    if current_weekday == 5:
        logging.info(f"Es sábado ({local_now.strftime('%Y-%m-%d')}). Scrapeando programación de fin de semana (sábado y domingo).")
        return 2  # Scrapear sábado y domingo
    # Si es domingo (weekday = 6)
    elif current_weekday == 6:
        logging.info(f"Es domingo ({local_now.strftime('%Y-%m-%d')}). Scrapeando solo domingo (fin de semana).")
        return 1  # Solo domingo
    else:
        logging.info(f"Es {day_name} ({local_now.strftime('%Y-%m-%d')}). Usando configuración normal de días.")
        return None  # Usar configuración por defecto

def validate_program_data(programa):
    """Valida que un programa tenga los campos requeridos"""
    required_fields = ['title', 'start', 'stop', 'channel_id']
    
    for field in required_fields:
        if not programa.get(field):
            return False, f"Campo requerido '{field}' faltante o vacío"
    
    # Validar formato de fechas
    try:
        datetime.strptime(programa['start'][:14], "%Y%m%d%H%M%S")
        datetime.strptime(programa['stop'][:14], "%Y%m%d%H%M%S")
    except ValueError as e:
        return False, f"Formato de fecha inválido: {e}"
    
    return True, "OK"

def generate_xml_structure(channels, all_programs):
    """Genera la estructura XML del EPG"""
    # Generar la cabecera del XML y la lista de canales
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="JhonVT-EPG-Generator" generator-info-url="https://github.com/[tu-usuario]/EPG">\n'
    channel_xml = ""
    
    # Añadir información de canales
    for channel in channels:
        channel_id = channel.get("id")
        channel_name = channel.get("nombre")
        logo_url = channel.get("logo", "")

        channel_xml += f'  <channel id="{channel_id}">\n'
        channel_xml += f'    <display-name>{escapar_xml(channel_name)}</display-name>\n'
        if logo_url:
            channel_xml += f'    <icon src="{escapar_xml(logo_url)}"/>\n'
        channel_xml += '  </channel>\n'
    
    # Generar la sección de programas del XML
    program_xml = ""
    valid_programs = 0
    invalid_programs = 0
    
    for programa in all_programs:
        is_valid, error_msg = validate_program_data(programa)
        
        if not is_valid:
            logging.warning(f"Programa inválido saltado: {error_msg} - {programa.get('title', 'Sin título')}")
            invalid_programs += 1
            continue
        
        program_xml += f'  <programme start="{programa["start"]}" stop="{programa["stop"]}" channel="{programa["channel_id"]}">\n'
        program_xml += f'    <title lang="es">{escapar_xml(programa["title"])}</title>\n'
        
        if programa.get("description"):
            program_xml += f'    <desc lang="es">{escapar_xml(programa["description"])}</desc>\n'
        
        if programa.get("image"):
            program_xml += f'    <icon src="{escapar_xml(programa["image"])}"/>\n'
        
        program_xml += '  </programme>\n'
        valid_programs += 1
    
    xml_final = xml_header + channel_xml + program_xml + '</tv>'
    
    logging.info(f"XML generado: {valid_programs} programas válidos, {invalid_programs} programas inválidos saltados")
    
    return xml_final

def main():
    """Función principal que orquesta la generación del EPG."""
    start_time = datetime.now()
    logging.info("="*60)
    logging.info("INICIANDO GENERACIÓN DE EPG")
    logging.info("="*60)
    
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        logging.info("✓ Configuración cargada correctamente.")
    except FileNotFoundError:
        logging.error("❌ Error: El archivo config.json no se encontró.")
        return
    except json.JSONDecodeError as e:
        logging.error(f"❌ Error: El archivo config.json tiene un formato inválido: {e}")
        return

    # MEJORA: Auto-descubrir canales si la lista está vacía
    try:
        auto_discover_channels_if_needed(min_channels=3)
        # Recargar configuración después del posible auto-descubrimiento
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logging.warning(f"⚠ Auto-descubrimiento falló: {e}")

    settings = config.get("settings", {})
    timezone_offset_hours = settings.get("timezone_offset_hours", 5)  # Cambiado a 5 (EST)
    
    # Mostrar configuración actual
    logging.info(f"Configuración actual:")
    logging.info(f"  • Zona horaria: UTC-{timezone_offset_hours}")
    logging.info(f"  • Canales configurados: {len(config.get('channels', []))}")
    logging.info(f"  • Modo semana completa: {settings.get('force_full_week', False)}")
    
    # Calcular días a scrapear basado en si es sábado o no
    weekend_days = calculate_days_to_scrape(timezone_offset_hours, settings)
    if weekend_days:
        # Crear configuración temporal para fin de semana o semana completa
        weekend_settings = settings.copy()
        weekend_settings["days_to_scrape"] = weekend_days
        weekend_settings["is_weekend_mode"] = weekend_days == 2
        weekend_settings["is_full_week_mode"] = weekend_days == 7
    else:
        weekend_settings = settings.copy()
        weekend_settings["is_weekend_mode"] = False
        weekend_settings["is_full_week_mode"] = False
    
    # Diccionario de scrapers disponibles. Si creas uno nuevo, lo añades aquí.
    scrapers = {
        "gatotv": GatoTVScraper(weekend_settings),
        "mitv": MiTVScraper(weekend_settings)
    }

    all_programs = []
    processed_channels = []
    failed_channels = []
    
    channels = config.get("channels", [])
    
    if not channels:
        logging.error("❌ No hay canales configurados para procesar")
        return
    
    logging.info(f"Procesando {len(channels)} canales...")
    
    for i, channel in enumerate(channels, 1):
        channel_id = channel.get("id")
        channel_name = channel.get("nombre")
        logo_url = channel.get("logo", "")
        scraper_key = channel.get("scraper")

        if not all([channel_id, channel_name, scraper_key]):
            logging.warning(f"⚠ Saltando canal {i} por falta de 'id', 'nombre' o 'scraper': {channel}")
            failed_channels.append(channel_name or f"Canal {i}")
            continue

        processed_channels.append(channel)

        # Obtener la programación para este canal
        scraper = scrapers.get(scraper_key)
        if scraper:
            if weekend_settings.get("is_full_week_mode"):
                mode_text = "SEMANA COMPLETA (PRUEBA)"
            elif weekend_settings.get("is_weekend_mode"):
                mode_text = "FIN DE SEMANA"
            else:
                mode_text = "NORMAL"
            
            logging.info(f"[{i}/{len(channels)}] Procesando '{channel_name}' con {scraper_key} en modo {mode_text}...")
            
            try:
                programas_canal = scraper.fetch_programs(channel)
                
                # Añadir channel_id a cada programa
                for prog in programas_canal:
                    prog['channel_id'] = channel_id
                
                all_programs.extend(programas_canal)
                logging.info(f"✓ {len(programas_canal)} programas obtenidos para '{channel_name}'")
                
            except Exception as e:
                logging.error(f"❌ Error procesando '{channel_name}': {e}")
                failed_channels.append(channel_name)
                continue
                
        else:
            logging.error(f"❌ No se encontró scraper '{scraper_key}' para '{channel_name}'")
            failed_channels.append(channel_name)

    # Generar XML final
    logging.info("Generando archivo EPG...")
    xml_final = generate_xml_structure(processed_channels, all_programs)
    
    # Guardar archivo
    output_filename = settings.get("output_file", "epgpersonal.xml.gz")
    
    try:
        with gzip.open(output_filename, "wt", encoding="utf-8") as f:
            f.write(xml_final)
        
        # Calcular estadísticas finales
        end_time = datetime.now()
        duration = end_time - start_time
        
        total_programs = len(all_programs)
        successful_channels = len(processed_channels) - len(failed_channels)
        
        if weekend_settings.get("is_full_week_mode"):
            mode_text = "MODO SEMANA COMPLETA (PRUEBA)"
        elif weekend_settings.get("is_weekend_mode"):
            mode_text = "MODO FIN DE SEMANA"
        else:
            mode_text = "MODO NORMAL"
        
        logging.info("="*60)
        logging.info("GENERACIÓN EPG COMPLETADA")
        logging.info("="*60)
        logging.info(f"✓ Archivo: {output_filename}")
        logging.info(f"✓ Modo: {mode_text}")
        logging.info(f"✓ Canales procesados: {successful_channels}/{len(channels)}")
        logging.info(f"✓ Programas totales: {total_programs}")
        logging.info(f"✓ Tiempo transcurrido: {duration.total_seconds():.2f} segundos")
        
        if failed_channels:
            logging.warning(f"⚠ Canales con errores ({len(failed_channels)}): {', '.join(failed_channels)}")
        
        logging.info("="*60)
        
    except Exception as e:
        logging.error(f"❌ Error guardando archivo EPG: {e}")

if __name__ == "__main__":
    main()