#include "orchestration/orchestration_agent.hpp"

#include <algorithm>
#include <chrono>
#include <cctype>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace orchestration {
namespace {

std::string json_string(const std::string& value) {
    return "\"" + OrchestrationAgent::escape_json(value) + "\"";
}

template <typename Container, typename Fn>
std::string join_json_array(const Container& values, const Fn& render) {
    std::ostringstream out;
    out << "[";
    bool first = true;
    for (const auto& value : values) {
        if (!first) {
            out << ",";
        }
        out << render(value);
        first = false;
    }
    out << "]";
    return out.str();
}

std::string render_transition(const FlowTransition& transition) {
    std::ostringstream out;
    out << "{"
        << "\"from\":" << json_string(transition.from) << ","
        << "\"to\":" << json_string(transition.to) << ","
        << "\"trigger\":" << json_string(transition.trigger) << ","
        << "\"description\":" << json_string(transition.description)
        << "}";
    return out.str();
}

std::string render_artifact(const ProductionArtifact& artifact) {
    std::ostringstream out;
    out << "{"
        << "\"kind\":" << json_string(artifact.kind) << ","
        << "\"path\":" << json_string(artifact.path) << ","
        << "\"description\":" << json_string(artifact.description)
        << "}";
    return out.str();
}

std::string render_flow_diagram(const FlowDiagram& flow_diagram) {
    std::ostringstream out;
    out << "{"
        << "\"agent_id\":" << json_string(flow_diagram.agent_id) << ","
        << "\"title\":" << json_string(flow_diagram.title) << ","
        << "\"entry_state\":" << json_string(flow_diagram.entry_state) << ","
        << "\"terminal_state\":" << json_string(flow_diagram.terminal_state) << ","
        << "\"states\":" << join_json_array(flow_diagram.states, [](const std::string& state) {
               return json_string(state);
           })
        << ","
        << "\"transitions\":" << join_json_array(flow_diagram.transitions, render_transition)
        << "}";
    return out.str();
}

std::string render_sub_agent(const SubAgentSpec& sub_agent) {
    std::ostringstream out;
    out << "{"
        << "\"id\":" << json_string(sub_agent.id) << ","
        << "\"role\":" << json_string(sub_agent.role) << ","
        << "\"objective\":" << json_string(sub_agent.objective) << ","
        << "\"responsibilities\":" << join_json_array(sub_agent.responsibilities, [](const std::string& item) {
               return json_string(item);
           })
        << ","
        << "\"upstream_dependencies\":" << join_json_array(sub_agent.upstream_dependencies, [](const std::string& item) {
               return json_string(item);
           })
        << ","
        << "\"downstream_handoffs\":" << join_json_array(sub_agent.downstream_handoffs, [](const std::string& item) {
               return json_string(item);
           })
        << ","
        << "\"managed_artifacts\":" << join_json_array(sub_agent.managed_artifacts, render_artifact)
        << ","
        << "\"runtime_entrypoint\":" << json_string(sub_agent.runtime_entrypoint) << ","
        << "\"tool_module\":" << json_string(sub_agent.tool_module) << ","
        << "\"flow_diagram\":" << render_flow_diagram(sub_agent.flow_diagram)
        << "}";
    return out.str();
}

std::string render_plan(const OrchestrationPlan& plan) {
    std::ostringstream out;
    out << "{"
        << "\"generated_at\":" << json_string(plan.generated_at) << ","
        << "\"project_name\":" << json_string(plan.project_name) << ","
        << "\"objective\":" << json_string(plan.objective) << ","
        << "\"task_id\":" << json_string(plan.task_id) << ","
        << "\"mcp_server_entrypoint\":" << json_string(plan.mcp_server_entrypoint) << ","
        << "\"python_tool_library\":" << json_string(plan.python_tool_library) << ","
        << "\"production_artifacts\":" << join_json_array(plan.production_artifacts, render_artifact)
        << ","
        << "\"sub_agents\":" << join_json_array(plan.sub_agents, render_sub_agent)
        << "}";
    return out.str();
}

std::string render_index(const OrchestrationPlan& plan) {
    std::ostringstream out;
    out << "{"
        << "\"generated_at\":" << json_string(plan.generated_at) << ","
        << "\"project_name\":" << json_string(plan.project_name) << ","
        << "\"tool_library\":" << json_string(plan.python_tool_library) << ","
        << "\"mcp_server_entrypoint\":" << json_string(plan.mcp_server_entrypoint) << ","
        << "\"agents\":[";

    for (std::size_t i = 0; i < plan.sub_agents.size(); ++i) {
        const auto& sub_agent = plan.sub_agents[i];
        out << "{"
            << "\"agent_id\":" << json_string(sub_agent.id) << ","
            << "\"role\":" << json_string(sub_agent.role) << ","
            << "\"flow_path\":" << json_string("flows/" + sub_agent.id + ".json") << ","
            << "\"entry_state\":" << json_string(sub_agent.flow_diagram.entry_state) << ","
            << "\"terminal_state\":" << json_string(sub_agent.flow_diagram.terminal_state) << ","
            << "\"runtime_entrypoint\":" << json_string(sub_agent.runtime_entrypoint) << ","
            << "\"tool_module\":" << json_string(sub_agent.tool_module)
            << "}";
        if (i + 1 < plan.sub_agents.size()) {
            out << ",";
        }
    }

    out << "]}";
    return out.str();
}

void write_text_file(const std::filesystem::path& path, const std::string& body) {
    std::ofstream stream(path, std::ios::binary);
    if (!stream) {
        throw std::runtime_error("Failed to open " + path.string() + " for writing.");
    }
    stream << body;
}

FlowDiagram make_flow(
    std::string agent_id,
    std::string title,
    std::vector<std::string> states,
    std::vector<FlowTransition> transitions
) {
    return FlowDiagram{
        .agent_id = std::move(agent_id),
        .title = std::move(title),
        .entry_state = states.front(),
        .terminal_state = states.back(),
        .states = std::move(states),
        .transitions = std::move(transitions),
    };
}

}  // namespace

