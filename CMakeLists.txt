cmake_minimum_required(VERSION 3.20)

project(TetrisOrchestrationAgent VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(orchestration_agent_lib
    orchestration/src/orchestration_agent.cpp
)

target_include_directories(orchestration_agent_lib
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/orchestration/include
)

add_executable(orchestration_agent_cli
    orchestration/src/main.cpp
)

target_link_libraries(orchestration_agent_cli
    PRIVATE orchestration_agent_lib
)

enable_testing()

add_executable(orchestration_agent_tests
    orchestration/tests/orchestration_agent_test.cpp
)

target_link_libraries(orchestration_agent_tests
    PRIVATE orchestration_agent_lib
)

add_test(
    NAME orchestration_agent_tests
    COMMAND orchestration_agent_tests
)
