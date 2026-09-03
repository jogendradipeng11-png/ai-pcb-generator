import { Circuit } from "@tscircuit/core"

export default function CircuitBoard() {
  return (
    <board width="20mm" height="15mm">
      <resistor name="R1" resistance="10k" footprint="0402" pcbX={-4} pcbY={0} />
      <led name="LED1" footprint="0603" pcbX={4} pcbY={0} />
      <trace from="R1.pin1" to="net.VCC" />
      <trace from="R1.pin2" to="LED1.pin1" />
      <trace from="LED1.pin2" to="net.GND" />
    </board>
  )
}