OrchestrationPlan OrchestrationAgent::build_plan(const OrchestrationRequest& request) const {
    OrchestrationPlan plan;
    plan.generated_at = utc_timestamp();
    plan.project_name = request.project_name.empty() ? "Tetris" : request.project_name;
    plan.objective = request.objective.empty()
        ? "Generate a production-ready orchestration bundle for design, build, QA, and release."
        : request.objective;
    plan.task_id = request.task_id.empty() ? "task-" + slugify(plan.project_name) : request.task_id;
    plan.mcp_server_entrypoint = "orchestration_mcp_server.py";
    plan.python_tool_library = "agent_flow_tools";
    plan.production_artifacts = {
        {"workflow", ".github/workflows/orchestration-agent-release.yml", "Build, test, package, and upload orchestration artifacts in GitHub Actions."},
        {"script", "scripts/build_orchestration_agent.sh", "Build the C++ orchestration agent with CMake."},
        {"script", "scripts/generate_orchestration_bundle.sh", "Generate the sub-agent plan and flow bundle."},
        {"script", "scripts/release_orchestration_bundle.sh", "Package the runtime bundle for distribution and CI uploads."},
        {"mcp_server", "orchestration_mcp_server.py", "Expose indexed flow diagrams as MCP tools for coding agents."}
    };
    plan.sub_agents = build_default_sub_agents();
    return plan;
}

void OrchestrationAgent::write_bundle(const OrchestrationPlan& plan, const std::filesystem::path& output_dir) const {
    const auto flow_dir = output_dir / "flows";
    std::filesystem::create_directories(flow_dir);

    write_text_file(output_dir / "plan.json", render_plan(plan));
    write_text_file(output_dir / "flow-index.json", render_index(plan));

    for (const auto& sub_agent : plan.sub_agents) {
        write_text_file(flow_dir / (sub_agent.id + ".json"), render_flow_diagram(sub_agent.flow_diagram));
    }
}

