#include "vfs.h"

#include <cctype>
#include <filesystem>
#include <fstream>
#include <unordered_map>

namespace fs = std::filesystem;

namespace {
std::unordered_map<std::string, std::string> g_files;  // ruta normalizada -> ruta real

// Mientras todos los archivos cuelguen de la misma carpeta de primer nivel, se la quita.
void strip_wrapper_dirs() {
    for (;;) {
        std::string prefix;
        bool same = !g_files.empty();
        for (const auto& kv : g_files) {
            size_t slash = kv.first.find('/');
            if (slash == std::string::npos) {
                same = false;
                break;
            }
            std::string first = kv.first.substr(0, slash + 1);
            if (prefix.empty()) {
                prefix = first;
            } else if (first != prefix) {
                same = false;
                break;
            }
        }
        if (!same) return;
        std::unordered_map<std::string, std::string> stripped;
        for (const auto& kv : g_files) stripped[kv.first.substr(prefix.size())] = kv.second;
        g_files.swap(stripped);
    }
}
}  // namespace

namespace vfs {

std::string normalize(const std::string& path) {
    std::string out;
    out.reserve(path.size());
    for (char c : path) {
        if (c == '\\') c = '/';
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        if (c == '/' && (out.empty() || out.back() == '/')) continue;  // barras repetidas / inicial
        out.push_back(c);
    }
    while (out.size() >= 2 && out[0] == '.' && out[1] == '/') out.erase(0, 2);
    return out;
}

bool mount(const std::string& root, bool strip_wrapper) {
    g_files.clear();
    std::error_code ec;
    if (!fs::is_directory(root, ec)) return false;

    fs::recursive_directory_iterator it(root, fs::directory_options::skip_permission_denied, ec);
    for (; !ec && it != fs::recursive_directory_iterator(); it.increment(ec)) {
        std::error_code ec2;
        if (!it->is_regular_file(ec2)) continue;
        std::string rel = fs::relative(it->path(), root, ec2).generic_string();
        if (ec2) continue;
        g_files[normalize(rel)] = it->path().string();
    }
    if (strip_wrapper) strip_wrapper_dirs();
    return true;
}

size_t count() { return g_files.size(); }

bool exists(const std::string& path) { return g_files.count(normalize(path)) != 0; }

std::string real_path(const std::string& path) {
    auto it = g_files.find(normalize(path));
    return it == g_files.end() ? std::string() : it->second;
}

bool read(const std::string& path, std::vector<uint8_t>& out) {
    std::string real = real_path(path);
    if (real.empty()) return false;
    std::ifstream f(real, std::ios::binary | std::ios::ate);
    if (!f) return false;
    std::streamsize size = f.tellg();
    if (size < 0) return false;
    f.seekg(0);
    out.resize(static_cast<size_t>(size));
    if (size > 0 && !f.read(reinterpret_cast<char*>(out.data()), size)) return false;
    return true;
}

}  // namespace vfs
