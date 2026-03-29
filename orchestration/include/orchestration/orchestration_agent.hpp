#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace orchestration {

struct FlowTransition {
    std::string from;
    std::string to;
    std::string trigger;
    std::string description;
};

struct FlowDiagram {
    std::string agent_id;
    std::string title;
    std::string entry_state;
    std::string terminal_state;
    std::vector<std::string> states;
    std::vector<FlowTransition> transitions;
};

struct ProductionArtifact {
    std::string kind;
    std::string path;
    std::string description;
};

struct SubAgentSpec {
    std::string id;
    std::string role;
    std::string objective;
    std::vector<std::string> responsibilities;
    std::vector<std::string> upstream_dependencies;
    std::vector<std::string> downstream_handoffs;
    std::vector<ProductionArtifact> managed_artifacts;
    std::string runtime_entrypoint;
    std::string tool_module;
    FlowDiagram flow_diagram;
};

struct OrchestrationRequest {
    std::string project_name;
    std::string objective;
    std::string task_id;
};

struct OrchestrationPlan {
    std::string generated_at;
    std::string project_name;
    std::string objective;
    std::string task_id;
    std::string mcp_server_entrypoint;
    std::string python_tool_library;
    std::vector<ProductionArtifact> production_artifacts;
    std::vector<SubAgentSpec> sub_agents;
};

class OrchestrationAgent {
  public:
    OrchestrationPlan build_plan(const OrchestrationRequest& request) const;
    void write_bundle(const OrchestrationPlan& plan, const std::filesystem::path& output_dir) const;

  private:
    std::vector<SubAgentSpec> build_default_sub_agents() const;
    static std::string utc_timestamp();
    static std::string escape_json(const std::string& value);
    static std::string slugify(const std::string& value);
};

}  // namespace orchestration
