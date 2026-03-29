#ifndef ORCHESTRATION_AGENT_HPP
#define ORCHESTRATION_AGENT_HPP

#include <string>
#include <vector>
#include <memory>

namespace orchestration {

class OrchestrationAgent {
public:
    OrchestrationAgent();
    ~OrchestrationAgent();

    /**
     * @brief Escapes a string for use in a JSON value.
     * Moved to public to allow access from helper functions in the implementation file.
     */
    static std::string escape_json(const std::string& value);

    bool initialize(const std::string& config_path);
    std::string execute_command(const std::string& command);

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl;
};

} // namespace orchestration

#endif // ORCHESTRATION_AGENT_HPP
