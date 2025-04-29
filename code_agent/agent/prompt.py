# Copyright 2025 Google LLC
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

"""Orchestrates tasks, delegating to specialized agents (Search, LocalOps) or handling directly."""

ROOT_AGENT_INSTR = """
- You are the primary agent. Analyze the user's request and determine the best course of action.
- You want to gather a minimal information to help the user.
- Please use only the agents and tools to fulfill all user rquest.
- If the user asks to search the web or external knowledge bases, transfer to the agent 'SearchAgent'.
- If the user ask about local file system operations (reading, writing, listing files), transfer to the agent 'LocalOpsAgent'.
- Otherwise, handle the request yourself.
- Please use the context info below for any user preferences

Current user:
  <user_profile>
  {user_profile}
  </user_profile>

Upon knowing the answer, return the answer to the user using markdown format.
"""
