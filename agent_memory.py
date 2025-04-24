#!/usr/bin/env python3
"""
Agent Memory Manager

This module provides memory functionality for agents to remember conversations.
It uses Agno's memory features to store and retrieve chat history.
"""

from typing import Dict, Any, List
from agno.memory import Memory
from datetime import datetime
import json
import os
import pickle

class AgentMemoryManager:
    """
    Class to manage memory for all agents in the system.
    Stores and retrieves conversation history.
    """
    
    def __init__(self, persistence_dir="./agent_memories"):
        """
        Initialize the memory manager with agent memories.
        
        Args:
            persistence_dir: Directory to store persisted memories
        """
        self.memories: Dict[str, Memory] = {}
        self.persistence_dir = persistence_dir
        
        # Create persistence directory if it doesn't exist
        if not os.path.exists(persistence_dir):
            os.makedirs(persistence_dir)
        
        # Load any existing memories
        self._load_memories()
    
    def _get_memory_path(self, agent_id: str) -> str:
        """Get the file path for an agent's memory."""
        return os.path.join(self.persistence_dir, f"{agent_id}_memory.pkl")
    
    def _load_memories(self) -> None:
        """Load all persisted memories from disk."""
        if os.path.exists(self.persistence_dir):
            for filename in os.listdir(self.persistence_dir):
                if filename.endswith("_memory.pkl"):
                    agent_id = filename.replace("_memory.pkl", "")
                    file_path = os.path.join(self.persistence_dir, filename)
                    try:
                        with open(file_path, 'rb') as f:
                            self.memories[agent_id] = pickle.load(f)
                    except (pickle.PickleError, EOFError, IOError) as e:
                        print(f"Error loading memory for {agent_id}: {e}")
                        # Create a new memory if loading fails
                        self.memories[agent_id] = Memory()
    
    def _save_memory(self, agent_id: str) -> None:
        """
        Save an agent's memory to disk.
        
        Args:
            agent_id: The unique identifier for the agent.
        """
        if agent_id in self.memories:
            try:
                with open(self._get_memory_path(agent_id), 'wb') as f:
                    pickle.dump(self.memories[agent_id], f)
            except (pickle.PickleError, IOError) as e:
                print(f"Error saving memory for {agent_id}: {e}")
    
    def get_memory(self, agent_id: str) -> Memory:
        """
        Get an agent's memory, creating it if it doesn't exist.
        
        Args:
            agent_id: The unique identifier for the agent.
            
        Returns:
            Memory: The agent's memory object.
        """
        if agent_id not in self.memories:
            self.memories[agent_id] = Memory()
        return self.memories[agent_id]
    
    def add_user_message(self, agent_id: str, message: str) -> None:
        """
        Add a user message to an agent's memory.
        
        Args:
            agent_id: The unique identifier for the agent.
            message: The user's message content.
        """
        memory = self.get_memory(agent_id)
        memory.add_user_message(message)
        self._save_memory(agent_id)
    
    def add_ai_message(self, agent_id: str, message: str) -> None:
        """
        Add an AI message to an agent's memory.
        
        Args:
            agent_id: The unique identifier for the agent.
            message: The AI's message content.
        """
        memory = self.get_memory(agent_id)
        memory.add_ai_message(message)
        self._save_memory(agent_id)
    
    def get_conversation_history(self, agent_id: str, max_messages: int = 10) -> str:
        """
        Get the conversation history for an agent.
        
        Args:
            agent_id: The unique identifier for the agent.
            max_messages: Maximum number of messages to include in history.
            
        Returns:
            str: Formatted conversation history.
        """
        memory = self.get_memory(agent_id)
        messages = memory.messages[-max_messages:] if len(memory.messages) > max_messages else memory.messages
        
        if not messages:
            return ""
        
        history = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            history.append(f"{role}: {msg.content}")
        
        return "\n\n".join(history)
    
    def clear_memory(self, agent_id: str) -> None:
        """
        Clear an agent's memory.
        
        Args:
            agent_id: The unique identifier for the agent.
        """
        if agent_id in self.memories:
            self.memories[agent_id] = Memory()
            self._save_memory(agent_id)
    
    def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get statistics about an agent's memory.
        
        Args:
            agent_id: The unique identifier for the agent.
            
        Returns:
            Dict: Memory statistics.
        """
        memory = self.get_memory(agent_id)
        return {
            "message_count": len(memory.messages),
            "user_messages": sum(1 for msg in memory.messages if msg.role == "user"),
            "ai_messages": sum(1 for msg in memory.messages if msg.role == "assistant"),
            "last_updated": datetime.now().isoformat()
        }

# Create a singleton instance of the memory manager
memory_manager = AgentMemoryManager()