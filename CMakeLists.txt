cmake_minimum_required(VERSION 3.16)
project(sprally CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build de escritorio para desarrollar y probar sin Android.
add_library(vfs src/vfs.cpp)
target_include_directories(vfs PUBLIC src)

enable_testing()
add_executable(vfs_test tests/vfs_test.cpp)
target_link_libraries(vfs_test vfs)
add_test(NAME vfs_test COMMAND vfs_test)

find_package(SDL2 QUIET)
find_library(GLES2_LIB GLESv2)
if(SDL2_FOUND AND GLES2_LIB)
  add_executable(sprally src/main.cpp)
  target_include_directories(sprally PRIVATE ${SDL2_INCLUDE_DIRS})
  target_link_libraries(sprally vfs ${SDL2_LIBRARIES} ${GLES2_LIB})
else()
  message(STATUS "SDL2 o GLESv2 no encontrados: se omite el ejecutable 'sprally' (el test del VFS sí se compila)")
endif()
