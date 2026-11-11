"""The NeMo Guardrails configuration, written as plain text here so it ships with the package and
cannot go missing from a Docker image.

Every rail is a small Colang flow that calls one custom action (see engine.py). The action holds
the logic; the flow only says "if the action says block, refuse and stop". No language model is
configured, because the fast rules need none, and the judge call uses the student's own model
through our code rather than through NeMo."""

YAML = """
colang_version: "1.0"
rails:
  input:
    flows:
      - learnloom input rail
  output:
    flows:
      - learnloom output rail
  tool_output:
    flows:
      - learnloom tool call rail
  tool_input:
    flows:
      - learnloom tool result rail
"""

COLANG = """
define bot learnloom refuse
  "refused"

define flow learnloom input rail
  $mn_in = execute mn_input
  if $mn_in["action"] == "block"
    bot learnloom refuse
    stop

define flow learnloom output rail
  $mn_out = execute mn_output
  if $mn_out["action"] == "block"
    bot learnloom refuse
    stop

define flow learnloom tool call rail
  $mn_tc = execute mn_tool_call(calls=$tool_calls)
  if $mn_tc["action"] == "block"
    bot learnloom refuse
    stop

define flow learnloom tool result rail
  $mn_tr = execute mn_tool_result(text=$tool_message, name=$tool_name)
  if $mn_tr["action"] == "block"
    bot learnloom refuse
    stop
"""
