from flask import Flask, request, jsonify, send_from_directory
import os, json, subprocess, base64
from openai import OpenAI

app = Flask(__name__, static_folder='.')

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

def write_circuit_tsx(description):
    # Ask Groq to generate tscircuit code
    system = """You are a tscircuit expert. Return ONLY valid TSX code for index.circuit.tsx.
    Use <board>, <connector standard="usb_c">, <chip>, <capacitor>, <resistor>, <led>.
    For USB-C use: footprint="usb_c_receptacle_usb2_type_c" and pins A4,B9=VBUS, A1,B12=GND, A5=CC1, B5=CC2 with 5.1k pulldowns.
    Export default function Circuit() { return <board>...</board> }"""

    resp = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role":"system","content":system},{"role":"user","content":f"Design: {description}"}],
        response_format={"type":"json_object"} # We'll parse TSX from JSON
    )
    tsx_code = json.loads(resp.choices[0].message.content)["tsx"]

    with open("cb/project/index.circuit.tsx", "w") as f:
        f.write(tsx_code)

@app.route('/')
def home(): return send_from_directory('.', 'index.html')

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.json['prompt']

    # 1. Generate TSX with Groq
    write_circuit_tsx(prompt)

    # 2. Build with tscircuit CLI
    subprocess.run(["npx", "tsci", "build", "--schematic-png", "--pcb-png"], cwd="cb/project", check=True)

    # 3. Read PNGs and return base64
    with open("cb/project/dist/index/schematic.png", "rb") as f: sch = base64.b64encode(f.read()).decode()
    with open("cb/project/dist/index/pcb.png", "rb") as f: pcb = base64.b64encode(f.read()).decode()

    # 4. Dummy BOM for now
    bom_csv = "Ref,Value\nU1,AMS1117-3.3\nC1,10uF"

    return jsonify({"schematic_png": sch, "pcb_png": pcb, "bom_csv": bom_csv})

if __name__ == '__main__': app.run(host='0.0.0.0', port=5000)