std::vector<SubAgentSpec> OrchestrationAgent::build_default_sub_agents() const {
    return {
        SubAgentSpec{
            .id = "architecture-agent",
            .role = "System architect",
            .objective = "Translate the objective into a release-ready multi-agent execution plan.",
            .responsibilities = {
                "Break the user objective into bounded sub-agent roles.",
                "Define working-state flow diagrams and delivery checkpoints.",
                "Publish handoff criteria for implementation, QA, and release agents."
            },
            .upstream_dependencies = {},
            .downstream_handoffs = {"implementation-agent", "qa-agent", "release-agent"},
            .managed_artifacts = {
                {"plan", "runtime/orchestration/plan.json", "Top-level orchestration plan consumed by downstream agents."},
                {"flow", "runtime/orchestration/flows/architecture-agent.json", "Lifecycle states for the architecture agent."}
            },
            .runtime_entrypoint = "scripts/generate_orchestration_bundle.sh",
            .tool_module = "agent_flow_tools.flow_registry",
            .flow_diagram = make_flow(
                "architecture-agent",
                "Architecture Agent Working State",
                {"planned", "researching", "designing", "handoff_ready", "completed"},
                {
                    {"planned", "researching", "objective accepted", "The orchestrator assigns a concrete objective and repo scope."},
                    {"researching", "designing", "context indexed", "Repository facts and GitHub production targets are collected."},
                    {"designing", "handoff_ready", "plan drafted", "Sub-agent manifests, scripts, and artifact routes are defined."},
                    {"handoff_ready", "completed", "plan approved", "The orchestration plan is written to the runtime bundle."}
                }
            )
        },
        SubAgentSpec{
            .id = "implementation-agent",
            .role = "Coding agent",
            .objective = "Build the runtime, tooling, and integration code defined by the orchestration plan.",
            .responsibilities = {
                "Implement language runtimes and shared contracts.",
                "Wire generated artifacts into the MCP surface.",
                "Keep GitHub workflow, runtime scripts, and code in sync."
            },
            .upstream_dependencies = {"architecture-agent"},
            .downstream_handoffs = {"qa-agent", "release-agent"},
            .managed_artifacts = {
                {"source", "orchestration/src/orchestration_agent.cpp", "C++ runtime used to generate the orchestration bundle."},
                {"source", "agent_flow_tools/flow_registry.py", "Python library that indexes generated flow diagrams."}
            },
            .runtime_entrypoint = "scripts/build_orchestration_agent.sh",
            .tool_module = "agent_flow_tools.flow_registry",
            .flow_diagram = make_flow(
                "implementation-agent",
                "Implementation Agent Working State",
                {"queued", "building", "integrating", "ready_for_review", "completed"},
                {
                    {"queued", "building", "design handoff received", "The coding agent starts implementing generated work items."},
                    {"building", "integrating", "core features compile", "Language runtimes and interfaces are joined into one bundle."},
                    {"integrating", "ready_for_review", "tooling verified", "MCP tools and scripts are aligned with the generated plan."},
                    {"ready_for_review", "completed", "review passed", "Implementation artifacts are ready for QA."}
                }
            )
        },
        SubAgentSpec{
            .id = "qa-agent",
            .role = "Verification agent",
            .objective = "Validate flow integrity, runtime behavior, and packaging expectations before release.",
            .responsibilities = {
                "Execute C++ and Python verification paths.",
                "Validate flow index structure and release handoffs.",
                "Report regressions before GitHub packaging starts."
            },
            .upstream_dependencies = {"architecture-agent", "implementation-agent"},
            .downstream_handoffs = {"release-agent"},
            .managed_artifacts = {
                {"test", "tests/test_orchestration_flow_registry.py", "Python coverage for the indexed flow toolchain."},
                {"test", "orchestration/tests/orchestration_agent_test.cpp", "C++ coverage for bundle generation."}
            },
            .runtime_entrypoint = "scripts/release_orchestration_bundle.sh",
            .tool_module = "agent_flow_tools.flow_registry",
            .flow_diagram = make_flow(
                "qa-agent",
                "QA Agent Working State",
                {"queued", "validating", "fixing_feedback", "release_candidate", "completed"},
                {
                    {"queued", "validating", "implementation handoff", "The QA agent receives a buildable runtime bundle."},
                    {"validating", "fixing_feedback", "issue found", "Tests or artifact checks request another implementation pass."},
                    {"fixing_feedback", "validating", "fix submitted", "The updated implementation returns for re-validation."},
                    {"validating", "release_candidate", "all checks green", "The bundle is fit for packaging and publication."},
                    {"release_candidate", "completed", "release approved", "QA hands the bundle to the release agent."}
                }
            )
        },
        SubAgentSpec{
            .id = "release-agent",
            .role = "Release manager",
            .objective = "Package the orchestration runtime as a GitHub-ready production artifact set.",
            .responsibilities = {
                "Package scripts, generated bundle files, and MCP tooling.",
                "Publish GitHub Actions artifacts and release notes inputs.",
                "Keep shell runtime entrypoints aligned with the generated plan."
            },
            .upstream_dependencies = {"architecture-agent", "implementation-agent", "qa-agent"},
            .downstream_handoffs = {},
            .managed_artifacts = {
                {"artifact", "dist/orchestration-bundle", "Packaged output uploaded by GitHub Actions."},
                {"workflow", ".github/workflows/orchestration-agent-release.yml", "CI path responsible for building and uploading the production bundle."}
            },
            .runtime_entrypoint = "scripts/release_orchestration_bundle.sh",
            .tool_module = "agent_flow_tools.flow_registry",
            .flow_diagram = make_flow(
                "release-agent",
                "Release Agent Working State",
                {"queued", "assembling_artifacts", "publishing_github_artifacts", "shipped", "completed"},
                {
                    {"queued", "assembling_artifacts", "qa approved", "Release packaging begins once QA marks the bundle ready."},
                    {"assembling_artifacts", "publishing_github_artifacts", "bundle created", "Scripts, flows, and docs are staged for upload."},
                    {"publishing_github_artifacts", "shipped", "github workflow complete", "GitHub Actions stores the production bundle as artifacts."},
                    {"shipped", "completed", "release notes attached", "The runtime package is ready for downstream deployment."}
                }
            )
        }
    };
}

