#include <SDL.h>
#include <SDL_opengles2.h>

#include <cstdio>
#include <string>

#include "vfs.h"

#ifdef __ANDROID__
#include <android/log.h>
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, "SPR", __VA_ARGS__)
#else
#define LOGI(...) (std::printf(__VA_ARGS__), std::printf("\n"))
#endif

// Android: ImportActivity copia los assets a <files>/game_assets.
// PC: primer argumento, o ./game_assets.
static std::string assets_root(int argc, char** argv) {
#ifdef __ANDROID__
    (void)argc;
    (void)argv;
    return std::string(SDL_AndroidGetInternalStoragePath()) + "/game_assets";
#else
    return argc > 1 ? argv[1] : "game_assets";
#endif
}

int main(int argc, char** argv) {
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO) != 0) {
        LOGI("SDL_Init falló: %s", SDL_GetError());
        return 1;
    }

    std::string root = assets_root(argc, argv);
    bool mounted = vfs::mount(root);
    LOGI("Assets en %s: montado=%d, archivos=%zu", root.c_str(), mounted, vfs::count());

    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);

    SDL_Window* win = SDL_CreateWindow("South Park Rally", SDL_WINDOWPOS_CENTERED,
                                       SDL_WINDOWPOS_CENTERED, 1280, 720,
                                       SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN | SDL_WINDOW_FULLSCREEN_DESKTOP);
    if (!win) {
        LOGI("SDL_CreateWindow falló: %s", SDL_GetError());
        return 1;
    }
    SDL_GLContext ctx = SDL_GL_CreateContext(win);
    if (!ctx) {
        LOGI("SDL_GL_CreateContext falló: %s", SDL_GetError());
        return 1;
    }

    // Pantalla verde = assets encontrados, roja = carpeta vacía o inexistente.
    const bool ok = mounted && vfs::count() > 0;
    bool running = true;
    while (running) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT) running = false;
            if (e.type == SDL_KEYDOWN && e.key.keysym.sym == SDLK_ESCAPE) running = false;
        }
        glClearColor(ok ? 0.1f : 0.6f, ok ? 0.5f : 0.1f, 0.1f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        SDL_GL_SwapWindow(win);
    }

    SDL_GL_DeleteContext(ctx);
    SDL_DestroyWindow(win);
    SDL_Quit();
    return 0;
}
