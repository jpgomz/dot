
import os
import glob
import sys
import csv
import unicodedata
import re
import shutil
import subprocess
import shlex
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from b2sdk.v2 import InMemoryAccountInfo, B2Api

LOG_FILE = "procesamiento_log.csv"
INDEX_FILE = "index.html"

# ==============================================================
# Funciones auxiliares
# ==============================================================

def slugify(text):
    """
    Convierte un string en un nombre de archivo seguro:
    - Elimina acentos
    - Sustituye caracteres no válidos por _
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", text)
    return text.strip("_")

def load_env_from_input_dir(input_dir):
    """Carga variables del archivo .env dentro del INPUT_DIR."""
    env_path = os.path.join(input_dir, ".env")
    if os.path.isfile(env_path):
        print(f"📦 Cargando configuración desde {env_path}")
        load_dotenv(env_path)
    else:
        print(f"⚠️ No se encontró {env_path}, se usarán variables del entorno global.")

# ==============================================================
# Funciones de Backblaze B2
# ==============================================================

_b2_api = None

def get_b2_api():
    """Devuelve una conexión autenticada a B2 (cacheada globalmente)."""
    global _b2_api
    if _b2_api is None:
        key_id = os.getenv("B2_KEY_ID")
        app_key = os.getenv("B2_APP_KEY")
        if not key_id or not app_key:
            raise RuntimeError("⚠️ Faltan credenciales B2_KEY_ID o B2_APP_KEY en .env o entorno")

        info = InMemoryAccountInfo()
        _b2_api = B2Api(info)
        _b2_api.authorize_account("production", key_id, app_key)
    return _b2_api

def upload_to_b2(local_path, bucket_name=None):
    """Sube un archivo a B2 y devuelve la URL pública."""
    b2 = get_b2_api()
    bucket_name = bucket_name or os.getenv("B2_BUCKET")
    endpoint = os.getenv("B2_ENDPOINT", "s3.us-east-005.backblazeb2.com")
    if not bucket_name:
        raise RuntimeError("⚠️ Falta B2_BUCKET en .env o entorno")

    bucket = b2.get_bucket_by_name(bucket_name)
    remote_name = os.path.basename(local_path)

    # --- Verificar si ya existe ---
    found = False
    try:
        for file_version, folder_name in bucket.ls():
            if file_version.file_name == remote_name:
                found = True
                break
    except Exception:
        pass

    if found:
        print(f"📁 Ya existe en B2: {remote_name}")
        return f"https://{bucket_name}.{endpoint}/{remote_name}"

    # --- Subir archivo (compatibilidad multi-versión) ---
    print(f"⬆️ Subiendo a B2: {remote_name}")

    try:
        # Nuevo SDK (>=3.x): usa argumento 'local_file'
        bucket.upload_local_file(local_file=local_path, file_name=remote_name)
    except TypeError:
        # Antiguo SDK (<3.x): usa argumento 'local_path'
        bucket.upload_local_file(local_path=local_path, file_name=remote_name)

    file_url = f"https://{bucket_name}.{endpoint}/{remote_name}"
    print(f"✅ Subido correctamente: {file_url}")
    return file_url

# ==============================================================
# Main
# ==============================================================

def main():
    if len(sys.argv) < 2:
        print("Uso: python lfscrap.py <directorio_htmls> [video] [upload]")
        sys.exit(1)

    INPUT_DIR = sys.argv[1]
    # Detectar modos
    args = [arg.lower() for arg in sys.argv[2:]]
    video_mode = "video" in args
    upload_mode = "upload" in args

    if not os.path.isdir(INPUT_DIR):
        print(f"Error: {INPUT_DIR} no es un directorio válido.")
        sys.exit(1)

     # Cargar configuración local (.env)
    load_env_from_input_dir(INPUT_DIR)

    os.makedirs(INPUT_DIR, exist_ok=True)

    files = [
        f for f in glob.glob(os.path.join(INPUT_DIR, "*.html"))
        if os.path.basename(f).lower() != "index.html"
    ]
    files = sorted(files, key=os.path.getctime)
    
    log_data = []

    for idx, file in enumerate(files, start=1):
        with open(file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")

        # 1a. Si tiene question__container, hacer procesamiento especial
        if soup.find(class_="question__container"):
            # Eliminar div.topic__index
            topic_index = soup.find("div", class_="topic__index")
            if topic_index:
                topic_index.decompose()
            
            # Agregar bordes a las opciones
            for li in soup.find_all("li", class_="choice--selected--false"):
                li["style"] = li.get("style", "") + " border: 2px solid red;"
            
            for li in soup.find_all("li", class_="choice--selected--true"):
                li["style"] = li.get("style", "") + " border: 2px solid green;"
            
            # Ajustar layout de choice__review cuando tiene contenido
            for li in soup.find_all("li"):
                choice_review = li.find(class_="choice__review")
                if choice_review and (choice_review.get_text(strip=True) or choice_review.find()):
                    # Hacer que el li use flexbox
                    current_style = li.get("style", "")
                    if "display:" not in current_style:
                        li["style"] = current_style + " display: flex; gap: 20px;"
                    
                    # Ajustar choice y choice__review
                    choice = li.find(class_="choice")
                    if choice:
                        choice["style"] = choice.get("style", "") + " flex: 0 0 auto;"
                    
                    choice_review["style"] = choice_review.get("style", "") + " flex: 1; text-align: left; margin-left: auto;"
            
            # Eliminar botón al final del question__container
            question_container = soup.find(class_="question__container")
            if question_container:
                button = question_container.find("button")
                if button:
                    button.decompose()

        # 1. Obtener sección
        section_tag = soup.select_one(".learner-section__title[aria-label]")
        section_name = section_tag["aria-label"] if section_tag else "sin_seccion"
        section_name = slugify(section_name)

        section_path = os.path.join(INPUT_DIR, section_name)
        os.makedirs(section_path, exist_ok=True)
        
        # Si se pasa el parámetro "video", procesar los <video> encontrados
        soup = process_videos_in_html(soup, INPUT_DIR, section_path, video_mode=video_mode, upload_mode=upload_mode)

        # 2. Extraer título
        title_tag = soup.select_one(".editor-content h1 span")
        title = title_tag.get_text(strip=True) if title_tag else "sin_titulo"
        safe_title = slugify(title)

        # 2b. Cambiar w_600 por w_200 en imágenes de topic__list__item--expanded
        for topic_item in soup.find_all(class_="topic__list__item--expanded"):
            for img in topic_item.find_all("img", attrs={"data-sf-original-src": True}):
                original_src = img["data-sf-original-src"]
                if "w_600" in original_src:
                    img["data-sf-original-src"] = original_src.replace("w_600", "w_200")

        # 3. Reemplazar data-sf-original-src → src
        for tag in soup.find_all(attrs={"data-sf-original-src": True}):
            tag["src"] = tag["data-sf-original-src"]
            del tag["data-sf-original-src"]

        # 3b. Eliminar div.directional__nav
        directional_nav = soup.find("div", class_="directional__nav")
        if directional_nav:
            directional_nav.decompose()

        # 4. Insertar meta tag con numeración ascendente
        if soup.head:
            meta_tag = soup.new_tag("meta", attrs={"name": "order", "content": str(idx)})
            soup.head.insert(0, meta_tag)

        # 5. Guardar archivo usando el título
        filename = f"{safe_title}.html"
        output_file = os.path.join(section_path, filename)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(str(soup))

        print(f"Procesado: {file} → {output_file} (#{idx} - Título: {title})")
        log_data.append([file, output_file, title, section_name, idx])

    # Guardar log en CSV
    log_path = os.path.join(INPUT_DIR, LOG_FILE)
    with open(log_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["archivo_original", "archivo_procesado", "titulo", "seccion", "orden"])
        writer.writerows(log_data)

    print(f"\n✅ Procesamiento completado. Log generado en {log_path}")

    # 6. Mover PDFs
    pdfs = move_pdfs(INPUT_DIR)

    # 7. Generar index.html (ahora con PDFs)
    generate_index(log_data, INPUT_DIR, pdfs)

    # 8. Navegación
    add_navigation(log_data, INPUT_DIR)

    print("\n✅ Todo finalizado correctamente")

# ==============================================================
# Procesamiento de videos
# ==============================================================

def fetch_manifest(url):
    """Ejecuta curl -L para obtener el contenido del manifest .m3u8."""
    try:
        result = subprocess.run(
            shlex.split(f'curl -L "{url}"'),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error al obtener manifest: {url}\n{e}")
        return ""

def parse_m3u8_manifest(manifest_text):
    """Extrae las URLs de subtítulos y del stream 540p."""
    caption_url = None
    video_540_url = None

    lines = manifest_text.strip().splitlines()
    for i, line in enumerate(lines):
        # --- Buscar la URI de subtítulos ---
        if line.startswith("#EXT-X-MEDIA") and "TYPE=SUBTITLES" in line:
            match = re.search(r'URI="([^"]+)"', line)
            if match:
                caption_manifest_url = match.group(1)

                # Segundo curl para obtener el .vtt final
                try:
                    result = subprocess.run(
                        shlex.split(f'curl -L "{caption_manifest_url}"'),
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    caption_manifest = result.stdout.strip().splitlines()

                    # Buscar la línea que no empieza con #
                    for sub_line in caption_manifest:
                        sub_line = sub_line.strip()
                        if sub_line and not sub_line.startswith("#"):
                            caption_url = sub_line
                            break

                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Error al obtener caption manifest: {caption_manifest_url}\n{e}")

        # --- Buscar stream 540p ---
        if line.startswith("#EXT-X-STREAM-INF") and 'NAME="540p"' in line:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith("http"):
                    video_540_url = next_line

    return caption_url, video_540_url

def download_with_ffmpeg(video_url, caption_url, output_dir, base_name):
    """Descarga video y subtítulos usando ffmpeg y curl."""
    os.makedirs(output_dir, exist_ok=True)
    mp4_file = os.path.join(output_dir, f"{base_name}.mp4")
    vtt_file = os.path.join(output_dir, f"{base_name}.vtt")

    # Descargar video con ffmpeg (solo si no existe)
    if video_url:
        if os.path.exists(mp4_file):
            print(f"✅ Video ya existe, omitiendo descarga → {mp4_file}")
        else:
            print(f"🎥 Descargando video 540p → {mp4_file}")
            cmd = f'ffmpeg -y -i "{video_url}" -c copy "{mp4_file}"'
            subprocess.run(shlex.split(cmd), check=True)

    # Descargar subtítulos con curl (solo si no existe)
    if caption_url:
        if os.path.exists(vtt_file):
            print(f"✅ Subtítulos ya existen, omitiendo descarga → {vtt_file}")
        else:
            print(f"📝 Descargando subtítulos → {vtt_file}")
            cmd = f'curl -L -o "{vtt_file}" "{caption_url}"'
            subprocess.run(shlex.split(cmd), check=True)

    return mp4_file, vtt_file

def process_videos_in_html(soup, output_dir, section_path, video_mode=False, upload_mode=False):
    """Si está activado el modo 'video', analiza cada tag <video> con data-sf-original-src."""
    if not video_mode:
        return soup

    videos_dir = os.path.join(output_dir, "videos")
    os.makedirs(videos_dir, exist_ok=True)
    bucket_name = os.getenv("B2_BUCKET")

    # Buscar dentro de <source>, no <video>
    for source_tag in soup.find_all("source", attrs={"data-sf-original-src": True}):
        video_src = source_tag["data-sf-original-src"]
        base_name = Path(video_src).stem.split("?")[0]  # eliminar parámetros tipo ?start_position=22

        print(f"🎬 Procesando video manifest: {video_src}")

        manifest_text = fetch_manifest(video_src)
        if not manifest_text:
            continue

        caption_url, video_540_url = parse_m3u8_manifest(manifest_text)
        print(f"  📝 Subtítulos: {caption_url}")
        print(f"  🎥 Video 540p: {video_540_url}")

        try:
            mp4_path, vtt_path = download_with_ffmpeg(video_540_url, caption_url, videos_dir, base_name)
        except subprocess.CalledProcessError:
            print(f"⚠️ Error descargando {video_src}")
            continue

        # Subida opcional a Backblaze
        if upload_mode:
            print(f"☁️ Subiendo {base_name} a Backblaze B2...")
            mp4_url = upload_to_b2(mp4_path, bucket_name)
            vtt_url = upload_to_b2(vtt_path, bucket_name)
        else:
            mp4_url = os.path.relpath(mp4_path, section_path)
            vtt_url = os.path.relpath(vtt_path, section_path)

        # Crear nuevo tag <video> con subtítulos
        new_video = soup.new_tag("video")
        new_video["controls"] = None
        new_video["preload"] = "metadata"
        new_video["crossorigin"] = "anonymous"

        source = soup.new_tag("source", src=mp4_url, type="video/mp4")
        track = soup.new_tag("track", kind="subtitles", src=vtt_url, srclang="en", label="English")
        track["default"] = None  # activa los subtítulos por defecto

        new_video.append(source)
        new_video.append(track)

        # Buscar el div.video__container y reemplazar todo su contenido
        video_container = source_tag.find_parent("div", class_="video__container")
        if video_container:
            # Limpiar todo el contenido del div
            video_container.clear()
            # Agregar solo el nuevo video
            video_container.append(new_video)
            print(f"✅ Contenedor video__container actualizado con nuevo <video>")
        else:
            print(f"⚠️ No se encontró div.video__container, reemplazando solo el <video>")
            # Fallback: reemplazar el <video> original como antes
            parent_video = source_tag.find_parent("video")
            if parent_video:
                parent_video.replace_with(new_video)

    return soup

def move_pdfs(input_dir):
    """
    Mueve PDFs a resources/, elimina prefijos alfanuméricos- 
    y devuelve la lista completa de PDFs en resources/.
    Si ya existe un PDF con el mismo nombre, lo reemplaza.
    """
    resources_dir = os.path.join(input_dir, "resources")
    os.makedirs(resources_dir, exist_ok=True)

    pdf_files = sorted(glob.glob(os.path.join(input_dir, "*.pdf")), key=os.path.getctime)

    for pdf in pdf_files:
        base = os.path.basename(pdf)

        # Quitar prefijo tipo "abc123-" → "Lab2.1-File.pdf"
        clean_name = re.sub(r"^[A-Za-z0-9]+-", "", base)

        dest_file = os.path.join(resources_dir, clean_name)

        # ⚠️ Si ya existe, lo borramos antes para asegurar reemplazo limpio
        if os.path.exists(dest_file):
            os.remove(dest_file)

        shutil.move(pdf, dest_file)
        print(f"📂 PDF movido: {pdf} → {dest_file}")

    # 🔁 Ahora listamos TODOS los PDFs que hay en resources
    all_pdfs = sorted(glob.glob(os.path.join(resources_dir, "*.pdf")), key=os.path.getctime)

    # Ordenar por LabX.Y si existe
    def lab_key(path):
        m = re.search(r"Lab(\d+)\.(\d+)", os.path.basename(path))
        if m:
            return (int(m.group(1)), int(m.group(2)))
        return (9999, 9999)  # los que no tienen "LabX.Y" van al final

    all_pdfs.sort(key=lab_key)
    return all_pdfs

def generate_index(log_data, output_dir, pdfs=None):
    """Genera un index.html con los enlaces ordenados por 'orden'."""
    # Ordenar por el campo 'orden'
    log_data_sorted = sorted(log_data, key=lambda x: x[4])

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Índice de Archivos Procesados</title>",
        "</head>",
        "<body>",
        "<h1>Índice de Archivos Procesados</h1>",
    ]

    # Agrupar por sección
    current_section = None
    for _, output_file, title, section, order in log_data_sorted:
        rel_path = os.path.relpath(output_file, output_dir)
        if section != current_section:
            if current_section is not None:
                html_parts.append("</ul>")
            html_parts.append(f"<h2>{section}</h2>")
            html_parts.append("<ul>")
            current_section = section
        html_parts.append(f"<li>#{order} - <a href='{rel_path}'>{title}</a></li>")

    if current_section is not None:
        html_parts.append("</ul>")

    # Recursos (PDFs)
    if pdfs:
        html_parts.append("<h2>Recursos</h2>")
        html_parts.append("<ul>")
        for pdf in pdfs:
            rel_pdf = os.path.relpath(pdf, output_dir)
            html_parts.append(f"<li><a href='{rel_pdf}'>{os.path.basename(pdf)}</a></li>")
        html_parts.append("</ul>")

    html_parts.append("</body></html>")

    index_path = os.path.join(output_dir, INDEX_FILE)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"📖 Índice generado en {index_path}")

def add_navigation(log_data, output_dir):
    """Agrega enlaces de navegación a cada archivo procesado (prev/next/menu)."""
    log_data_sorted = sorted(log_data, key=lambda x: x[4])  # orden por idx

    total = len(log_data_sorted)

    for i, (_, output_file, title, section, order) in enumerate(log_data_sorted):
        with open(output_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")

        nav_div = soup.new_tag("div")
        nav_div["class"] = "navigation"
        
        # Link al menú principal
        rel_index = os.path.relpath(os.path.join(output_dir, "index.html"), os.path.dirname(output_file))
        menu_link = soup.new_tag("a", href=rel_index)
        menu_link.string = "🏠 Menú Principal"
        nav_div.append(menu_link)

        # Prev
        if i > 0:
            prev_file = os.path.relpath(log_data_sorted[i-1][1], os.path.dirname(output_file))
            prev_link = soup.new_tag("a", href=prev_file, style="margin-left:20px")
            prev_link.string = "⬅️ Prev"
            nav_div.append(prev_link)

        # Next
        if i < total - 1:
            next_file = os.path.relpath(log_data_sorted[i+1][1], os.path.dirname(output_file))
            next_link = soup.new_tag("a", href=next_file, style="margin-left:20px")
            next_link.string = "Next ➡️"
            nav_div.append(next_link)

        # Insertar la navegación al inicio del body
        if soup.body:
            soup.body.insert(0, nav_div)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(str(soup))

        print(f"↔️ Navegación agregada a: {output_file}")

if __name__ == "__main__":
    main()
