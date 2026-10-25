#!/usr/bin/env python3
"""Extrae un .zip del juego a una carpeta de forma segura (sin zip-slip).

Uso:
    python3 tools/extract_zip.py <archivo.zip> <carpeta_destino>

Avisa si el zip trae instaladores o imágenes de disco (.iso, .cab, .bin/.cue,
setup.exe) en vez del juego ya instalado: en ese caso hay que instalarlo o
extraerlo primero en la PC, y recién después importar la carpeta resultante.
"""
import os
import sys
import zipfile

INSTALLER_HINTS = (".iso", ".cab", ".cue", ".img", ".mdf", ".nrg", ".msi")


def safe_extract(zip_path, dest):
    dest = os.path.realpath(dest)
    os.makedirs(dest, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            target = os.path.realpath(os.path.join(dest, name))
            if target != dest and not target.startswith(dest + os.sep):
                print(f"Se omite entrada sospechosa: {info.filename}", file=sys.stderr)
                continue
            if info.is_dir() or name.endswith("/"):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
            extracted.append(name)
    return extracted


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    zip_path, dest = sys.argv[1], sys.argv[2]
    try:
        files = safe_extract(zip_path, dest)
    except (zipfile.BadZipFile, OSError) as e:
        sys.exit(f"No se pudo extraer {zip_path}: {e}")

    print(f"{len(files)} archivos extraídos en {dest}")
    hints = [f for f in files
             if f.lower().endswith(INSTALLER_HINTS) or os.path.basename(f).lower() in ("setup.exe", "install.exe")]
    if hints:
        print("\nAviso: parece haber instaladores o imágenes de disco, no solo el juego instalado:")
        for f in hints[:10]:
            print("  " + f)


if __name__ == "__main__":
    main()
