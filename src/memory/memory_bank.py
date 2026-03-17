# src/memory/memory_bank.py

import json
import os
from typing import Dict, Any, Optional


class MemoryBank:
    """
    A comprehensive memory management system for the chess pairing application.
    Stores and manages application state, user preferences, and historical data.
    """

    def __init__(self, storage_path: str = "memory_bank.json"):
        """
        Initialize the MemoryBank with a storage path.
        
        Args:
            storage_path (str): Path to the JSON file where data will be stored.
        """
        self.storage_path = storage_path
        self.data: Dict[str, Any] = {
            "application_state": {},
            "user_preferences": {},
            "historical_data": {}
        }
        self.load()

    def load(self) -> None:
        """
        Load data from the storage file if it exists.
        """
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as file:
                self.data = json.load(file)

    def save(self) -> None:
        """
        Save the current data to the storage file.
        """
        with open(self.storage_path, "w") as file:
            json.dump(self.data, file, indent=4)

    def set_application_state(self, key: str, value: Any) -> None:
        """
        Set a value in the application state.
        
        Args:
            key (str): Key for the state value.
            value (Any): Value to store.
        """
        self.data["application_state"][key] = value
        self.save()

    def get_application_state(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the application state.
        
        Args:
            key (str): Key for the state value.
        
        Returns:
            Optional[Any]: The stored value or None if not found.
        """
        return self.data["application_state"].get(key)

    def set_user_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference.
        
        Args:
            key (str): Key for the preference.
            value (Any): Value to store.
        """
        self.data["user_preferences"][key] = value
        self.save()

    def get_user_preference(self, key: str) -> Optional[Any]:
        """
        Retrieve a user preference.
        
        Args:
            key (str): Key for the preference.
        
        Returns:
            Optional[Any]: The stored preference or None if not found.
        """
        return self.data["user_preferences"].get(key)

    def add_historical_data(self, key: str, value: Any) -> None:
        """
        Add historical data.
        
        Args:
            key (str): Key for the historical data.
            value (Any): Value to store.
        """
        self.data["historical_data"][key] = value
        self.save()

    def get_historical_data(self, key: str) -> Optional[Any]:
        """
        Retrieve historical data.
        
        Args:
            key (str): Key for the historical data.
        
        Returns:
            Optional[Any]: The stored historical data or None if not found.
        """
        return self.data["historical_data"].get(key)

    def clear_memory(self) -> None:
        """
        Clear all stored data.
        """
        self.data = {
            "application_state": {},
            "user_preferences": {},
            "historical_data": {}
        }
        self.save()