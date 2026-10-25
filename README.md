# South Park Rally – port nativo a Android

Port del South Park Rally de PC (1999) a Android con NDK + SDL2 + OpenGL ES 2.
**Este repo no incluye ningún asset del juego ni enlaces para descargarlo**: cada usuario importa su propia copia.

## Estructura

```
src/            Código del motor (portable: corre en PC y en Android)
  vfs.h/.cpp    Sistema de archivos virtual (ignora mayúsculas, "\" vs "/" y carpeta contenedora)
  main.cpp      Ventana SDL2 + contexto GLES2 + montaje de assets
tests/          Tests del VFS
tools/          scan_assets.py (identifica formatos) y extract_zip.py (extracción segura)
docs/           FORMATS.md: notas de ingeniería inversa de formatos
android/        Proyecto Gradle (ImportActivity + GameActivity + CMake)
third_party/    SDL2 (submódulo fijado en release-2.30.11)
.github/        CI: tests de escritorio + APK debug
```

## Primeros pasos

```
git clone --recurse-submodules <url-de-tu-repo>
# si ya lo clonaste sin submódulos:
git submodule update --init
```

1. **Extraer y analizar tu copia del juego en la PC**
   ```
   python3 tools/extract_zip.py juego.zip game_assets
   python3 tools/scan_assets.py game_assets --json report.json
   ```
   Anotá lo que veas en `docs/FORMATS.md`. Si el zip trae instaladores o imágenes de disco (`.iso`, `.cab`, `setup.exe`), `extract_zip.py` te avisa: hay que instalar o extraer eso primero y usar la carpeta resultante.
2. **Desarrollar en PC** (más rápido de iterar):
   ```
   cmake -B build && cmake --build build && ctest --test-dir build
   ./build/sprally game_assets
   ```
3. **Android:** abrí `android/` en Android Studio (instala NDK 26 y CMake 3.22 desde el SDK Manager) y ejecutá en el dispositivo.

## Importar los assets en Android

La primera vez, `ImportActivity` ofrece dos opciones: **elegir el .zip** (se extrae dentro de la app, con protección contra rutas maliciosas) o **elegir la carpeta** ya extraída. Los archivos quedan en `files/game_assets`. Para reimportar, borrá los datos de la app.

El VFS descarta automáticamente una única carpeta contenedora (por ejemplo `SouthParkRally/…` dentro del zip), así que el resto del código ve las rutas relativas a la raíz del juego.

## GitHub Actions

`.github/workflows/build.yml` tiene dos trabajos:

- **desktop:** compila y corre los tests del VFS. Al lanzarlo a mano (*Run workflow*) acepta `assets_zip_url`: la URL de tu copia del juego en .zip. Se descarga en el runner, se extrae con `extract_zip.py` y se analiza con `scan_assets.py`. No se publica ni se empaqueta.
- **android:** compila el APK debug y lo sube como artefacto `sprally-debug-apk` (sin assets).

## Inspector y visor de RBH/VRAM (PC)

`viewer/` contiene un inspector en Python para estudiar `cartman.rbh/.vram` (jeep) y
`cartman_anim.rbh/.vram` (personaje). Estado honesto: **inspector, reportes y vista previa
experimental de texturas; todavía sin decodificador de geometría** (ver `docs/RBH_NOTES.md`).

```
cd viewer
pip install -r requirements.txt
python -m spr_viewer gui                       # interfaz gráfica
python -m spr_viewer report cartman.rbh --json cartman.rbh.json
python -m spr_viewer hexdump cartman.rbh --offset 0 --length 256
python -m spr_viewer vram cartman.vram --width 256 --height 256 --format rgb565 --out prueba.png
pytest                                         # tests
```

Los archivos del juego se abren siempre en modo solo lectura.

## Hoja de ruta

- [ ] Identificar contenedores y formatos (`tools/scan_assets.py`)
- [ ] Texturas → GL (TGA/BMP/propio)
- [ ] Visor de modelos
- [ ] Audio (SDL_mixer o miniaudio)
- [ ] Pistas y física (ingeniería inversa del .exe con Ghidra)
- [ ] Controles táctiles / mando

## Legal

El código de este repo es propio. El juego y sus assets pertenecen a sus titulares originales: no se incluyen, no se enlazan y no se redistribuyen (ni en el APK ni como artefactos de CI).
