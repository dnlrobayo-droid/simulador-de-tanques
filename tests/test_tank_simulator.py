import unittest
from tank_simulator import Tank, Simulation

class TestTankSimulation(unittest.TestCase):

    def setUp(self):
        self.tank = Tank("TestTank")
        self.simulation = Simulation()

    def test_tank_initialization(self):
        self.assertEqual(self.tank.name, "TestTank")
        self.assertEqual(self.tank.health, 100)
        self.assertEqual(self.tank.ammo, 10)

    def test_tank_movement(self):
        initial_position = self.tank.position
        self.tank.move(10, 0)  # move 10 units on the x-axis
        self.assertNotEqual(initial_position, self.tank.position)

    def test_tank_fire(self):
        initial_ammo = self.tank.ammo
        self.tank.fire()
        self.assertEqual(self.tank.ammo, initial_ammo - 1)

    def test_tank_health(self):
        self.tank.take_damage(20)
        self.assertEqual(self.tank.health, 80)

    def test_simulation_run(self):
        self.simulation.add_tank(self.tank)
        outcome = self.simulation.run()
        self.assertIsInstance(outcome, dict)  # Assuming the outcome is a dictionary

if __name__ == "__main__":
    unittest.main()