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

import abc
from typing import Any, Dict, Optional, Tuple

from gem.multiagent.multi_agent_env import MultiAgentEnv


class ParallelEnv(MultiAgentEnv):
    def __init__(self):
        super().__init__()
        self.metadata = {"is_parallelizable": True}

    @abc.abstractmethod
    def step(self, actions: Dict[str, str]) -> Tuple[
        Dict[str, str],
        Dict[str, float],
        Dict[str, bool],
        Dict[str, bool],
        Dict[str, Dict],
    ]:
        self._validate_actions(actions)
        raise NotImplementedError

    @abc.abstractmethod
    def reset(
        self, seed: Optional[int] = None
    ) -> Tuple[Dict[str, str], Dict[str, Dict]]:
        raise NotImplementedError

    def render(self) -> Optional[Any]:
        return None

    def state(self) -> Any:
        raise NotImplementedError

    def close(self) -> None:
        pass

    def _validate_actions(self, actions: Dict[str, str]) -> None:
        action_agents = set(actions.keys())
        active_agents = set(self.agents)

        if action_agents != active_agents:
            missing = active_agents - action_agents
            extra = action_agents - active_agents

            error_parts = []
            if missing:
                error_parts.append(f"Missing actions for agents: {sorted(missing)}")
            if extra:
                error_parts.append(
                    f"Actions provided for non-active agents: {sorted(extra)}"
                )

            raise ValueError(". ".join(error_parts))

    def _remove_dead_agents(self) -> None:
        self.agents = [
            agent
            for agent in self.agents
            if not (
                self.terminations.get(agent, False)
                or self.truncations.get(agent, False)
            )
        ]
