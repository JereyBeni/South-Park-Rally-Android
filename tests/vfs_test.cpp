#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <filesystem>
#include <fstream>

#include "vfs.h"

namespace fs = std::filesystem;

int main() {
    fs::path root = fs::temp_directory_path() / "spr_vfs_test";
    fs::remove_all(root);
    fs::create_directories(root / "Data" / "Tex");
    {
        std::ofstream f(root / "Data" / "Tex" / "Car01.TGA", std::ios::binary);
        f << "hola";
    }

    assert(vfs::mount(root.string()));
    assert(vfs::count() == 1);
    assert(vfs::exists("data\\tex\\CAR01.tga"));
    assert(vfs::exists("./Data//Tex/Car01.TGA"));
    assert(!vfs::exists("data/tex/nope.tga"));

    std::vector<uint8_t> buf;
    assert(vfs::read("DATA/TEX/car01.tga", buf));
    assert(buf.size() == 4 && buf[0] == 'h');
    assert(!vfs::read("no/existe.bin", buf));
    assert(!vfs::mount((root / "nada").string()));

    fs::remove_all(root);
    std::puts("vfs_test OK");
    return 0;
}
