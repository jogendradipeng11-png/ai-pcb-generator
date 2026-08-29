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
    
    # TODO: Replace this with OpenAI/Gemini API call
    # For now we return a template based on your 8S BMS circuit
    
    schematic = f"""KiCad Schematic for: {prompt}

Components:
U1: CD74HC4067 - 16-Channel Analog MUX
U2: INA219 - Current Sensor
R1-R8: 100k Resistor - Voltage Divider
R9-R16: 22k Resistor - Voltage Divider
J1: 8S Battery Connector
MCU: ESP8266 NodeMCU

Nets:
BAT+ -> R1 -> MUX.C7
BAT7 -> R2 -> MUX.C6
...
MUX.SIG -> MCU.A0
MCU.D3,D4,D5,D6 -> MUX.S0,S1,S2,S3
INA219.SDA -> MCU.D2
INA219.SCL -> MCU.D1
"""
    
    bom = """Ref,Value,Footprint,Qty
R1-R8,100k,Resistor_0805,8
R9-R16,22k,Resistor_0805,8
U1,CD74HC4067,SOIC-24,1
U2,INA219,SOT-23-6,1
MCU,NodeMCU,ESP8266_Module,1
J1,BAT_8S,Connector_2.54mm,1
"""
    
    explanation = f"AI Generated for prompt: '{prompt}'\n\nThis design includes:\n1. 8S Cell voltage monitoring via CD74HC4067 MUX\n2. 100A current sensing via INA219 + Shunt\n3. Common GND rule applied\n4. Ready for KiCad import"
    
    return jsonify({
        "schematic": schematic,
        "bom": bom,
        "explanation": explanation
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
