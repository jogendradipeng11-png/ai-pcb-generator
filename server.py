from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder='static')

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', 'No prompt')
    
    # 1. Real KiCad 8 Schematic format
    schematic = f"""(kicad_sch (version 20240108) (generator ai-pcb)
  (uuid "ai-pcb-gen")
  (title "AI Generated: {prompt}")
  (lib_symbols
    (symbol "Device:R" (pin_numbers hide) (pin_names hide))
    (symbol "Package_SO:SOIC-24" (pin_numbers hide) (pin_names hide))
  )
  (symbol (lib_id "Device:R") (at 50 50 0) (unit 1)
    (property "Reference" "R1" (at 50 60 0))
    (property "Value" "100k" (at 50 40 0))
  )
  (symbol (lib_id "Package_SO:SOIC-24") (at 100 50 0) (unit 1)
    (property "Reference" "U1" (at 100 70 0))
    (property "Value" "CD74HC4067" (at 100 30 0))
  )
  (wire (pts (xy 60 50) (xy 90 50)))
)
"""
    
    # 2. BOM
    bom_json = [
        {"Ref": "R1-R8", "Value": "100k", "Footprint": "Resistor_SMD:R_0805", "Qty": "8"},
        {"Ref": "U1", "Value": "CD74HC4067", "Footprint": "Package_SO:SOIC-24", "Qty": "1"},
        {"Ref": "U2", "Value": "INA219", "Footprint": "Package_TO_SOT_SMD:SOT-23-6", "Qty": "1"},
        {"Ref": "MCU", "Value": "NodeMCU", "Footprint": "Module:ESP8266_NodeMCU", "Qty": "1"},
    ]
    bom_csv = "Ref,Value,Footprint,Qty\n"
    for row in bom_json:
        bom_csv += f"{row['Ref']},{row['Value']},{row['Footprint']},{row['Qty']}\n"
    
    # 3. 3D Data for Three.js
    pcb_3d = [
        {"x": -30, "y": 0, "w": 10, "h": 5, "d": 3, "color": 0x38bdf8}, # R
        {"x": 0, "y": 0, "w": 15, "h": 8, "d": 4, "color": 0x0ea5e9}, # U1 MUX
        {"x": 25, "y": 5, "w": 10, "h": 5, "d": 3, "color": 0x0ea5e9}, # U2 INA
        {"x": 40, "y": 0, "w": 20, "h": 15, "d": 5, "color": 0x38bdf8}, # MCU
    ]
    
    return jsonify({
        "schematic": schematic,
        "bom_json": bom_json,
        "bom_csv": bom_csv,
        "pcb_3d": pcb_3d
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
