#include "orchestration/orchestration_agent.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace {

std::string read_file(const std::filesystem::path& path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        throw std::runtime_error("Unable to open " + path.string());
    }
    std::ostringstream buffer;
    buffer << stream.rdbuf();
    return buffer.str();
}

void assert_true(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        orchestration::OrchestrationAgent agent;
        const auto plan = agent.build_plan({
            .project_name = "Tetris",
            .objective = "Verify the orchestration runtime bundle.",
            .task_id = "test-runtime-bundle",
        });

        assert_true(plan.sub_agents.size() == 4, "Expected four default sub-agents.");
        assert_true(plan.python_tool_library == "agent_flow_tools", "Expected the Python tool library to be indexed.");

        const auto output_dir = std::filesystem::temp_directory_path() / "orchestration-agent-tests";
        std::filesystem::remove_all(output_dir);
        agent.write_bundle(plan, output_dir);

        assert_true(std::filesystem::exists(output_dir / "plan.json"), "plan.json should be written.");
        assert_true(std::filesystem::exists(output_dir / "flow-index.json"), "flow-index.json should be written.");
        assert_true(std::filesystem::exists(output_dir / "flows" / "release-agent.json"), "release flow should be written.");

        const auto plan_json = read_file(output_dir / "plan.json");
        const auto index_json = read_file(output_dir / "flow-index.json");

        assert_true(plan_json.find("release-agent") != std::string::npos, "Plan should reference the release agent.");
        assert_true(index_json.find("agent_flow_tools.flow_registry") != std::string::npos, "Index should point to the Python tool module.");

        std::filesystem::remove_all(output_dir);
        std::cout << "orchestration_agent_tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
