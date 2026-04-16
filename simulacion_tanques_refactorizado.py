import json
import logging
from typing import Any, Dict, Union

# Configure logging
logging.basicConfig(level=logging.INFO)

class TankSimulator:
    """
    A class to simulate tank behavior in a battlefield environment.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the simulator with provided configuration.
        
        Parameters:
        - config: A dictionary containing configuration settings.
        """
        self.config = config
        self.tanks = []

    def load_config(self, filepath: str) -> None:
        """
        Load configuration settings from a JSON file.
        
        Parameters:
        - filepath: Path to the JSON config file.
        """
        try:
            with open(filepath, 'r') as file:
                self.config = json.load(file)
            logging.info("Configuration loaded successfully.")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")

    def save_config(self, filepath: str) -> None:
        """
        Save current configuration settings to a JSON file.
        
        Parameters:
        - filepath: Path to save the JSON config file.
        """
        try:
            with open(filepath, 'w') as file:
                json.dump(self.config, file, indent=4)
            logging.info("Configuration saved successfully.")
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")

    def add_tank(self, tank: Dict[str, Union[str, int]]) -> None:
        """
        Add a new tank to the simulation.
        
        Parameters:
        - tank: A dictionary representing the tank's properties.
        """
        self.tanks.append(tank)
        logging.info(f'Tank added: {tank}')

    def run_simulation(self) -> None:
        """
        Run the tank simulation.
        """
        logging.info("Simulation started.")
        # Simulation logic goes here

    def get_tank_status(self) -> None:
        """
        Print the status of all tanks.
        """
        for tank in self.tanks:
            logging.info(f'Tank status: {tank}')

# Example usage (commented out for production code):
# if __name__ == '__main__':
#     simulator = TankSimulator(config={}) 
#     simulator.load_config('path/to/config.json')
#     simulator.run_simulation()