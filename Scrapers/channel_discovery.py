import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import logging
import json

def discover_gatotv_channels():
    """
    Descubre automáticamente todos los canales disponibles en GatoTV
    Basado en la implementación de iptv-org
    """
    logging.info("[GatoTV] Iniciando descubrimiento automático de canales...")
    
    try:
        # Headers realistas para evitar bloqueos
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en;q=0.6",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Obtener la página principal de la guía completa
        response = requests.get('https://www.gatotv.com/guia_tv/completa', headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar filas de canales en la tabla principal
        channel_rows = soup.select('.tbl_EPG_row, .tbl_EPG_rowAlternate')
        
        channels = []
        processed_ids = set()  # Evitar duplicados
        
        for row in channel_rows:
            try:
                # Buscar el enlace del canal en la primera columna
                # Probar múltiples selectores
                link_elem = None
                selectors = [
                    'td:nth-child(1) > div:nth-child(2) > a:nth-child(3)',
                    'td:first-child a[href*="/canal/"]',
                    'td:first-child a',
                    'a[href*="/canal/"]'
                ]
                
                for selector in selectors:
                    link_elem = row.select_one(selector)
                    if link_elem:
                        break
                
                if link_elem:
                    href = link_elem.get('href')
                    name = link_elem.get_text(strip=True)
                    
                    if href and name and len(name) > 1:
                        # Extraer site_id de la URL
                        if href.startswith('/'):
                            href = f"https://www.gatotv.com{href}"
                        
                        parsed_url = urlparse(href)
                        path_parts = [p for p in parsed_url.path.split('/') if p]
                        
                        if 'canal' in path_parts and len(path_parts) > 1:
                            canal_index = path_parts.index('canal')
                            if canal_index + 1 < len(path_parts):
                                site_id = path_parts[canal_index + 1]
                                
                                # Evitar duplicados
                                if site_id in processed_ids:
                                    continue
                                processed_ids.add(site_id)
                                
                                # Limpiar nombre del canal
                                name = name.replace('\n', ' ').replace('\t', ' ')
                                name = ' '.join(name.split())  # Normalizar espacios
                                
                                # Buscar logo en la fila
                                logo_url = extract_logo_url(row)
                                
                                channel_data = {
                                    "id": f"{site_id}.cr",  # Formato estándar con código de país
                                    "nombre": name,
                                    "site_id": site_id,
                                    "scraper": "gatotv",
                                    "url": f"https://www.gatotv.com/canal/{site_id}",
                                    "logo": logo_url
                                }
                                
                                channels.append(channel_data)
                                logging.info(f"[GatoTV] Canal encontrado: {name} ({site_id})")
                        
            except Exception as e:
                logging.debug(f"[GatoTV] Error procesando fila de canal: {e}")
                continue
        
        # Filtrar canales con nombres muy cortos o inválidos
        channels = [ch for ch in channels if len(ch['nombre']) > 2 and not ch['nombre'].isdigit()]
        
        logging.info(f"[GatoTV] Descubrimiento completado: {len(channels)} canales encontrados")
        return channels
        
    except Exception as e:
        logging.error(f"[GatoTV] Error en descubrimiento de canales: {e}")
        return []

def extract_logo_url(row):
    """Extrae URL del logo del canal si está disponible"""
    try:
        # Buscar imagen en la fila
        img_elem = row.select_one('img')
        if img_elem:
            src = img_elem.get('src')
            if src:
                # Convertir a URL absoluta si es necesario
                if src.startswith('/'):
                    src = f"https://www.gatotv.com{src}"
                elif not src.startswith('http'):
                    src = f"https://www.gatotv.com/{src}"
                return src
    except Exception as e:
        logging.debug(f"[GatoTV] Error extrayendo logo: {e}")
    return ""

def discover_mitv_channels():
    """
    Descubre canales disponibles en Mi.TV (implementación básica)
    """
    logging.info("[Mi.TV] Iniciando descubrimiento automático de canales...")
    
    # Lista básica de canales conocidos de Mi.TV (Colombia)
    # En una implementación completa, esto scrapearia la página principal
    known_channels = [
        {
            "id": "caracol.co",
            "nombre": "Caracol Televisión",
            "site_id": "caracol-television",
            "scraper": "mitv",
            "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/Caracol_Televisi%C3%B3n_logo.svg/1200px-Caracol_Televisi%C3%B3n_logo.svg.png"
        },
        {
            "id": "rcn.co",
            "nombre": "RCN Televisión",
            "site_id": "rcn-television",
            "scraper": "mitv",
            "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/RCN_Televisi%C3%B3n_logo.svg/1200px-RCN_Televisi%C3%B3n_logo.svg.png"
        }
    ]
    
    logging.info(f"[Mi.TV] {len(known_channels)} canales conocidos disponibles")
    return known_channels

def update_config_with_discovered_channels(config_file='config.json'):
    """
    Actualiza automáticamente el config.json con canales descubiertos
    """
    try:
        # Cargar configuración actual
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Descubrir canales de diferentes fuentes
        gatotv_channels = discover_gatotv_channels()
        mitv_channels = discover_mitv_channels()
        
        all_discovered = gatotv_channels + mitv_channels
        
        if all_discovered:
            # Combinar con canales existentes (evitar duplicados por ID)
            existing_ids = {ch.get('id') for ch in config.get('channels', [])}
            new_channels = [ch for ch in all_discovered if ch['id'] not in existing_ids]
            
            if new_channels:
                config.setdefault('channels', []).extend(new_channels)
                
                # Guardar configuración actualizada
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                logging.info(f"Configuración actualizada con {len(new_channels)} canales nuevos")
                
                # Mostrar resumen de canales añadidos
                for ch in new_channels[:5]:  # Mostrar solo los primeros 5
                    logging.info(f"  + {ch['nombre']} ({ch['scraper']})")
                if len(new_channels) > 5:
                    logging.info(f"  ... y {len(new_channels) - 5} canales más")
                
                return True
            else:
                logging.info("No se encontraron canales nuevos")
                return False
        else:
            logging.warning("No se pudieron descubrir canales")
            return False
            
    except Exception as e:
        logging.error(f"Error actualizando configuración: {e}")
        return False

def auto_discover_channels_if_needed(min_channels=3):
    """
    Descubre canales automáticamente si la lista está vacía o es muy pequeña
    """
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        current_channels = len(config.get('channels', []))
        
        # Si hay pocos canales, intentar descubrir más
        if current_channels < min_channels:
            logging.info(f"Solo {current_channels} canales en config (mínimo: {min_channels}). Iniciando descubrimiento automático...")
            success = update_config_with_discovered_channels()
            
            if success:
                logging.info("✓ Canales actualizados exitosamente")
            else:
                logging.warning("⚠ No se pudieron añadir canales nuevos")
        else:
            logging.info(f"Configuración actual: {current_channels} canales (suficientes)")
        
    except FileNotFoundError:
        logging.error("Archivo config.json no encontrado")
    except json.JSONDecodeError:
        logging.error("Error leyendo config.json - formato JSON inválido")
    except Exception as e:
        logging.error(f"Error en auto-descubrimiento: {e}")

def list_available_channels():
    """
    Lista todos los canales disponibles sin modificar la configuración
    """
    print("\n" + "="*60)
    print("CANALES DISPONIBLES PARA SCRAPING")
    print("="*60)
    
    print("\nCANALES DE COSTA RICA (GatoTV):")
    gatotv_channels = discover_gatotv_channels()
    
    if gatotv_channels:
        for i, ch in enumerate(gatotv_channels, 1):
            print(f"  {i:2d}. {ch['nombre']} (ID: {ch['id']})")
    else:
        print("  No se pudieron descubrir canales de GatoTV")
    
    print(f"\nCANALES DE COLOMBIA (Mi.TV):")
    mitv_channels = discover_mitv_channels()
    
    if mitv_channels:
        for i, ch in enumerate(mitv_channels, 1):
            print(f"  {i:2d}. {ch['nombre']} (ID: {ch['id']})")
    else:
        print("  No se pudieron descubrir canales de Mi.TV")
    
    total = len(gatotv_channels) + len(mitv_channels)
    print(f"\n📊 TOTAL: {total} canales disponibles")
    print("="*60)
    
    return gatotv_channels + mitv_channels

if __name__ == "__main__":
    # Para pruebas independientes
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_available_channels()
        elif sys.argv[1] == "update":
            update_config_with_discovered_channels()
        elif sys.argv[1] == "auto":
            auto_discover_channels_if_needed()
    else:
        print("Uso:")
        print("  python channel_discovery.py list    - Listar canales disponibles")
        print("  python channel_discovery.py update  - Actualizar config.json")
        print("  python channel_discovery.py auto    - Auto-descubrir si es necesario")

