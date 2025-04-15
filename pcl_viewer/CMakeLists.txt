cmake_minimum_required(VERSION 3.10)
project(pcl_viewer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Force g++-9 if needed
set(CMAKE_CXX_COMPILER g++-9)

find_package(PCL REQUIRED)

include_directories(${PCL_INCLUDE_DIRS})
link_directories(${PCL_LIBRARY_DIRS})
add_definitions(${PCL_DEFINITIONS})

add_executable(pcl_viewer visualize.cpp)

target_link_libraries(pcl_viewer ${PCL_LIBRARIES} stdc++fs)

