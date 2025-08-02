# 📺 EPG Generator para Costa Rica

Generador automático de guías de programación televisiva (EPG) en formato XMLTV para canales costarricenses y latinoamericanos.

![Automatización](https://img.shields.io/badge/Automatización-GitHub%20Actions-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![Formato](https://img.shields.io/badge/Formato-XMLTV-orange)
![Estado](https://img.shields.io/badge/Estado-Activo-brightgreen)

## 🚀 Características

### ✨ Funcionalidades Principales
- **Scraping Automático**: Extrae programación de múltiples fuentes web
- **Formato XMLTV**: Compatible con reproductores IPTV estándar (Kodi, VLC, etc.)
- **Automatización GitHub Actions**: Actualización diaria automática a las 8:05 AM (UTC-6)
- **Modos Inteligentes**: Adaptación automática según el día de la semana
- **Compresión GZIP**: Archivos EPG optimizados para descarga rápida
- **Descubrimiento Automático**: Encuentra canales disponibles automáticamente
- **Multi-fuente**: Soporte para múltiples sitios web de programación

### 🛡️ Características Técnicas
- Manejo robusto de errores y reconexiones
- Validación de estructura de sitios web
- Logging detallado para debugging
- Parsing inteligente con múltiples selectores CSS
- Manejo correcto de zonas horarias (EST/UTC-5)
- Detección automática de transiciones de día

## 📋 Fuentes Soportadas

| Fuente | Status | Cobertura | Canales Disponibles |
|--------|--------|-----------|-------------------|
| **GatoTV** | ✅ Activo | Costa Rica | Canal 6, Canal 7, Canal 11, etc. |
| **Mi.TV** | ✅ Activo | Colombia | Caracol, RCN, etc. |

## ⚙️ Instalación y Configuración

### 📦 Instalación Local

```bash
# Clonar repositorio
git clone https://github.com/[tu-usuario]/EPG.git
cd EPG

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar generación
python main.py
```

### 🔧 Configuración Básica

El archivo `config.json` controla todos los aspectos del generador:

```json
{
  "settings": {
    "days_to_scrape": 7,
    "timezone_offset_hours": 5,
    "output_file": "epgpersonal.xml.gz",
    "force_full_week": false
  },
  "channels": [
    {
      "id": "Repretel6.cr",
      "nombre": "Canal 6",
      "logo": "https://...",
      "scraper": "gatotv",
      "url": "https://www.gatotv.com/canal/6_de_costa_rica",
      "site_id": "6_de_costa_rica"
    }
  ]
}
```

### 🌐 Modos de Operación

| Modo | Descripción | Activación |
|------|-------------|------------|
| **Normal** | Scrapea según `days_to_scrape` | Automático (lunes-viernes) |
| **Fin de Semana** | Sábado y domingo (2 días) | Automático (sábados) |
| **Semana Completa** | 7 días desde lunes | `"force_full_week": true` |

## 🤖 Automatización

### GitHub Actions

El EPG se actualiza automáticamente:
- **Horario**: Todos los días a las 8:05 AM (UTC-6, hora de Costa Rica)
- **Trigger**: Cron job + ejecución manual disponible
- **Resultado**: Archivo `epgpersonal.xml.gz` actualizado en el repositorio

### URL de Descarga

Una vez configurado, tu EPG estará disponible en:
```
https://raw.githubusercontent.com/[usuario]/[repo]/main/epgpersonal.xml.gz
```

## 🔍 Descubrimiento Automático de Canales

### Usar Descubrimiento Automático

```bash
# Listar todos los canales disponibles
python channel_discovery.py list

# Actualizar config.json con canales encontrados
python channel_discovery.py update

# Auto-descubrir si hay pocos canales configurados
python channel_discovery.py auto
```

### Integración en el Código

El sistema automáticamente descubre canales si tu configuración tiene menos de 3 canales:

```python
# En main.py - se ejecuta automáticamente
auto_discover_channels_if_needed(min_channels=3)
```

## 🛠️ Desarrollo y Personalización

### Añadir Nuevo Scraper

1. **Crear archivo scraper**:
```python
# Scrapers/nuevo_scraper.py
class NuevoScraper:
    def __init__(self, config):
        self.headers = config.get("headers", {})
        self.days_to_scrape = config.get("days_to_scrape", 1)
    
    def fetch_programs(self, channel_config):
        # Tu lógica de scraping aquí
        return programas  # Lista de diccionarios
```

2. **Registrar en main.py**:
```python
from Scrapers.nuevo_scraper import NuevoScraper

scrapers = {
    "gatotv": GatoTVScraper(weekend_settings),
    "mitv": MiTVScraper(weekend_settings),
    "nuevo": NuevoScraper(weekend_settings)  # Añadir aquí
}
```

3. **Actualizar config.json**:
```json
{
  "id": "canal.pais",
  "nombre": "Nombre del Canal",
  "scraper": "nuevo",
  "url": "https://sitio.com/canal/id"
}
```

### Estructura de Respuesta del Scraper

Los scrapers deben devolver una lista de programas con esta estructura:

```python
{
    "title": "Nombre del Programa",
    "description": "Descripción opcional",
    "image": "https://imagen.com/programa.jpg",  # Opcional
    "start": "20240802140000 +0000",  # Formato: YYYYMMDDHHMMSS +0000
    "stop": "20240802150000 +0000"
}
```

### Validación y Testing

```python
# Validar estructura del sitio
def validate_site_structure(self, soup, url):
    expected_elements = ["selector1", "selector2"]
    for element in expected_elements:
        if not soup.select(element):
            logging.error(f"Estructura cambió: {element} no encontrado")
            return False
    return True

# Testing de scraper
python -c "
from Scrapers.gatotv_scraper import GatoTVScraper
config = {'days_to_scrape': 1, 'timezone_offset_hours': 5}
scraper = GatoTVScraper(config)
channel = {'nombre': 'Test', 'url': 'https://...', 'site_id': 'test'}
programs = scraper.fetch_programs(channel)
print(f'Programas encontrados: {len(programs)}')
"
```

## 📊 Logs y Monitoreo

### Sistema de Logging

Los logs se guardan en `epg_generator.log` con información detallada:

```
2024-08-02 08:05:01 - INFO - [GatoTV] Scrapeando Lunes 2024-08-02 para 'Canal 6'
2024-08-02 08:05:02 - INFO - [GatoTV] ✓ 24 programas encontrados para Lunes
2024-08-02 08:05:03 - INFO - ✓ Archivo: epgpersonal.xml.gz
2024-08-02 08:05:03 - INFO - ✓ Programas totales: 168
```

### Niveles de Log

- **INFO**: Operaciones normales y estadísticas
- **WARNING**: Problemas menores (canales saltados, estructura cambiada)
- **ERROR**: Errores críticos que impiden el procesamiento
- **DEBUG**: Información detallada para desarrollo

## 🔍 Troubleshooting

### Errores Comunes

#### ❌ No se encuentran programas
```bash
# Verificar estructura del sitio
curl -s "https://www.gatotv.com/canal/6_de_costa_rica" | grep -i "tbl_EPG"

# Probar con un solo día
python -c "
import json
with open('config.json', 'r') as f: 
    config = json.load(f)
config['settings']['days_to_scrape'] = 1
config['settings']['force_full_week'] = False
with open('config.json', 'w') as f: 
    json.dump(config, f, indent=2)
"
```

#### ❌ Error de timeout
```python
# En tu scraper, aumentar timeout
res = requests.get(url, headers=self.headers, timeout=30)  # Aumentar de 15 a 30
```

#### ❌ Estructura del sitio cambió
```python
# Verificar selectores CSS actuales
from bs4 import BeautifulSoup
import requests

response = requests.get("https://www.gatotv.com/canal/6_de_costa_rica")
soup = BeautifulSoup(response.text, 'html.parser')

# Verificar elementos clave
print("Tabla EPG:", bool(soup.select("table.tbl_EPG")))
print("Filas de programas:", len(soup.select("tr.tbl_EPG_row")))
```

### Validar EPG Generado

```bash
# Descomprimir y validar XML
gunzip -c epgpersonal.xml.gz | head -20

# Verificar estructura XMLTV
gunzip -c epgpersonal.xml.gz | xmllint --format - | head -50

# Contar programas
gunzip -c epgpersonal.xml.gz | grep -c "<programme"
```

## 📈 Estadísticas y Métricas

### Información del Proyecto
- **Líneas de código**: ~500+ líneas
- **Dependencias**: 5 paquetes Python principales
- **Frecuencia**: Actualización diaria automática
- **Formato**: XMLTV estándar comprimido con GZIP
- **Compatibilidad**: Python 3.9+

### Rendimiento Típico
- **Tiempo de ejecución**: 30-120 segundos (dependiendo del número de canales)
- **Canales soportados**: 10+ canales activos
- **Programas por día**: 20-50 por canal
- **Tamaño archivo**: 50-200 KB comprimido

## 🔗 URLs Útiles

### Configuración para Reproductores IPTV

**Kodi**:
1. Instalar PVR IPTV Simple Client
2. Configurar EPG: `https://raw.githubusercontent.com/[usuario]/[repo]/main/epgpersonal.xml.gz`

**VLC**:
1. Media → Open Network Stream
2. EPG URL: `https://raw.githubusercontent.com/[usuario]/[repo]/main/epgpersonal.xml.gz`

## 🚀 Próximas Mejoras

### Roadmap
- [ ] **Más fuentes**: Añadir scrapers para otros países
- [ ] **Cache inteligente**: Evitar re-scraping innecesario
- [ ] **API REST**: Endpoint para consultar programación
- [ ] **Dashboard web**: Interfaz visual para monitoreo
- [ ] **Notificaciones**: Alertas cuando fallan scrapers
- [ ] **Estadísticas**: Métricas de uso y rendimiento

### Contribuir

1. **Fork** del proyecto
2. **Crear** feature branch: `git checkout -b feature/nueva-caracteristica`
3. **Commit** cambios: `git commit -m 'Añadir nueva característica'`
4. **Push** al branch: `git push origin feature/nueva-caracteristica`
5. **Crear** Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🙏 Agradecimientos

- **iptv-org/epg**: Inspiración para la arquitectura de scrapers
- **Comunidad IPTV**: Testing y feedback
- **GitHub Actions**: Plataforma de automatización

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/[usuario]/[repo]/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/[usuario]/[repo]/discussions)
- **Email**: [tu-email@ejemplo.com]

---

**⭐ Si este proyecto te ayuda, por favor dale una estrella en GitHub!**
