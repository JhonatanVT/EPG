import json
import logging
import importlib
import gzip
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuración del Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(file_path="config.json"):
    """Carga la configuración desde un archivo JSON."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error al cargar el archivo de configuración '{file_path}': {e}")
        return None

def get_scraper_instance(scraper_name, config):
    """Importa dinámicamente y crea una instancia de un scraper."""
    try:
        module_name = f"scrapers.{scraper_name}_scraper"
        class_name = f"{scraper_name.replace('_', ' ').title().replace(' ', '')}Scraper"
        
        module = importlib.import_module(module_name)
        ScraperClass = getattr(module, class_name)
        return ScraperClass(config["settings"])
    except (ImportError, AttributeError) as e:
        logging.error(f"No se pudo cargar el scraper '{scraper_name}': {e}")
        return None

def generate_xml(channels, all_programs, output_file):
    """Genera el archivo XMLTV final y lo comprime."""
    root = ET.Element("tv", {"generator-info-name": "JhonVT-EPG-Generator"})
    
    for channel in channels:
        channel_elem = ET.SubElement(root, "channel", {"id": channel["id"]})
        ET.SubElement(channel_elem, "display-name").text = channel["nombre"]
        if channel.get("logo"):
            ET.SubElement(channel_elem, "icon", {"src": channel["logo"]})

    for program in sorted(all_programs, key=lambda p: p['start']):
        prog_elem = ET.SubElement(root, "programme", {
            "start": program["start"],
            "stop": program["stop"],
            "channel": program["channel_id"]
        })
        ET.SubElement(prog_elem, "title", {"lang": "es"}).text = program["title"]

    try:
        ET.indent(root, space="  ")
    except AttributeError:
        logging.warning("ET.indent no disponible (requiere Python 3.9+).")

    tree = ET.ElementTree(root)
    with gzip.open(output_file, "wb") as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    logging.info(f"✅ Archivo EPG '{output_file}' generado con éxito.")

def main():
    config = load_config()
    if not config:
        return

    all_programs = []
    scrapers = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_channel = {}
        for channel in config["channels"]:
            scraper_name = channel.get("scraper")
            if not scraper_name: continue

            if scraper_name not in scrapers:
                scrapers[scraper_name] = get_scraper_instance(scraper_name, config)
            
            scraper = scrapers[scraper_name]
            if scraper:
                future = executor.submit(scraper.fetch_programs, channel)
                future_to_channel[future] = channel

        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                programs = future.result()
                for p in programs:
                    p['channel_id'] = channel['id']
                all_programs.extend(programs)
                logging.info(f"Canal '{channel['nombre']}' procesado, {len(programs)} programas encontrados.")
            except Exception as e:
                logging.error(f"Error al procesar el futuro para el canal '{channel['nombre']}': {e}")

    generate_xml(config["channels"], all_programs, config["settings"]["output_file"])

if __name__ == "__main__":
    main()

