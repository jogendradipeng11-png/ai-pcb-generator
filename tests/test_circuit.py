import unittest

from server import simulate_connectivity, write_circuit_tsx


class CircuitConnectivityTest(unittest.TestCase):
    def test_simple_led_request_generates_a_connected_circuit(self):
        result = simulate_connectivity(write_circuit_tsx("simple 3.3V LED drive circuit"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["components"], 2)
        self.assertEqual(result["traces"], 3)

    def test_placed_components_are_connected(self):
        tsx = """
        <board width="10mm" height="10mm">
          <resistor name="R1" resistance="10k" footprint="0402" pcbX="-2" pcbY="0" />
          <led name="LED1" footprint="0603" pcbX="2" pcbY="0" />
          <trace from="R1.pin1" to="net.VCC" />
          <trace from="R1.pin2" to="LED1.pin1" />
          <trace from="LED1.pin2" to="net.GND" />
        </board>
        """
        result = simulate_connectivity(tsx)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["components"], 2)
        self.assertEqual(result["traces"], 3)

    def test_unconnected_component_fails(self):
        tsx = """
        <board width="10mm" height="10mm">
          <resistor name="R1" resistance="10k" footprint="0402" pcbX="-2" pcbY="0" />
          <led name="LED1" footprint="0603" pcbX="2" pcbY="0" />
          <trace from="R1.pin1" to="net.VCC" />
        </board>
        """
        result = simulate_connectivity(tsx)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("Component has no connected trace: LED1", result["errors"])


if __name__ == "__main__":
    unittest.main()
