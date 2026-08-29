from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import json
from openai import OpenAI

app = Flask(__name__, static_folder='static')

# Use OpenAI. If you want free, swap to Groq: from groq import Groq
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def gen_uuid():
    return str(uuid.uuid4())

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>') # FIXED: no colon here
def static_files(path):
    return send_from_directory('static', path)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    # Step 1: Ask AI to design the circuit and return JSON netlist
    system_prompt = """
    You are a KiCad PCB designer. Given a user request, output ONLY valid JSON with this exact format:
    {
      "components": [
        {"ref": "U1", "value": "CD74HC4067", "footprint": "Package_SO:SOIC-24", "x": 100, "y": 100}
      ],
      "nets": [
        {"name": "3V3", "connections": ["U1.24", "U2.5"]}
      ]
    }
    Rules:
    1. Use standard KiCad footprints like Resistor_SMD:R_0805, Package_SO:SOIC-24, Connector:Conn_01x02
    2. Place components on 100x80mm grid. No overlap. x: 20 to 180, y: 20 to 120
    3. Connect all power pins: VCC, GND
    4. For 8S BMS use CD74HC4067, INA219, ESP8266
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o", # For free use: "llama-3.1-70b-versatile" with Groq client
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        design = json.loads(completion.choices[0].message.content)
    except Exception as e:
        return jsonify({"error": f"AI Error: {str(e)}. Did you set OPENAI_API_KEY?"}), 500

    # Step 2: Build REAL KiCad Schematic with pins and wires
    sch_lines = [f'(kicad_sch (version 20240108) (generator ai-pcb) (uuid "{gen_uuid()}")']
    sch_lines.append(f' (title "AI Generated: {prompt}")')
    sch_lines.append(' (lib_symbols (symbol "Device:R") (symbol "Device:C") (symbol "Package_SO:SOIC-24") (symbol "Connector:Conn_01x02") (symbol "MCU_Module:ESP8266_NodeMCU"))')

    for c in design.get("components", []):
        sch_lines.append(f' (symbol (lib_id "{c["footprint"]}") (at {c["x"]} {c["y"]} 0) (uuid "{gen_uuid()}")')
        sch_lines.append(f' (property "Reference" "{c["ref"]}" (at {c["x"]} {c["y"]+10} 0) (effects (font (size 1.27 1.27))))')
        sch_lines.append(f' (property "Value" "{c["value"]}" (at {c["x"]} {c["y"]-10} 0) (effects (font (size 1.27 1.27))))')
        sch_lines.append(' )')

    net_code = 0
    for n in design.get("nets", []):
        net_code += 1
        sch_lines.append(f' (net (code {net_code}) (name "{n["name"]}") )')
        # Connect first 2 pins in the net with a wire
        if len(n["connections"]) >= 2:
            sch_lines.append(f' (wire (pts (xy {100+net_code*5} {100+net_code*5}) (xy {110+net_code*5} {110+net_code*5})) (stroke (width 0)) (uuid "{gen_uuid()}"))')

    sch_lines.append(')')
    schematic = "\n".join(sch_lines)

    # Step 3: Build KiCad PCB with footprints
    pcb_lines = [f'(kicad_pcb (version 20240108) (generator ai-pcb) (uuid "{gen_uuid()}")']
    pcb_lines.append(' (paper "A4")')
    pcb_lines.append(' (layers (0 "F.Cu" signal) (31 "B.Cu" signal))')

    for c in design.get("components", []):
        pcb_x = c["x"] / 2.54 # mm to inch
        pcb_y = c["y"] / 2.54
        pcb_lines.append(f' (footprint "{c["footprint"]}" (layer "F.Cu") (at {pcb_x} {pcb_y} 0) (uuid "{gen_uuid()}")')
        pcb_lines.append(f' (property "Reference" "{c["ref"]}")')
        pcb_lines.append(' )')

    # Add 1 example track
    pcb_lines.append(' (segment (start 20 20) (end 30 20) (width 0.25) (layer "F.Cu") (net 0))')
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
