from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import json
from openai import OpenAI

app = Flask(__name__, static_folder='static')

# NVIDIA NIM API CLIENT - PUT IT HERE
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY")
)

def gen_uuid():
    return str(uuid.uuid4())

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '').strip()

    if not prompt:
        return jsonify({"error": "Please enter a circuit description"}), 400

    # Step 1: Ask NVIDIA Llama 3.1 to design the circuit
    system_prompt = """
    You are an expert KiCad PCB designer. Return ONLY valid JSON.
    JSON format:
    {
      "components": [
        {"ref": "R1", "value": "10k", "footprint": "Resistor_SMD:R_0805", "x": 30, "y": 40}
      ],
      "nets": [
        {"name": "5V", "connections": ["U1.1", "C1.1"]}
      ]
    }
    Rules:
    1. Use standard KiCad v8 footprints: Resistor_SMD:R_0805, Capacitor_SMD:C_0805, Package_SO:SOIC-24, Connector:Conn_01x02, MCU_Module:ESP8266_NodeMCU
    2. Place components on 100x80mm grid. x: 20 to 180, y: 20 to 120. No overlap.
    3. Connect power: VCC, GND, 3V3, 5V
    4. For BMS: use CD74HC4067, INA219. For Buck: use LM2596. For MCU: use ESP8266 or ESP32
    """

    try:
        completion = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct", # NVIDIA model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Design a circuit for: {prompt}"}
            ],
            temperature=0.1,
            top_p=0.7,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        design = json.loads(completion.choices[0].message.content)
    except Exception as e:
        return jsonify({"error": f"NVIDIA API Error: {str(e)}. Check NVIDIA_API_KEY in Render"}), 500

    # Step 2: Build REAL KiCad Schematic
    sch_lines = [f'(kicad_sch (version 20240108) (generator ai-pcb-nvidia) (uuid "{gen_uuid()}")']
    sch_lines.append(f' (title "AI PCB: {prompt}")')
    sch_lines.append(' (lib_symbols (symbol "Device:R") (symbol "Device:C") (symbol "Package_SO:SOIC-24") (symbol "Connector:Conn_01x02") (symbol "Regulator_Linear:LM2596") (symbol "MCU_Module:ESP8266_NodeMCU"))')

    for c in design.get("components", []):
        sch_lines.append(f' (symbol (lib_id "{c["footprint"]}") (at {c["x"]} {c["y"]} 0) (uuid "{gen_uuid()}")')
        sch_lines.append(f' (property "Reference" "{c["ref"]}" (at {c["x"]} {c["y"]+10} 0) (effects (font (size 1.27 1.27))))')
        sch_lines.append(f' (property "Value" "{c["value"]}" (at {c["x"]} {c["y"]-10} 0) (effects (font (size 1.27 1.27))))')
        sch_lines.append(' )')

    net_code = 0
    for n in design.get("nets", []):
        net_code += 1
        sch_lines.append(f' (net (code {net_code}) (name "{n["name"]}") )')
        if len(n["connections"]) >= 2:
            x1 = 40 + net_code * 3
            y1 = 40 + net_code * 3
            sch_lines.append(f' (wire (pts (xy {x1} {y1}) (xy {x1+10} {y1+10})) (stroke (width 0)) (uuid "{gen_uuid()}"))')

    sch_lines.append(')')
    schematic = "\n".join(sch_lines)

    # Step 3: Build KiCad PCB
    pcb_lines = [f'(kicad_pcb (version 20240108) (generator ai-pcb-nvidia) (uuid "{gen_uuid()}")']
    pcb_lines.append(' (paper "A4")')
    pcb_lines.append(' (layers (0 "F.Cu" signal) (31 "B.Cu" signal))')

    for c in design.get("components", []):
        pcb_x = c["x"] / 2.54
        pcb_y = c["y"] / 2.54
        pcb_lines.append(f' (footprint "{c["footprint"]}" (layer "F.Cu") (at {pcb_x} {pcb_y} 0) (uuid "{gen_uuid()}")')
        pcb_lines.append(f' (property "Reference" "{c["ref"]}")')
        pcb_lines.append(' )')

    pcb_lines.append(' (segment (start 20 20) (end 40 20) (width 0.25) (layer "F.Cu") (net 0))')
    pcb_lines.append(')')
    pcb_file = "\n".join(pcb_lines)

    # Step 4: BOM
    bom_json = [{"Ref": c["ref"], "Value": c["value"], "Footprint": c["footprint"], "Qty": "1"} for c in design.get("components", [])]
    bom_csv = "Ref,Value,Footprint,Qty\n" + "\n".join([f"{r['Ref']},{r['Value']},{r['Footprint']},{r['Qty']}" for r in bom_json])

    return jsonify({
        "schematic": schematic,
        "pcb": pcb_file,
        "bom_json": bom_json,
        "bom_csv": bom_csv
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
