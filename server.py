from flask import Flask, request, jsonify, send_from_directory
import os
import uuid

app = Flask(__name__, static_folder='static')

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
    prompt = data.get('prompt', '8S BMS')
    
    # 1. FULL KICAD SCHEMATIC with nets for 8S
    sch_lines = [f'(kicad_sch (version 20240108) (generator ai-pcb) (uuid "{gen_uuid()}")']
    sch_lines.append(f'  (title "AI Generated: {prompt}")')
    
    # Symbols
    sch_lines.append('  (lib_symbols')
    sch_lines.append('    (symbol "Device:R")')
    sch_lines.append('    (symbol "Connector:Conn_01x02")')
    sch_lines.append('    (symbol "Amplifier_Current:INA219")')
    sch_lines.append('    (symbol "Logic:CD74HC4067")')
    sch_lines.append('    (symbol "MCU_Module:ESP8266_NodeMCU")')
    sch_lines.append('  )')
    
    y = 50
    # 8S Battery cells + voltage dividers
    for i in range(8):
        sch_lines.append(f'  (symbol (lib_id "Connector:Conn_01x02") (at 20 {y} 0) (unit 1) (uuid "{gen_uuid()}")')
        sch_lines.append(f'    (property "Reference" "J{i+1}" (at 20 {y+10} 0))')
        sch_lines.append(f'    (property "Value" "BAT{i}" (at 20 {y-10} 0))')
        sch_lines.append('  )')
        
        sch_lines.append(f'  (symbol (lib_id "Device:R") (at 50 {y} 0) (unit 1) (uuid "{gen_uuid()}")')
        sch_lines.append(f'    (property "Reference" "R{i+1}a" (at 50 {y+10} 0))')
        sch_lines.append(f'    (property "Value" "100k" (at 50 {y-10} 0))')
        sch_lines.append('  )')
        sch_lines.append(f'  (symbol (lib_id "Device:R") (at 70 {y} 0) (unit 1) (uuid "{gen_uuid()}")')
        sch_lines.append(f'    (property "Reference" "R{i+1}b" (at 70 {y+10} 0))')
        sch_lines.append(f'    (property "Value" "22k" (at 70 {y-10} 0))')
        sch_lines.append('  )')
        
        # Net from battery to divider to MUX pin
        sch_lines.append(f'  (wire (pts (xy 25 {y}) (xy 45 {y})))') # J to R1a
        sch_lines.append(f'  (wire (pts (xy 55 {y}) (xy 65 {y})))') # R1a to R1b
        sch_lines.append(f'  (wire (pts (xy 75 {y}) (xy 120 {y+ i*10})))') # R1b to MUX
        sch_lines.append(f'  (net (code {i+1}) (name "CELL_{i}") )')
        y += 20
    
    # MUX
    sch_lines.append(f'  (symbol (lib_id "Logic:CD74HC4067") (at 120 120 0) (unit 1) (uuid "{gen_uuid()}")')
    sch_lines.append(f'    (property "Reference" "U1" (at 120 150 0))')
    sch_lines.append(f'    (property "Value" "CD74HC4067" (at 120 100 0))')
    sch_lines.append('  )')
    
    # INA219
    sch_lines.append(f'  (symbol (lib_id "Amplifier_Current:INA219") (at 200 120 0) (unit 1) (uuid "{gen_uuid()}")')
    sch_lines.append(f'    (property "Reference" "U2" (at 200 150 0))')
    sch_lines.append(f'    (property "Value" "INA219" (at 200 100 0))')
    sch_lines.append('  )')
    
    # ESP8266
    sch_lines.append(f'  (symbol (lib_id "MCU_Module:ESP8266_NodeMCU") (at 280 120 0) (unit 1) (uuid "{gen_uuid()}")')
    sch_lines.append(f'    (property "Reference" "U3" (at 280 170 0))')
    sch_lines.append(f'    (property "Value" "NodeMCU" (at 280 90 0))')
    sch_lines.append('  )')
    
    # MUX SIG to ESP A0, S0-S3 to D pins, I2C
    sch_lines.append(f'  (wire (pts (xy 135 130) (xy 275 110)))') # MUX SIG -> A0
    sch_lines.append(f'  (wire (pts (xy 135 140) (xy 275 120)))') # S0 -> D3
    sch_lines.append(f'  (wire (pts (xy 210 130) (xy 275 130)))') # SDA
    sch_lines.append(f'  (wire (pts (xy 210 140) (xy 275 140)))') # SCL
    
    sch_lines.append(')')
    schematic = "\n".join(sch_lines)
    
    # 2. BASIC KICAD PCB with footprints + tracks for routing
    pcb_lines = [f'(kicad_pcb (version 20240108) (generator ai-pcb) (uuid "{gen_uuid()}")']
    pcb_lines.append('  (paper "A4")')
    
    x = 20
    for i in range(8):
        pcb_lines.append(f'  (footprint "Resistor_SMD:R_0805" (at {x} 50 0) (uuid "{gen_uuid()}")')
        pcb_lines.append(f'    (property "Reference" "R{i+1}a")')
        pcb_lines.append('    (pad "1" smd rect (at -1 0) (size 1 1.2) (layers "F.Cu"))')
        pcb_lines.append('    (pad "2" smd rect (at 1 0) (size 1 1.2) (layers "F.Cu"))')
        pcb_lines.append('  )')
        x += 8
    
    pcb_lines.append(f'  (footprint "Package_SO:SOIC-24" (at 100 50 0) (uuid "{gen_uuid()}")')
    pcb_lines.append(f'    (property "Reference" "U1")')
    pcb_lines.append('  )')
    
    # Example tracks connecting R1a to R1b to U1
    pcb_lines.append('  (segment (start 22 50) (end 28 50) (width 0.25) (layer "F.Cu"))')
    pcb_lines.append('  (segment (start 30 50) (end 36 50) (width 0.25) (layer "F.Cu"))')
    pcb_lines.append('  (segment (start 38 50) (end 100 50) (width 0.25) (layer "F.Cu"))')
    
    pcb_lines.append(')')
    pcb_file = "\n".join(pcb_lines)
    
    # 3. BOM
    bom_json = [{"Ref": f"R{i+1}a,R{i+1}b", "Value": "100k/22k", "Footprint": "Resistor_SMD:R_0805", "Qty": "8"} for i in range(8)]
    bom_json += [
        {"Ref": "U1", "Value": "CD74HC4067", "Footprint": "Package_SO:SOIC-24", "Qty": "1"},
        {"Ref": "U2", "Value": "INA219", "Footprint": "Package_TO_SOT_SMD:SOT-23-6", "Qty": "1"},
        {"Ref": "U3", "Value": "NodeMCU", "Footprint": "Module:ESP8266_NodeMCU", "Qty": "1"},
    ]
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
