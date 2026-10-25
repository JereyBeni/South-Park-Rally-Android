# Notas técnicas: RBH y VRAM

Estado: **investigación inicial. No hay ninguna estructura confirmada contra archivos reales.**
Este documento separa lo confirmado de las hipótesis y se actualiza a medida que se analizan
`cartman.rbh`, `cartman.vram`, `cartman_anim.rbh` y `cartman_anim.vram`.

## Convenciones de nombres (fuente: hilo de ReSHAX sobre los modelos de South Park Rally PC)

- Cada modelo `.rbh` viene emparejado con un `.vram` del mismo nombre base (textura).
- Los vehículos se llaman por el personaje (por ejemplo `cartman`); los personajes usan el
  sufijo `_anim` (`cartman_anim`).
- El hilo (2016, archivado desde Zenhax) cita una página de la wiki rewiki.regengedanken.de sobre
  `.RBH` y dos hilos de Xentax donde el usuario herbert3000 abrió las texturas `.vram` y
  entendió parte del modelo. Ninguno de esos enlaces está verificado aquí.
- Problema abierto según el hilo: cómo se relacionan los índices de textura con las regiones
  dentro del `.vram`.

## Confirmado

Nada todavía.

## Identificadores candidatos (pistas, no pruebas)

`PIFF`, `RBHH`, `BODY`, `PACK`, `PKDB`, `PKDW`, `PKDL`, `GLOB`, `RELC`.

`python -m spr_viewer report <archivo>` lista dónde aparecen, los 16 bytes siguientes y esos
bytes como enteros de 32 bits little-endian. Esos enteros son solo observaciones: pueden ser
tamaños, offsets o datos sin relación.

## Preguntas abiertas

1. ¿Los tags forman una jerarquía de chunks (tag + tamaño) o son solo marcadores dentro de un bloque?
2. ¿Los offsets son absolutos o relativos (¿qué papel tiene `RELC`?).
3. ¿Los vértices van empaquetados (`PKDB`/`PKDW`/`PKDL`) o con compresión? ¿Qué primitivas y qué orden de caras?
4. ¿Dónde están UVs, normales y grupos de material?
5. `cartman_anim.rbh`: ¿hay esqueleto, pesos y clips, o es solo una malla estática?
6. `.vram`: dimensiones, formato de píxel, paletas, número de páginas y mapeo de índices.

## Método de trabajo

1. Correr `report` sobre los cuatro archivos y revisar entropía (¿hay compresión?).
2. Validar hipótesis de chunks recorriendo el archivo y comprobando que tamaños y offsets cierran.
3. Cuando una estructura se verifique contra los archivos, moverla a **Confirmado** con offsets y
   un test que use bytes mínimos de ejemplo (sin copiar assets al repo).

## Sin datos inventados

El visor no dibuja ninguna malla de reemplazo. Hasta que la geometría se recupere de los
archivos, el viewport solo muestra grilla y ejes, y la exportación OBJ permanece deshabilitada.
La vista previa de texturas está marcada como experimental porque interpreta bytes con los
parámetros que elige el usuario.
