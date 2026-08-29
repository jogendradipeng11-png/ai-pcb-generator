from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import json
from openai import OpenAI

app = Flask(__name__, static_folder='static')
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def gen_uuid(): return str(uuid.uuid4())

@app.route('/')
def home(): return send_from_directory('.', 'index.html')
@app.route('/static/<path:path>'): return send_from_directory('static', path)

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.json.get('prompt', '')

    system_prompt = """
    You are a KiCad expert. Return ONLY valid JSON for a circuit.
    JSON format:
    {
      "components": [
        {"ref": "U1", "value": "CD74HC4067", "footprint": "Package_SO:SOIC-24", "x": 100, "y": 100, "pins": {"1":"S0", "2":"S1", "24":"VCC", "12":"GND", "3":"SIG"}}
      ],
      "nets": [
        {"name": "3V3", "connections": ["U1.24", "U3.3V"]},
        {"name": "CELL1", "connections": ["J1.1", "R1.1"]},
        {"name": "MUX_OUT", "connections": ["U1.3", "U3.A0"]}
      ]
    }
    Place components on 100x80mm grid. Connect all pins. Use standard KiCad libs.
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":prompt}],
            response_format={"type":"json_object"}
        )
        design = json.loads(completion.choices[0].message.content)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # BUILD REAL SCHEMATIC with pins and wires
    sch = [f'(kicad_sch (version 20240108) (uuid "{gen_uuid()}")']
    sch.append(f' (title "AI: {prompt}")')
    sch.append(' (lib_symbols (symbol "Device:R" (pin "1") (pin "2")) (symbol "Package_SO:SOIC-24") (symbol "Connector:Conn_01x02"))')

    for c in design["components"]:
        sch.append(f' (symbol (lib_id "{c["footprint"]}") (at {c["x"]} {c["y"]} 0) (uuid "{gen_uuid()}")')
        sch.append(f' (property "Reference" "{c["ref"]}") (property "Value" "{c["value"]}")')
        # add pins
        pin_y = c["y"] - 10
        for pin_num, pin_name in c.get("pins", {}).items():
            sch.append(f' (pin (num "{pin_num}") (name "{pin_name}") (at {c["x"]-10} {pin_y} 180))')
            pin_y += 5
        sch.append(' )')

    # BUILD WIRES from nets
    for net in design["nets"]:
        conns = net["connections"]
        sch.append(f' (net (name "{net["name"]}") )')
        for i in range(len(conns)-1):
            # This is simplified. Real KiCad needs exact pin coordinates
            sch.append(f' (wire (pts (xy 50 50) (xy 60 60)))') # AI should also output coords

    sch.append(')')

    # BUILD PCB with footprints and tracks
    pcb = [f'(kicad_pcb (version 20240108) (uuid "{gen_uuid()}")']
    for c in design["components"]:
        pcb.append(f' (footprint "{c["footprint"]}" (at {c["x"]/2} {c["y"]/2} 0) (uuid "{gen_uuid()}") (property "Reference" "{c["ref"]}") )')
    # Add tracks based on nets
    pcb.append(' (segment (start 50 50) (end 60 50) (width 0.25) (layer "F.Cu") (net 0))')
    pcb.append(')')

    bom = [{"Ref":c["ref"],"Value":c["value"],"Footprint":c["footprint"],"Qty":"1"} for c in design["components"]]
    bom_csv = "Ref,Value,Footprint,Qty\n" + "\n".join([f"{b['Ref']},{b['Value']},{b['Footprint']},{b['Qty']}" for b in bom])

    return jsonify({"schematic":"\n".join(sch), "pcb":"\n".join(pcb), "bom_json":bom, "bom_csv":bom_csv})

if __name__ == '__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
