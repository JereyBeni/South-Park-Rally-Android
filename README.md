# South Park Rally – port nativo a Android

Port del South Park Rally de PC (1999) a Android con NDK + SDL2 + OpenGL ES 2.
**Este repo no incluye ningún asset del juego**: cada usuario importa los de su copia original.

## Estructura

```
src/            Código del motor (portable: corre en PC y en Android)
  vfs.h/.cpp    Sistema de archivos virtual (ignora mayúsculas y "\" vs "/")
  main.cpp      Ventana SDL2 + contexto GLES2 + montaje de assets
tests/          Tests del VFS
tools/          scan_assets.py: identifica formatos de la carpeta del juego
docs/           FORMATS.md: notas de ingeniería inversa de formatos
android/        Proyecto Gradle (ImportActivity + GameActivity + CMake)
third_party/    SDL2 (submódulo, ver abajo)
```

## Primeros pasos

1. Traer SDL2:
   ```
   git submodule add -b SDL2 https://github.com/libsdl-org/SDL third_party/SDL2
   ```
2. Analizar los assets en tu PC (antes de tocar Android):
   ```
   python3 tools/scan_assets.py "C:\Juegos\SouthParkRally" --json report.json
   ```
   Anotá los resultados en `docs/FORMATS.md`.
3. Desarrollar en PC (más rápido de iterar):
   ```
   cmake -B build && cmake --build build
   ./build/sprally /ruta/a/la/carpeta/del/juego
   ```
4. Compilar para Android: abrí la carpeta `android/` en Android Studio (instala NDK y CMake desde el SDK Manager) y ejecutá en el dispositivo.

## Cómo se importan los assets en Android

Al abrir la app por primera vez, `ImportActivity` pide elegir la carpeta del juego (selector de carpetas del sistema) y la copia a `files/game_assets` dentro de la app. Después arranca `GameActivity` (SDL). Para reimportar, borrá los datos de la app.

## Por qué el VFS ignora mayúsculas

Windows no distingue `Car01.TGA` de `car01.tga` y Android sí. El juego original probablemente mezcla ambos y usa `\` como separador. `vfs::normalize` unifica todo en minúsculas con `/`, así que el resto del código puede pedir rutas tal como aparecen en el ejecutable original.

## Hoja de ruta

- [ ] Identificar contenedores y formatos (`tools/scan_assets.py`)
- [ ] Texturas → GL (TGA/BMP/propio)
- [ ] Visor de modelos
- [ ] Audio (SDL_mixer o miniaudio)
- [ ] Pistas y física (ingeniería inversa del .exe con Ghidra)
- [ ] Controles táctiles / mando

## Legal

El código de este repo es propio. El juego y sus assets pertenecen a sus titulares originales y no se distribuyen aquí.
