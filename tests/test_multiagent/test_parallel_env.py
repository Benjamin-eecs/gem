# Copyright 2025 AxonRL Team. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for Parallel environments."""

from typing import Dict, Optional, Tuple

import pytest

from gem.multiagent.parallel_env import ParallelEnv


class SimpleParallelEnv(ParallelEnv):
    """Simple parallel environment for testing."""

    def __init__(self):
        super().__init__()
        self.possible_agents = ["agent1", "agent2", "agent3"]
        self.agents = self.possible_agents.copy()

        self.step_count = 0
        self.max_steps = 10

        # Initialize state
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.rewards = {agent: 0.0 for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}

    def step(self, actions: Dict[str, str]) -> Tuple[
        Dict[str, str],
        Dict[str, float],
        Dict[str, bool],
        Dict[str, bool],
        Dict[str, Dict],
    ]:
        # Validate actions
        self._validate_actions(actions)

        observations = {}
        rewards = {}
        terminations = {}
        truncations = {}
        infos = {}

        # Process each agent's action
        for agent, action in actions.items():
            # Generate observation
            observations[agent] = (
                f"Step {self.step_count + 1} result for {agent} after {action}"
            )

            # Calculate reward
            if action == "good":
                rewards[agent] = 1.0
            elif action == "bad":
                rewards[agent] = -1.0
            else:
                rewards[agent] = 0.0

            # Check termination
            if action == "terminate":
                terminations[agent] = True
            else:
                terminations[agent] = False

            # Info
            infos[agent] = {"step": self.step_count + 1}

        # Increment step count
        self.step_count += 1

        # Check truncation
        if self.step_count >= self.max_steps:
            for agent in self.agents:
                truncations[agent] = True
        else:
            for agent in self.agents:
                truncations[agent] = False

        # Update internal state
        self.terminations = terminations
        self.truncations = truncations
        self.rewards = rewards
        self.infos = infos

        # Remove dead agents
        self._remove_dead_agents()

        return observations, rewards, terminations, truncations, infos

    def reset(
        self, seed: Optional[int] = None
    ) -> Tuple[Dict[str, str], Dict[str, Dict]]:
        super().reset(seed)

        self.agents = self.possible_agents.copy()
        self.step_count = 0

        observations = {}
        infos = {}

        for agent in self.agents:
            observations[agent] = f"Initial observation for {agent}"
            infos[agent] = {"initial": True}

        return observations, infos

    def state(self):
        """Return global state."""
        return {
            "step_count": self.step_count,
            "agents": self.agents.copy(),
            "terminations": self.terminations.copy(),
            "truncations": self.truncations.copy(),
        }


class TestParallelEnv:
    """Test Parallel environment functionality."""

    def test_initialization(self):
        """Test parallel environment initialization."""
        env = SimpleParallelEnv()

        assert len(env.agents) == 3
        assert env.step_count == 0
        assert env.metadata["is_parallelizable"] is True

    def test_reset(self):
        """Test environment reset."""
        env = SimpleParallelEnv()

        observations, infos = env.reset()

        assert len(observations) == 3
        assert len(infos) == 3
        assert "agent1" in observations
        assert "Initial observation" in observations["agent1"]
        assert infos["agent1"]["initial"] is True

    def test_step_with_all_agents(self):
        """Test stepping with actions from all agents."""
        env = SimpleParallelEnv()
        env.reset()

        actions = {"agent1": "good", "agent2": "bad", "agent3": "neutral"}

        obs, rewards, terms, truncs, infos = env.step(actions)

        assert len(obs) == 3
        assert len(rewards) == 3
        assert rewards["agent1"] == 1.0
        assert rewards["agent2"] == -1.0
        assert rewards["agent3"] == 0.0
        assert env.step_count == 1
        assert all(not term for term in terms.values())
        assert all(not trunc for trunc in truncs.values())

    def test_step_missing_agents(self):
        """Test step fails when actions missing for some agents."""
        env = SimpleParallelEnv()
        env.reset()

        actions = {
            "agent1": "good",
            "agent2": "bad",
            # Missing agent3
        }

        with pytest.raises(ValueError, match="Missing actions for agents"):
            env.step(actions)

    def test_step_extra_agents(self):
        """Test step fails when actions provided for non-active agents."""
        env = SimpleParallelEnv()
        env.reset()

        actions = {
            "agent1": "good",
            "agent2": "bad",
            "agent3": "neutral",
            "agent4": "extra",  # Non-existent agent
        }

        with pytest.raises(ValueError, match="Actions provided for non-active agents"):
            env.step(actions)

    def test_termination(self):
        """Test agent termination."""
        env = SimpleParallelEnv()
        env.reset()

        actions = {"agent1": "terminate", "agent2": "good", "agent3": "good"}

        obs, rewards, terms, truncs, infos = env.step(actions)

        assert terms["agent1"] is True
        assert terms["agent2"] is False
        assert terms["agent3"] is False

        # Agent1 should be removed from active agents
        assert "agent1" not in env.agents
        assert "agent2" in env.agents
        assert "agent3" in env.agents

    def test_truncation(self):
        """Test environment truncation."""
        env = SimpleParallelEnv()
        env.reset()
        env.max_steps = 2

        actions = {"agent1": "good", "agent2": "good", "agent3": "good"}

        # First step
        obs, rewards, terms, truncs, infos = env.step(actions)
        assert all(not trunc for trunc in truncs.values())

        # Second step - should truncate
        obs, rewards, terms, truncs, infos = env.step(actions)
        assert all(trunc for trunc in truncs.values())

    def test_remove_dead_agents(self):
        """Test removal of terminated/truncated agents."""
        env = SimpleParallelEnv()
        env.reset()

        # Terminate one agent
        actions = {"agent1": "terminate", "agent2": "good", "agent3": "good"}

        env.step(actions)

        assert len(env.agents) == 2
        assert "agent1" not in env.agents

        # Next step should only require actions for remaining agents
        actions = {"agent2": "good", "agent3": "good"}

        # Should not raise error
        obs, rewards, terms, truncs, infos = env.step(actions)
        assert len(obs) == 2

    def test_validate_actions(self):
        """Test action validation method."""
        env = SimpleParallelEnv()
        env.reset()

        # Valid actions
        env._validate_actions(
            {"agent1": "action", "agent2": "action", "agent3": "action"}
        )

        # Missing agent
        with pytest.raises(ValueError, match="Missing actions"):
            env._validate_actions({"agent1": "action", "agent2": "action"})

        # Extra agent
        with pytest.raises(ValueError, match="non-active agents"):
            env._validate_actions(
                {
                    "agent1": "action",
                    "agent2": "action",
                    "agent3": "action",
                    "agent4": "action",
                }
            )

    def test_multiple_steps(self):
        """Test multiple steps in sequence."""
        env = SimpleParallelEnv()
        env.reset()

        for i in range(3):
            actions = {agent: "good" for agent in env.agents}
            obs, rewards, terms, truncs, infos = env.step(actions)

            assert env.step_count == i + 1
            assert all(reward == 1.0 for reward in rewards.values())
            assert all(info["step"] == i + 1 for info in infos.values())

    def test_global_state(self):
        """Test global state method."""
        env = SimpleParallelEnv()
        env.reset()

        state = env.state()

        assert state["step_count"] == 0
        assert len(state["agents"]) == 3
        assert all(not term for term in state["terminations"].values())
        assert all(not trunc for trunc in state["truncations"].values())

        # Step and check state again
        actions = {agent: "good" for agent in env.agents}
        env.step(actions)

        state = env.state()
        assert state["step_count"] == 1
