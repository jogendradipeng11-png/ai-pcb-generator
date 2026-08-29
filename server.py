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
    prompt = data.get('prompt', '')
    
    # 1. SVG Schematic Preview - basic block diagram
    schematic_svg = """
    <svg width="700" height="300" style="background:#1e293b; border-radius:8px;">
      <rect x="20" y="50" width="120" height="60" fill="#38bdf8" rx="5"/>
      <text x="80" y="85" fill="black" text-anchor="middle">8S Battery</text>
      
      <rect x="200" y="40" width="140" height="80" fill="#0ea5e9" rx="5"/>
      <text x="270" y="75" fill="black" text-anchor="middle">CD74HC4067</text>
      <text x="270" y="95" fill="black" text-anchor="middle">MUX</text>
      
      <rect x="400" y="100" width="120" height="60" fill="#0ea5e9" rx="5"/>
      <text x="460" y="135" fill="black" text-anchor="middle">INA219</text>
      
      <rect x="580" y="80" width="100" height="100" fill="#38bdf8" rx="5"/>
      <text x="630" y="130" fill="black" text-anchor="middle">ESP8266</text>
      
      <line x1="140" y1="80" x2="200" y2="80" stroke="white" stroke-width="2"/>
      <line x1="340" y1="80" x2="400" y2="130" stroke="white" stroke-width="2"/>
      <line x1="520" y1="130" x2="580" y2="130" stroke="white" stroke-width="2"/>
    </svg>
    """
    
    # 2. BOM as JSON for table + CSV for download
    bom_json = [
        {"Ref": "R1-R8", "Value": "100k", "Footprint": "Resistor_0805", "Qty": 8},
        {"Ref": "R9-R16", "Value": "22k", "Footprint": "Resistor_0805", "Qty": 8},
        {"Ref": "U1", "Value": "CD74HC4067", "Footprint": "SOIC-24", "Qty": 1},
        {"Ref": "U2", "Value": "INA219", "Footprint": "SOT-23-6", "Qty": 1},
        {"Ref": "MCU", "Value": "NodeMCU", "Footprint": "ESP8266_Module", "Qty": 1},
    ]
    bom_csv = "Ref,Value,Footprint,Qty\n" + "\n".join([",".join(row.values()) for row in bom_json])
    
    # 3. KiCad schematic text for download
    schematic = f"""EESchema Schematic
# For prompt: {prompt}
$Comp
L Resistor R1
U 1 1 5F3A1B2C
P 2000 2000
F 0 "R1" H 2000 2300 50 0000 C CNN
F 1 "100k" H 2000 1700 50 0000 C CNN
$EndComp
# ... more components
"""
    
    explanation = f"AI Generated for: '{prompt}'\n\nThis 8S BMS uses CD74HC4067 to multiplex 8 cell voltages into ESP8266 ADC. INA219 measures pack current. All cells share common GND."
    
    return jsonify({
        "schematic_svg": schematic_svg,
        "bom_json": bom_json,
        "bom_csv": bom_csv,
        "schematic": schematic,
        "explanation": explanation
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
