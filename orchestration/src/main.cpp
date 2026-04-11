#include "orchestration/orchestration_agent.hpp"

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

struct CliArgs {
    std::string project_name = "Tetris";
    std::string objective = "Generate production artifacts for an end-to-end agent runtime.";
    std::string task_id = "task-tetris-runtime";
    std::filesystem::path output_dir = "runtime/orchestration";
};

void print_help() {
    std::cout
        << "Usage: orchestration_agent_cli [--project-name NAME] [--objective TEXT] "
        << "[--task-id ID] [--output-dir PATH]\n";
}

CliArgs parse_args(int argc, char** argv) {
    CliArgs args;
    for (int index = 1; index < argc; ++index) {
        const std::string current = argv[index];

        auto require_value = [&](const std::string& option) -> std::string {
            if (index + 1 >= argc) {
                throw std::runtime_error("Missing value for " + option);
            }
            ++index;
            return argv[index];
        };

        if (current == "--project-name") {
            args.project_name = require_value(current);
        } else if (current == "--objective") {
            args.objective = require_value(current);
        } else if (current == "--task-id") {
            args.task_id = require_value(current);
        } else if (current == "--output-dir") {
            args.output_dir = require_value(current);
        } else if (current == "--help" || current == "-h") {
            print_help();
            std::exit(0);
        } else {
            throw std::runtime_error("Unknown option: " + current);
        }
    }

    return args;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const CliArgs args = parse_args(argc, argv);

        orchestration::OrchestrationAgent agent;
        const auto plan = agent.build_plan({
            .project_name = args.project_name,
            .objective = args.objective,
            .task_id = args.task_id,
        });

        agent.write_bundle(plan, args.output_dir);

        std::cout << "Generated orchestration bundle in " << args.output_dir.string() << "\n";
        std::cout << "Sub-agents: " << plan.sub_agents.size() << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "orchestration_agent_cli: " << error.what() << "\n";
        return 1;
    }
}
