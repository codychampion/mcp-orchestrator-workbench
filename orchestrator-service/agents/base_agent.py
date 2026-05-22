# Base agent class for autonomous agent execution
import asyncio
import json
from typing import Dict, Any, List, Optional
from planner.llm_client import call_llm

class BaseAgent:
    """
    Base class for all agents. Agents can think, decide, and act autonomously.
    """

    def __init__(self, role: str, goal: str, context: Dict[str, Any] = None):
        self.role = role
        self.goal = goal
        self.context = context or {}
        self.memory = []  # Stores agent's thought process and actions
        self.tools = []
        self.sub_agents = []

    async def think(self, situation: str, recent_tool_calls: list = None) -> str:
        """
        Agent thinks about the current situation and decides what to do next.
        Returns the agent's thoughts and decision.
        """
        # Build available tools description
        tools_desc = "Available tools:\n"
        if self.tools:
            for tool in self.tools:
                tools_desc += f"- {tool['name']}: {tool['description']}\n"
        else:
            tools_desc = "No tools available.\n"

        # Add warning about recent tool usage
        recent_tools_warning = ""
        if recent_tool_calls:
            recent_tools_warning = f"\nWARNING - Recently used tools: {recent_tool_calls[-3:]}\nAvoid calling the same tool repeatedly. Try different tools or complete the task.\n"

        prompt = f"""You are a {self.role} agent working towards: {self.goal}

Current situation: {situation}

Context:
{json.dumps(self.context, indent=2)}

Previous actions:
{json.dumps(self.memory[-3:], indent=2) if self.memory else "No previous actions"}

{tools_desc}{recent_tools_warning}

Think step by step about what to do next. Consider:
1. What information do you have?
2. What do you need to accomplish?
3. What's the best next action?
4. Should you use one of the available tools?
5. Have you already tried this tool? Try a different approach if so.
6. Can you complete the task now with the information you have?

Respond in JSON format:
{{
  "thoughts": "your reasoning process",
  "decision": "what you decide to do",
  "action": "call_tool" | "delegate" | "respond" | "complete",
  "action_details": {{
    "tool": "tool_name" (if action is call_tool - must be from available tools),
    "params": {{}} (if action is call_tool - match tool's parameter schema),
    "delegate_goal": "goal" (if action is delegate),
    "message": "message" (if action is respond or complete)
  }}
}}
"""
        messages = [
            {"role": "system", "content": f"You are an autonomous {self.role} agent. Think carefully and make decisions. You have access to tools to help accomplish your goal."},
            {"role": "user", "content": prompt}
        ]

        response = call_llm(messages, max_tokens=800)

        try:
            decision = json.loads(response)
            self.memory.append({
                "type": "thought",
                "content": decision,
                "timestamp": asyncio.get_event_loop().time()
            })
            return decision
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return {
                "thoughts": response,
                "decision": "respond",
                "action": "respond",
                "action_details": {"message": response}
            }

    async def execute_action(self, decision: Dict[str, Any], tool_executor) -> Any:
        """
        Execute the action decided by the agent.
        """
        action = decision.get("action")
        action_details = decision.get("action_details", {})

        if action == "call_tool":
            tool_name = action_details.get("tool")
            params = action_details.get("params", {})
            result = await tool_executor(tool_name, params)
            self.memory.append({
                "type": "action",
                "action": "tool_call",
                "tool": tool_name,
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            })
            return result

        elif action == "delegate":
            agent_type = action_details.get("agent_type")
            agent_goal = action_details.get("goal", self.goal)
            # Create sub-agent
            sub_agent = create_agent(agent_type, agent_goal, self.context)
            self.sub_agents.append(sub_agent)
            result = await sub_agent.run(tool_executor)
            self.memory.append({
                "type": "delegation",
                "agent_type": agent_type,
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            })
            return result

        elif action == "respond" or action == "complete":
            message = action_details.get("message", "Task completed")
            self.memory.append({
                "type": "response",
                "message": message,
                "timestamp": asyncio.get_event_loop().time()
            })
            return message

        return None

    async def run(self, tool_executor, max_iterations: int = 10, max_same_tool_calls: int = 3) -> Dict[str, Any]:
        """
        Main agent execution loop with loop detection. Agent thinks and acts until goal is achieved.
        """
        iteration = 0
        recent_tool_calls = []  # Track recent tool calls to detect loops
        result = None

        print(f"\n[AGENT-{self.role.upper()}] Starting execution with max_iterations={max_iterations}, max_same_tool_calls={max_same_tool_calls}")

        while iteration < max_iterations:
            # Think about current situation
            situation = f"Iteration {iteration + 1}: Working towards '{self.goal}'"
            decision = await self.think(situation, recent_tool_calls)

            print(f"[AGENT-{self.role.upper()}] Iteration {iteration + 1} - Action: {decision.get('action')}")

            # Yield decision for UI updates
            yield {
                "type": "thought",
                "agent": self.role,
                "decision": decision,
                "iteration": iteration
            }

            # Check for loop detection if calling a tool
            if decision.get("action") == "call_tool":
                tool_name = decision.get("action_details", {}).get("tool")
                tool_params = str(sorted(decision.get("action_details", {}).get("params", {}).items()))
                tool_signature = f"{tool_name}:{tool_params}"

                # Count how many times this exact tool call was made recently
                recent_same_calls = [call for call in recent_tool_calls[-5:] if call == tool_signature]

                if len(recent_same_calls) >= max_same_tool_calls:
                    print(f"[AGENT-{self.role.upper()}] ⚠️  LOOP DETECTED: '{tool_name}' called {len(recent_same_calls)} times with same params")
                    print(f"[AGENT-{self.role.upper()}] Recent calls: {recent_tool_calls[-5:]}")

                    # Force completion and yield loop detection
                    result = {
                        "status": "loop_detected",
                        "message": f"Loop detected: '{tool_name}' was called {len(recent_same_calls)} times repeatedly. Stopping execution.",
                        "tool": tool_name,
                        "recent_calls": recent_tool_calls[-5:]
                    }

                    yield {
                        "type": "loop_detected",
                        "agent": self.role,
                        "tool": tool_name,
                        "call_count": len(recent_same_calls),
                        "iteration": iteration
                    }

                    # Yield final state
                    yield {
                        "type": "complete",
                        "agent": self.role,
                        "goal": self.goal,
                        "iterations": iteration + 1,
                        "memory": self.memory,
                        "result": result,
                        "reason": "loop_detected"
                    }

                    return

                # Track this tool call
                recent_tool_calls.append(tool_signature)
                print(f"[AGENT-{self.role.upper()}] Tracked tool call: {tool_name}")

            # Execute the decided action
            result = await self.execute_action(decision, tool_executor)

            # Yield result for UI updates
            yield {
                "type": "action_result",
                "agent": self.role,
                "result": result,
                "iteration": iteration
            }

            # Check if agent decided to complete
            if decision.get("action") == "complete":
                print(f"[AGENT-{self.role.upper()}] Agent marked task as complete")
                break

            iteration += 1

        # Yield final state
        print(f"[AGENT-{self.role.upper()}] Execution finished after {iteration + 1} iterations")
        yield {
            "type": "complete",
            "agent": self.role,
            "goal": self.goal,
            "iterations": iteration + 1,
            "memory": self.memory,
            "result": result
        }


class ExecutorAgent(BaseAgent):
    """Agent specialized in executing tasks"""

    def __init__(self, goal: str, context: Dict[str, Any] = None):
        super().__init__("Executor", goal, context)


class AnalystAgent(BaseAgent):
    """Agent specialized in analyzing data"""

    def __init__(self, goal: str, context: Dict[str, Any] = None):
        super().__init__("Analyst", goal, context)


def create_agent(agent_type: str, goal: str, context: Dict[str, Any] = None) -> BaseAgent:
    """Factory function to create agents"""
    agents = {
        "executor": ExecutorAgent,
        "analyst": AnalystAgent
    }

    agent_class = agents.get(agent_type.lower(), ExecutorAgent)  # Default to ExecutorAgent
    return agent_class(goal, context)