std::string OrchestrationAgent::utc_timestamp() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t time = std::chrono::system_clock::to_time_t(now);

    std::tm utc{};
#if defined(_WIN32)
    gmtime_s(&utc, &time);
#else
    gmtime_r(&time, &utc);
#endif

    std::ostringstream out;
    out << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
    return out.str();
}

std::string OrchestrationAgent::escape_json(const std::string& value) {
    std::ostringstream out;
    for (const char ch : value) {
        switch (ch) {
            case '\\':
                out << "\\\\";
                break;
            case '"':
                out << "\\\"";
                break;
            case '\n':
                out << "\\n";
                break;
            case '\r':
                out << "\\r";
                break;
            case '\t':
                out << "\\t";
                break;
            default:
                out << ch;
                break;
        }
    }
    return out.str();
}

std::string OrchestrationAgent::slugify(const std::string& value) {
    std::string slug;
    slug.reserve(value.size());

    bool needs_dash = false;
    for (const char ch : value) {
        if (std::isalnum(static_cast<unsigned char>(ch))) {
            if (needs_dash && !slug.empty()) {
                slug.push_back('-');
            }
            slug.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
            needs_dash = false;
        } else if (!slug.empty()) {
            needs_dash = true;
        }
    }

    return slug.empty() ? "orchestration-task" : slug;
}

}  // namespace orchestration
