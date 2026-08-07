cmake_minimum_required(VERSION 3.16)
project(fl_on_chain LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

enable_testing()

add_library(tensor STATIC src/cpp/utils/tensor.cpp)
target_include_directories(tensor PUBLIC src/cpp/utils)

add_executable(tensor_tests tests/tensor_tests.cpp)
target_link_libraries(tensor_tests PRIVATE tensor)
add_test(NAME tensor_tests COMMAND tensor_tests)
