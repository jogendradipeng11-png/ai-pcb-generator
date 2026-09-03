from flask import Flask, request, jsonify, redirect, send_from_directory
import os, json, subprocess, base64
import re
from openai import OpenAI

app = Flask(__name__, static_folder='.')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "cb", "project")

client = None

def get_client():
    global client
    if client is None:
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not configured")
        client = OpenAI(
            api_key=api_key,
            base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        )
    return client

def write_circuit_tsx(description, validation_errors=None):
    # Ask the configured OpenAI-compatible provider to generate tscircuit code
    system = """You generate valid tscircuit TSX for index.circuit.tsx. Return only the TSX source code.
The TSX must export a default function returning one <board> with width and height in mm.
Place every component inside that board using pcbX and pcbY so footprints do not overlap.
Use realistic components from: <connector>, <chip>, <capacitor>, <resistor>, <led>.
Represent every electrical connection explicitly with <trace from="..." to="..." />.
Use named nets such as net.VCC, net.GND, net.VBUS, and net.SIGNAL for shared connections.
Connect every component pin to another pin or named net. Never leave functional pins floating.
Keep the design compact and autoroutable on a two-layer board. Do not use markdown fences or comments.
For USB-C use footprint="usb_c_receptacle_usb2_type_c", pins A4/B9=VBUS, A1/B12=GND,
A5=CC1 and B5=CC2, with 5.1k pulldowns to GND. Include a schematic-ready logical netlist."""

    correction = ""
    if validation_errors:
        correction = "\nPrevious output failed validation. Correct these errors: " + "; ".join(validation_errors)
        correction += "\nReturn a complete replacement with literal <trace from=\"...\" to=\"...\" /> elements."
    resp = get_client().chat.completions.create(
        model=os.environ.get("NVIDIA_MODEL", "openai/gpt-oss-20b"),
        messages=[{"role":"system","content":system},{"role":"user","content":f"Design: {description}{correction}"}],
    )
    content = (resp.choices[0].message.content or "").strip()
    try:
        response = json.loads(content)
        tsx_code = response.get("tsx", "") if isinstance(response, dict) else content
    except json.JSONDecodeError:
        tsx_code = content
    tsx_code = tsx_code.strip()
    if tsx_code.startswith("```"):
        tsx_code = re.sub(r"^```(?:tsx|typescript)?\s*|\s*```$", "", tsx_code).strip()
    with open(os.path.join(PROJECT_DIR, "index.circuit.tsx"), "w") as f:
        f.write(tsx_code)
    return tsx_code

def simulate_connectivity(tsx_code):
    """Run a deterministic netlist simulation before invoking the PCB builder."""
    components = re.findall(r"<(?:connector|chip|capacitor|resistor|led)\s+name=[\"']([^\"']+)", tsx_code)
    traces = re.findall(r"<trace\s+from=[\"']([^\"']+)[\"']\s+to=[\"']([^\"']+)[\"']\s*/?>", tsx_code)
    errors = []
    if "<board" not in tsx_code:
        errors.append("No board was declared")
    if not components:
        errors.append("No placed components were declared")
    if not traces:
        errors.append("No electrical traces were declared")

    connected_components = set()
    for source, target in traces:
        for endpoint in (source, target):
            if endpoint.startswith("net."):
                continue
            component_name = endpoint.split(".", 1)[0]
            if component_name not in components:
                errors.append(f"Trace endpoint references unknown component: {component_name}")
            else:
                connected_components.add(component_name)
    missing = sorted(set(components) - connected_components)
    errors.extend(f"Component has no connected trace: {name}" for name in missing)
    return {
        "status": "PASS" if not errors else "FAIL",
        "simulator": "connectivity",
        "components": len(components),
        "traces": len(traces),
        "errors": errors,
    }

@app.route('/')
def home(): return send_from_directory('.', 'index.html')

@app.route('/generate', methods=['GET'])
def generate_method_error():
    return redirect('/')

@app.route('/health')
def health():
    return jsonify({"status": "ok", "provider": "nvidia"})

@app.route('/generate', methods=['POST'])
def generate():
    payload = request.get_json(silent=True) or {}
    prompt = payload.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "A circuit description is required."}), 400

    try:
        # 1. Generate and validate TSX with Groq. Retry so a malformed model
        # response is corrected before the PCB builder is invoked.
        circuit_test = None
        tsx_code = None
        for attempt in range(3):
            tsx_code = write_circuit_tsx(
                prompt.strip(),
                circuit_test["errors"] if circuit_test else None,
            )
            circuit_test = simulate_connectivity(tsx_code)
            if circuit_test["status"] == "PASS":
                break
        if circuit_test["status"] == "FAIL":
            return jsonify({"error": "Circuit connectivity test failed.", "circuit_test": circuit_test}), 422

        # 2. Build with tscircuit CLI
        cli_path = os.path.join(BASE_DIR, "node_modules", "tscircuit", "cli.mjs")
        try:
            build = subprocess.run(
                ["npx", "tsx", cli_path, "build", "--schematic-png", "--pcb-png"],
                cwd=PROJECT_DIR,
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except FileNotFoundError as error:
            raise RuntimeError("Node.js/npm is unavailable. Deploy this app with the Docker runtime.") from error
        if build.returncode != 0:
            details = (build.stderr or build.stdout or "tscircuit build failed").strip()
            raise RuntimeError(f"tscircuit build failed: {details[-1200:]}")

        # 3. Read PNGs and return base64
        with open(os.path.join(PROJECT_DIR, "dist", "index", "schematic.png"), "rb") as f:
            sch = base64.b64encode(f.read()).decode()
        with open(os.path.join(PROJECT_DIR, "dist", "index", "pcb.png"), "rb") as f:
            pcb = base64.b64encode(f.read()).decode()
    except Exception as error:
        app.logger.exception("PCB generation failed")
        if error.__class__.__name__ in {"BadRequestError", "AuthenticationError", "APIError"}:
            return jsonify({"error": f"AI generation failed: {error}"}), 502
        return jsonify({"error": str(error)}), 503 if "Node.js/npm" in str(error) else 500

    # 4. Dummy BOM for now
    bom_csv = "Ref,Value\nU1,AMS1117-3.3\nC1,10uF"
    return jsonify({"schematic_png": sch, "pcb_png": pcb, "bom_csv": bom_csv, "circuit_test": circuit_test})

if __name__ == '__main__': app.run(host='0.0.0.0', port=5000)
