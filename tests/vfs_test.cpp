#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <filesystem>
#include <fstream>

#include "vfs.h"

namespace fs = std::filesystem;

static void write_file(const fs::path& p, const char* content) {
    fs::create_directories(p.parent_path());
    std::ofstream f(p, std::ios::binary);
    f << content;
}

int main() {
    const fs::path tmp = fs::temp_directory_path();

    // 1) Rutas sin distinguir mayúsculas ni separadores.
    fs::path root = tmp / "spr_vfs_test";
    fs::remove_all(root);
    write_file(root / "Data" / "Tex" / "Car01.TGA", "hola");
    write_file(root / "Game.exe", "MZ");  // archivo en la raíz: no hay carpeta contenedora

    assert(vfs::mount(root.string()));
    assert(vfs::count() == 2);
    assert(vfs::exists("data\\tex\\CAR01.tga"));
    assert(vfs::exists("./Data//Tex/Car01.TGA"));
    assert(!vfs::exists("data/tex/nope.tga"));

    std::vector<uint8_t> buf;
    assert(vfs::read("DATA/TEX/car01.tga", buf));
    assert(buf.size() == 4 && buf[0] == 'h');
    assert(!vfs::read("no/existe.bin", buf));
    assert(!vfs::mount((root / "nada").string()));

    // 2) Carpeta contenedora única (como sale de un .zip).
    fs::path root2 = tmp / "spr_vfs_test2";
    fs::remove_all(root2);
    write_file(root2 / "SouthParkRally" / "Data" / "x.bin", "abc");
    write_file(root2 / "SouthParkRally" / "spr.exe", "MZ");

    assert(vfs::mount(root2.string()));
    assert(vfs::exists("spr.exe") && vfs::exists("DATA/x.bin"));
    assert(vfs::mount(root2.string(), false));
    assert(vfs::exists("southparkrally/spr.exe") && !vfs::exists("spr.exe"));

    fs::remove_all(root);
    fs::remove_all(root2);
    std::puts("vfs_test OK");
    return 0;
}
