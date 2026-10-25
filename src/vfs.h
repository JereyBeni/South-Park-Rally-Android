#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

// Sistema de archivos virtual sobre una carpeta de assets.
// Las rutas se comparan sin distinguir mayúsculas y aceptan '\' o '/'.
namespace vfs {

// Escanea `root` recursivamente. Devuelve false si no es una carpeta.
// Con `strip_wrapper`, si todo el contenido cuelga de una única carpeta
// (típico de un .zip: "SouthParkRally/..."), esa carpeta se descarta.
bool mount(const std::string& root, bool strip_wrapper = true);

// Cantidad de archivos indexados.
size_t count();

// Minúsculas, '/' como separador, sin "./" inicial ni barras repetidas.
std::string normalize(const std::string& path);

bool exists(const std::string& path);

// Lee el archivo completo. Devuelve false si no existe o no se pudo leer.
bool read(const std::string& path, std::vector<uint8_t>& out);

// Ruta real en disco (vacía si no existe). Útil para librerías que piden un path.
std::string real_path(const std::string& path);

}  // namespace vfs
