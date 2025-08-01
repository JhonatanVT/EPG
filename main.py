import json
import logging
import gzip
from datetime import datetime, timedelta
from logging import FileHandler
from Scrapers.gatotv_scraper import GatoTVScraper
from Scrapers.mitv_scraper import MiTVScraper

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

def calculate_days_to_scrape(timezone_offset_hours):
    """
    Calcula cuántos días scraper basado en el día actual.
    Si es sábado, scrapea sábado y domingo (2 días).
    Si no, usa la configuración normal.
    """
    # Obtener la fecha local basada en el timezone offset
    local_now = datetime.utcnow() - timedelta(hours=timezone_offset_hours)
    current_weekday = local_now.weekday()  # 0=Lunes, 6=Domingo
    
    # Si es sábado (weekday = 5)
    if current_weekday == 5:
        logging.info(f"Es sábado ({local_now.strftime('%Y-%m-%d')}). Scrapeando programación de fin de semana (sábado y domingo).")
        return 2  # Scrapear sábado y domingo
    else:
        day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][current_weekday]
        logging.info(f"Es {day_name} ({local_now.strftime('%Y-%m-%d')}). Usando configuración normal de días.")
        return None  # Usar configuración por defecto

def main():
    """Función principal que orquesta la generación del EPG."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        logging.info("Configuración cargada correctamente.")
    except FileNotFoundError:
        logging.error("Error: El archivo config.json no se encontró.")
        return
    except json.JSONDecodeError:
        logging.error("Error: El archivo config.json tiene un formato inválido.")
        return

    settings = config.get("settings", {})
    timezone_offset_hours = settings.get("timezone_offset_hours", 6)
    
    # Calcular días a scrapear basado en si es sábado o no
    weekend_days = calculate_days_to_scrape(timezone_offset_hours)
    if weekend_days:
        # Crear configuración temporal para fin de semana
        weekend_settings = settings.copy()
        weekend_settings["days_to_scrape"] = weekend_days
        weekend_settings["is_weekend_mode"] = True
    else:
        weekend_settings = settings.copy()
        weekend_settings["is_weekend_mode"] = False
    
    # Diccionario de scrapers disponibles. Si creas uno nuevo, lo añades aquí.
    scrapers = {
        "gatotv": GatoTVScraper(weekend_settings),
        "mitv": MiTVScraper(weekend_settings)
    }

    all_programs = []
    
    # Generar la cabecera del XML y la lista de canales
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="JhonVT-EPG-Generator">\n'
    channel_xml = ""
    
    for channel in config.get("channels", []):
        channel_id = channel.get("id")
        channel_name = channel.get("nombre")
        logo_url = channel.get("logo", "")
        scraper_key = channel.get("scraper")

        if not all([channel_id, channel_name, scraper_key]):
            logging.warning(f"Saltando canal por falta de 'id', 'nombre' o 'scraper': {channel}")
            continue

        # Añadir canal a la sección de canales del XML
        channel_xml += f'  <channel id="{channel_id}">\n'
        channel_xml += f'    <display-name>{escapar_xml(channel_name)}</display-name>\n'
        if logo_url:
            channel_xml += f'    <icon src="{escapar_xml(logo_url)}"/>\n'
        channel_xml += '  </channel>\n'

        # Obtener la programación para este canal
        scraper = scrapers.get(scraper_key)
        if scraper:
            mode_text = "FIN DE SEMANA" if weekend_settings.get("is_weekend_mode") else "NORMAL"
            logging.info(f"Procesando canal '{channel_name}' con el scraper '{scraper_key}' en modo {mode_text}...")
            programas_canal = scraper.fetch_programs(channel)
            for prog in programas_canal:
                prog['channel_id'] = channel_id
            all_programs.extend(programas_canal)
            logging.info(f"Se encontraron {len(programas_canal)} programas para '{channel_name}'.")
        else:
            logging.warning(f"No se encontró un scraper para la clave '{scraper_key}' del canal '{channel_name}'.")

    # Generar la sección de programas del XML
    program_xml = ""
    for programa in all_programs:
        program_xml += f'  <programme start="{programa["start"]}" stop="{programa["stop"]}" channel="{programa["channel_id"]}">\n'
        program_xml += f'    <title lang="es">{escapar_xml(programa["title"])}</title>\n'
        if programa.get("description"):
            program_xml += f'    <desc lang="es">{escapar_xml(programa["description"])}</desc>\n'
        program_xml += '  </programme>\n'

    xml_final = xml_header + channel_xml + program_xml + '</tv>'
    output_filename = settings.get("output_file", "epgpersonal.xml.gz")

    with gzip.open(output_filename, "wt", encoding="utf-8") as f:
        f.write(xml_final)
    
    total_programs = len(all_programs)
    mode_text = "MODO FIN DE SEMANA" if weekend_settings.get("is_weekend_mode") else "MODO NORMAL"
    logging.info(f"Archivo EPG '{output_filename}' generado con éxito en {mode_text}. Total de programas: {total_programs}.")

if __name__ == "__main__":
    main()