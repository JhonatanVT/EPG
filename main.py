import json
import logging
import gzip
from scrapers.gatotv_scraper import GatoTVScraper
from scrapers.mitv_scraper import MiTVScraper

# Configuración del logging para ver qué está pasando
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def escapar_xml(texto):
    """Escapa caracteres especiales para que el XML sea válido."""
    if not texto:
        return ""
    return (texto.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&apos;"))

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
    
    # Diccionario de scrapers disponibles. Si creas uno nuevo, lo añades aquí.
    scrapers = {
        "gatotv": GatoTVScraper(settings),
        "mitv": MiTVScraper(settings)
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
            logging.info(f"Procesando canal '{channel_name}' con el scraper '{scraper_key}'...")
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
    logging.info(f"✅ Archivo EPG '{output_filename}' generado con éxito. Total de programas: {len(all_programs)}.")

if __name__ == "__main__":
    main()



