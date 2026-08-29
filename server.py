from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import json
from openai import OpenAI

app = Flask(__name__, static_folder='static')
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

def gen_uuid():
    return str(uuid.uuid4())

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')

    # Step 1: Ask GPT-4o to design the circuit and return JSON netlist
    system_prompt = """
    You are a KiCad PCB designer. Given a user request, output a JSON with:
    1. "components": list of {ref, value, footprint, x, y}
    2. "nets": list of {name, connections: [ref.pin, ref.pin]}
    3. "tracks": list of {net, start: [x,y], end: [x,y], width}
    Use standard KiCad footprints. Keep board size 100x80mm. Place components without overlap.
    Example for buck converter: components with LM2596, Inductor, Caps. nets with VIN, VOUT, GND.
    Return ONLY valid JSON.
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        design = json.loads(completion.choices[0].message.content)
    except Exception as e:
        return jsonify({"error": f"OpenAI Error: {str(e)}"}), 500

    # Step 2: Convert JSON to KiCad.kicad_sch
    sch_lines = [f'(kicad_sch (version 20240108) (generator ai-pcb) (uuid "{gen_uuid()}")']
    sch_lines.append(f' (title "AI Generated: {prompt}")')
    sch_lines.append(' (lib_symbols (symbol "Device:R") (symbol "Device:C") (symbol "Package_SO:SOIC-8"))')

    for c in design.get("components", []):
        sch_lines.append(f' (symbol (lib_id "Device:R") (at {c["x"]} {c["y"]} 0) (uuid "{gen_uuid()}")')
        sch_lines.append(f' (property "Reference" "{c["ref"]}")')
        sch_lines.append(f' (property "Value" "{c["value"]}")')
        sch_lines.append(' )')

    for n in design.get("nets", []):
        sch_lines.append(f' (net (name "{n["name"]}") )')

    sch_lines.append(')')
    schematic = "\n".join(sch_lines)

    # Step 3: Convert JSON to KiCad.kicad_pcb with tracks = "autorouted"
    pcb_lines = [f'(kicad_pcb (version 20240108) (generator ai-pcb) (uuid "{gen_uuid()}")']
    pcb_lines.append(' (paper "A4")')

    for c in design.get("components", []):
        pcb_lines.append(f' (footprint "{c["footprint"]}" (at {c["x"]} {c["y"]} 0) (uuid "{gen_uuid()}")')
        pcb_lines.append(f' (property "Reference" "{c["ref"]}")')
        pcb_lines.append(' )')

    for t in design.get("tracks", []):
        pcb_lines.append(f' (segment (start {t["start"][0]} {t["start"][1]}) (end {t["end"][0]} {t["end"][1]}) (width {t["width"]}) (layer "F.Cu") (net {t["net"]}))')

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
