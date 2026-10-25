cmake_minimum_required(VERSION 3.22)
project(sprally LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# cpp -> main -> src -> app -> android -> raíz del repo
set(REPO_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../../../../..)

add_subdirectory(${REPO_ROOT}/third_party/SDL2 ${CMAKE_BINARY_DIR}/SDL2)

# SDLActivity carga "libmain.so".
add_library(main SHARED
    ${REPO_ROOT}/src/main.cpp
    ${REPO_ROOT}/src/vfs.cpp)
target_include_directories(main PRIVATE ${REPO_ROOT}/src)
target_link_libraries(main SDL2 GLESv2 log)
