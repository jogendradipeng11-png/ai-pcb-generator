import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const generateBtn = document.getElementById('generateBtn');
const loader = document.getElementById('loader');
const results = document.getElementById('results');
let bomData = [];

generateBtn.onclick = async () => {
  const prompt = document.getElementById('prompt').value;
  if (!prompt) return alert("Enter a circuit description");

  loader.classList.remove('hidden');
  results.classList.add('hidden');

  const res = await fetch('/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({prompt})
  });

  const data = await res.json();
  loader.classList.add('hidden');

  if (data.error) return alert(data.error);

  // 1. Show Schematic
  document.getElementById('schCode').innerText = data.schematic;

  // 2. Show BOM
  bomData = data.bom_json;
  const table = document.getElementById('bomTable');
  table.innerHTML = '<tr><th>Ref</th><th>Value</th><th>Footprint</th><th>Qty</th></tr>';
  bomData.forEach(r => {
    table.innerHTML += `<tr><td>${r.Ref}</td><td>${r.Value}</td><td>${r.Footprint}</td><td>${r.Qty}</td></tr>`;
  });

  // 3. Show 3D
  show3D();

  results.classList.remove('hidden');
}

// Tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  }
});

// 3D Preview
function show3D() {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(75, document.getElementById('pcb3d').clientWidth/400, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer();
  renderer.setSize(document.getElementById('pcb3d').clientWidth, 400);
  document.getElementById('pcb3d').innerHTML = '';
  document.getElementById('pcb3d').appendChild(renderer.domElement);

  const geometry = new THREE.BoxGeometry(5, 3, 0.2);
  const material = new THREE.MeshStandardMaterial({color: 0x1a5c1a});
  const pcb = new THREE.Mesh(geometry, material);
  scene.add(pcb);

  const light = new THREE.DirectionalLight(0xffffff, 1);
  light.position.set(5,5,5);
  scene.add(light);

  camera.position.z = 5;
  new OrbitControls(camera, renderer.domElement);

  function animate() {
    requestAnimationFrame(animate);
    pcb.rotation.y += 0.01;
    renderer.render(scene, camera);
  }
  animate();
}

// Downloads
function downloadFile(filename, content) {
  const blob = new Blob([content], {type: 'text/plain'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}

function downloadCSV() {
  const csv = "Ref,Value,Footprint,Qty\n" + bomData.map(r => `${r.Ref},${r.Value},${r.Footprint},${r.Qty}`).join('\n');
  downloadFile('BOM.csv', csv);
}
