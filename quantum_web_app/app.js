const canvas = document.querySelector("#labCanvas");
const ctx = canvas.getContext("2d");
const API_BASE = (window.QUANTUM_API_BASE || localStorage.getItem("quantumApiBase") || "").replace(/\/$/, "");

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

const els = {
  backendStatus: document.querySelector("#backendStatus"),
  apiMetric: document.querySelector("#apiMetric"),
  modeSummary: document.querySelector("#modeSummary"),
  modeTitle: document.querySelector("#modeTitle"),
  modeText: document.querySelector("#modeText"),
  hitCount: document.querySelector("#hitCount"),
  modeMetric: document.querySelector("#modeMetric"),
  countLabel: document.querySelector("#countLabel"),
  playPause: document.querySelector("#playPause"),
  reset: document.querySelector("#reset"),
  fire: document.querySelector("#fire"),
  explain: document.querySelector("#explain"),
  exampleProblem: document.querySelector("#exampleProblem"),
  generateVisual: document.querySelector("#generateVisual"),
  aiText: document.querySelector("#aiText"),
  explainModal: document.querySelector("#explainModal"),
  closeModal: document.querySelector("#closeModal"),
  modalTitle: document.querySelector("#modalTitle"),
  modalSource: document.querySelector("#modalSource"),
  modalText: document.querySelector("#modalText"),
  chatForm: document.querySelector("#chatForm"),
  chatInput: document.querySelector("#chatInput"),
  attachPhoto: document.querySelector("#attachPhoto"),
  photoInput: document.querySelector("#photoInput"),
  photoPreview: document.querySelector("#photoPreview"),
  removePhoto: document.querySelector("#removePhoto"),
  chatSend: document.querySelector("#chatSend"),
  chatMessages: document.querySelector("#chatMessages"),
  chatSource: document.querySelector("#chatSource"),
  accountName: document.querySelector("#accountName"),
  loginNav: document.querySelector("#loginNav"),
  logoutNav: document.querySelector("#logoutNav"),
  authForm: document.querySelector("#authForm"),
  authName: document.querySelector("#authName"),
  authEmail: document.querySelector("#authEmail"),
  authPassword: document.querySelector("#authPassword"),
  loginSubmit: document.querySelector("#loginSubmit"),
  signupSubmit: document.querySelector("#signupSubmit"),
  authMessage: document.querySelector("#authMessage"),
  settingsForm: document.querySelector("#settingsForm"),
  settingsHint: document.querySelector("#settingsHint"),
  settingParticles: document.querySelector("#settingParticles"),
  settingWave: document.querySelector("#settingWave"),
  settingTheme: document.querySelector("#settingTheme"),
  settingApiBase: document.querySelector("#settingApiBase"),
  settingsMessage: document.querySelector("#settingsMessage"),
  planMessage: document.querySelector("#planMessage"),
  showParticles: document.querySelector("#showParticles"),
  showWave: document.querySelector("#showWave"),
  whichPath: document.querySelector("#whichPath"),
  slitSeparation: document.querySelector("#slitSeparation"),
  slitSeparationValue: document.querySelector("#slitSeparationValue"),
  wavelength: document.querySelector("#wavelength"),
  wavelengthValue: document.querySelector("#wavelengthValue"),
  slitWidth: document.querySelector("#slitWidth"),
  slitWidthValue: document.querySelector("#slitWidthValue"),
  particleRate: document.querySelector("#particleRate"),
  particleRateValue: document.querySelector("#particleRateValue"),
  barrierHeight: document.querySelector("#barrierHeight"),
  barrierHeightValue: document.querySelector("#barrierHeightValue"),
  dnaInput: document.querySelector("#dnaInput"),
  transcribeDna: document.querySelector("#transcribeDna"),
  translateDna: document.querySelector("#translateDna"),
  mutateDna: document.querySelector("#mutateDna"),
  substituteDna: document.querySelector("#substituteDna"),
  insertDna: document.querySelector("#insertDna"),
  deleteDna: document.querySelector("#deleteDna"),
  restoreDna: document.querySelector("#restoreDna"),
  analyzeDna: document.querySelector("#analyzeDna"),
  dnaStatus: document.querySelector("#dnaStatus"),
  mrnaOutput: document.querySelector("#mrnaOutput"),
  proteinOutput: document.querySelector("#proteinOutput"),
};

const modes = {
  "double-slit": {
    title: "Double Slit",
    metric: "Interference",
    summary: "One particle at a time builds a wave interference pattern.",
    text: "Two slits create two probability amplitudes. Dots land one-by-one, but many dots reveal bright and dark bands.",
  },
  light: {
    title: "Wave + Particle Light",
    metric: "Photons",
    summary: "Light spreads like a wave and arrives as photon-like detections.",
    text: "Expanding rings show wavefronts from a source. Moving dots show photon detections guided by the wave.",
  },
  "two-places": {
    title: "Two Places",
    metric: "Superposition",
    summary: "A single state can have probability in two separated places.",
    text: "The two blue lobes are two possible detection regions. White dots show measurements appearing in either place.",
  },
  packet: {
    title: "Wave Packet",
    metric: "Tunneling",
    summary: "A moving quantum packet reflects and leaks through a barrier.",
    text: "The packet travels toward a green barrier. Part of the wave can reflect while part tunnels through.",
  },
  dna: {
    title: "DNA Lab",
    metric: "Transcription",
    summary: "Build mRNA from DNA, then translate codons into amino acids.",
    text: "DNA stores instructions. Transcription copies a coding strand into mRNA, then translation reads mRNA codons to build a protein chain.",
  },
};

const state = {
  mode: "double-slit",
  paused: false,
  t: 0,
  hits: [],
  photons: [],
  packetSamples: [],
  doublePattern: [],
  backendOk: false,
  lastPatternKey: "",
  chatHistory: [],
  chatWaiting: false,
  attachedImage: null,
  user: null,
  dnaStep: "transcribe",
  dnaCodonIndex: 0,
  dnaMutatedIndex: -1,
  dnaMutation: null,
  dnaMutations: [],
  dnaHover: null,
  dnaSelected: null,
  dnaHotspots: [],
  dnaOriginal: "",
};

const CODON_TABLE = {
  UUU: "Phe", UUC: "Phe", UUA: "Leu", UUG: "Leu",
  UCU: "Ser", UCC: "Ser", UCA: "Ser", UCG: "Ser",
  UAU: "Tyr", UAC: "Tyr", UAA: "Stop", UAG: "Stop",
  UGU: "Cys", UGC: "Cys", UGA: "Stop", UGG: "Trp",
  CUU: "Leu", CUC: "Leu", CUA: "Leu", CUG: "Leu",
  CCU: "Pro", CCC: "Pro", CCA: "Pro", CCG: "Pro",
  CAU: "His", CAC: "His", CAA: "Gln", CAG: "Gln",
  CGU: "Arg", CGC: "Arg", CGA: "Arg", CGG: "Arg",
  AUU: "Ile", AUC: "Ile", AUA: "Ile", AUG: "Met",
  ACU: "Thr", ACC: "Thr", ACA: "Thr", ACG: "Thr",
  AAU: "Asn", AAC: "Asn", AAA: "Lys", AAG: "Lys",
  AGU: "Ser", AGC: "Ser", AGA: "Arg", AGG: "Arg",
  GUU: "Val", GUC: "Val", GUA: "Val", GUG: "Val",
  GCU: "Ala", GCC: "Ala", GCA: "Ala", GCG: "Ala",
  GAU: "Asp", GAC: "Asp", GAA: "Glu", GAG: "Glu",
  GGU: "Gly", GGC: "Gly", GGA: "Gly", GGG: "Gly",
};

const MAX_HOMEWORK_IMAGE_BYTES = 3 * 1024 * 1024;

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(600, Math.floor(rect.width * dpr));
  canvas.height = Math.max(360, Math.floor(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function view() {
  return canvas.getBoundingClientRect();
}

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function hitTestDna(point) {
  for (let i = state.dnaHotspots.length - 1; i >= 0; i -= 1) {
    const spot = state.dnaHotspots[i];
    if (point.x >= spot.x && point.x <= spot.x + spot.w && point.y >= spot.y && point.y <= spot.y + spot.h) {
      return spot;
    }
  }
  return null;
}

function setDnaHover(spot) {
  const same =
    state.dnaHover
    && spot
    && state.dnaHover.type === spot.type
    && state.dnaHover.index === spot.index;
  if (same || (!state.dnaHover && !spot)) return;
  state.dnaHover = spot;
  canvas.style.cursor = spot ? "pointer" : "";
  if (state.mode === "dna" && spot) updateDnaOutputs();
}

function cycleDnaBase(index) {
  const dna = cleanDnaSequence() || "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG";
  if (index < 0 || index >= dna.length) return;
  state.dnaSelected = { type: "base", index };
  applyDnaMutation("substitution", { index });
}

function handleCanvasPointerMove(event) {
  if (state.mode !== "dna") {
    setDnaHover(null);
    return;
  }
  setDnaHover(hitTestDna(canvasPoint(event)));
}

function handleCanvasClick(event) {
  if (state.mode !== "dna") return;
  const spot = hitTestDna(canvasPoint(event));
  if (!spot) return;
  if (spot.type === "base") {
    cycleDnaBase(spot.index);
    return;
  }
  if (spot.type === "codon") {
    state.dnaStep = "translate";
    state.dnaCodonIndex = spot.index;
    state.dnaSelected = { type: "codon", index: spot.index };
    updateDnaOutputs();
    const analysis = getDnaAnalysis();
    const codon = analysis.codons[spot.index] || "";
    addChatMessage("system", `Selected codon ${spot.index + 1}: ${codon} -> ${CODON_TABLE[codon] || "?"}.`);
  }
}

function getSettings() {
  const settings = {
    particles: els.showParticles.checked,
    wave: els.showWave.checked,
    whichPath: els.whichPath.checked,
    separation: Number(els.slitSeparation.value),
    wavelength: Number(els.wavelength.value),
    slitWidth: Number(els.slitWidth.value),
    rate: Number(els.particleRate.value),
    barrier: Number(els.barrierHeight.value),
  };
  if (state.mode === "dna") settings.dna = getDnaAnalysis();
  return settings;
}

function cleanDnaSequence() {
  const cleaned = els.dnaInput.value.toUpperCase().replace(/[^ATCG]/g, "").slice(0, 72);
  if (els.dnaInput.value !== cleaned) els.dnaInput.value = cleaned;
  return cleaned;
}

function transcribeDna(sequence = cleanDnaSequence()) {
  return sequence.replaceAll("T", "U");
}

function codonsFromMrna(mrna) {
  const codons = [];
  for (let i = 0; i + 2 < mrna.length; i += 3) codons.push(mrna.slice(i, i + 3));
  return codons;
}

function translateMrna(mrna = transcribeDna()) {
  const aminoAcids = [];
  for (const codon of codonsFromMrna(mrna)) {
    const amino = CODON_TABLE[codon] || "?";
    aminoAcids.push(amino);
    if (amino === "Stop") break;
  }
  return aminoAcids;
}

function getDnaAnalysis() {
  const sequence = cleanDnaSequence();
  const mrna = transcribeDna(sequence);
  const codons = codonsFromMrna(mrna);
  const protein = translateMrna(mrna);
  const startCodonIndex = codons.indexOf("AUG");
  const stopCodonIndex = codons.findIndex((codon) => CODON_TABLE[codon] === "Stop");
  return {
    codingStrand: sequence,
    mrna,
    codons,
    protein,
    startCodonIndex,
    stopCodonIndex,
    mutation: state.dnaMutation,
    mutations: state.dnaMutations || [],
  };
}

function updateDnaOutputs() {
  const dna = cleanDnaSequence();
  const mrna = transcribeDna(dna);
  const codons = codonsFromMrna(mrna);
  const protein = translateMrna(mrna);
  const codonCount = codons.length;
  els.mrnaOutput.textContent = mrna ? codons.join(" ") || mrna : "Type A, T, C, and G";
  els.proteinOutput.textContent = protein.length ? protein.join(" - ") : "Waiting for full codons";
  if (state.dnaHover?.type === "base") {
    const index = state.dnaHover.index;
    const base = dna[index] || "?";
    const mrnaBase = mrna[index] || "?";
    const complement = { A: "T", T: "A", C: "G", G: "C" }[base] || "?";
    els.dnaStatus.textContent = `Hover base ${index + 1}: DNA ${base}, paired with ${complement}, transcribes to mRNA ${mrnaBase}. Click to mutate.`;
  } else if (state.dnaHover?.type === "codon") {
    const index = state.dnaHover.index;
    const codon = codons[index] || "";
    els.dnaStatus.textContent = `Hover codon ${index + 1}: ${codon || "incomplete"} -> ${CODON_TABLE[codon] || "?"}. Click to select it.`;
  } else if (state.dnaMutatedIndex >= 0) {
    const base = dna[state.dnaMutatedIndex] || "?";
    const codonNumber = Math.floor(state.dnaMutatedIndex / 3) + 1;
    const mutationType = state.dnaMutation?.type || "substitution";
    const mutationCount = state.dnaMutations?.length || 1;
    const countText = mutationCount > 1 ? ` ${mutationCount} mutation spots are highlighted.` : "";
    if (mutationType === "insertion") {
      els.dnaStatus.textContent = `Insertion visible at base ${state.dnaMutatedIndex + 1}: added ${state.dnaMutation?.to || base}, shifting later codons.${countText}`;
    } else if (mutationType === "deletion") {
      els.dnaStatus.textContent = `Deletion marker at base ${state.dnaMutation?.position || state.dnaMutatedIndex + 1}: removed ${state.dnaMutation?.from || "a base"}, shifting later codons.${countText}`;
    } else {
      els.dnaStatus.textContent = `Substitution visible: base ${state.dnaMutatedIndex + 1} changed to ${base} in codon ${codonNumber}.${countText}`;
    }
  } else if (state.dnaStep === "translate") {
    els.dnaStatus.textContent = `Translation ready: ${codonCount} complete codon${codonCount === 1 ? "" : "s"} -> ${protein.length || 0} amino acid${protein.length === 1 ? "" : "s"}.`;
  } else {
    els.dnaStatus.textContent = `Transcription ready: DNA T bases become U bases in mRNA.`;
  }
  if (state.mode === "dna") {
    els.hitCount.textContent = String(dna.length);
    els.modeMetric.textContent = state.dnaStep === "translate" ? "Translation" : "Transcription";
  }
}

function updateLabels() {
  const settings = getSettings();
  els.slitSeparationValue.value = settings.separation.toFixed(2);
  els.wavelengthValue.value = settings.wavelength.toFixed(2);
  els.slitWidthValue.value = settings.slitWidth.toFixed(2);
  els.particleRateValue.value = String(settings.rate);
  els.barrierHeightValue.value = settings.barrier.toFixed(2);
  els.hitCount.textContent = String(state.hits.length);
  els.countLabel.textContent = state.mode === "dna" ? "DNA bases" : "Detections";
  els.modeMetric.textContent = modes[state.mode].metric;
  els.playPause.textContent = state.paused ? "Play" : "Pause";
  els.modeTitle.textContent = modes[state.mode].title;
  els.modeText.textContent = modes[state.mode].text;
  els.modeSummary.textContent = modes[state.mode].summary;
  document.querySelectorAll(".double-only").forEach((el) => {
    el.classList.toggle("hidden", state.mode !== "double-slit");
  });
  document.querySelectorAll(".packet-only").forEach((el) => {
    el.classList.toggle("hidden", state.mode !== "packet");
  });
  document.querySelectorAll(".dna-only").forEach((el) => {
    el.classList.toggle("hidden", state.mode !== "dna");
  });
  document.querySelectorAll(".quantum-only").forEach((el) => {
    el.classList.toggle("hidden", state.mode === "dna");
  });
  if (state.mode === "dna") updateDnaOutputs();
}

async function checkBackend() {
  try {
    const res = await fetch(apiUrl("/api/health"), { cache: "no-store" });
    const data = await res.json();
    state.backendOk = Boolean(data.ok);
  } catch (error) {
    state.backendOk = false;
    els.chatSource.textContent = "Backend offline";
    if (API_BASE) {
      els.aiText.textContent = `Could not connect to backend at ${API_BASE}. Check the deployed backend URL and CORS.`;
    }
  }
  els.backendStatus.textContent = state.backendOk ? "Backend online" : "Frontend only";
  els.backendStatus.className = `status ${state.backendOk ? "ok" : "bad"}`;
  els.apiMetric.textContent = state.backendOk ? "Online" : "Offline";
}

async function updateDoublePattern() {
  const settings = getSettings();
  const key = [
    settings.separation.toFixed(2),
    settings.slitWidth.toFixed(2),
    settings.wavelength.toFixed(2),
    settings.whichPath,
  ].join(":");
  if (key === state.lastPatternKey && state.doublePattern.length) return;
  state.lastPatternKey = key;

  if (state.backendOk) {
    const params = new URLSearchParams({
      separation: settings.separation,
      slitWidth: settings.slitWidth,
      wavelength: settings.wavelength,
      whichPath: settings.whichPath,
      samples: 260,
    });
    try {
      const res = await fetch(apiUrl(`/api/double-slit?${params}`));
      const data = await res.json();
      state.doublePattern = data.points;
      return;
    } catch {
      state.backendOk = false;
      els.backendStatus.textContent = "Frontend only";
      els.backendStatus.className = "status bad";
      els.apiMetric.textContent = "Offline";
    }
  }

  state.doublePattern = makeLocalDoublePattern(settings);
}

function makeLocalDoublePattern(settings) {
  const points = [];
  let maxValue = 0;
  for (let i = 0; i < 260; i += 1) {
    const y = -3 + (i / 259) * 6;
    const beta = Math.PI * settings.slitWidth * y / Math.max(settings.wavelength, 0.02);
    const envelope = Math.abs(beta) < 1e-9 ? 1 : (Math.sin(beta) / beta) ** 2;
    const phase = Math.PI * settings.separation * y / Math.max(settings.wavelength, 0.02);
    const value = envelope * (settings.whichPath ? 1 : Math.cos(phase) ** 2);
    maxValue = Math.max(maxValue, value);
    points.push({ y, intensity: value });
  }
  return points.map((p) => ({ y: p.y, intensity: maxValue ? p.intensity / maxValue : 0 }));
}

function reset() {
  state.t = 0;
  state.hits = [];
  state.photons = [];
  state.packetSamples = [];
  state.dnaCodonIndex = 0;
  state.dnaHover = null;
  state.lastPatternKey = "";
  updateLabels();
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });
  reset();
  addChatMessage("system", `Switched to ${modes[state.mode].title}.`);
}

function setDnaStep(step) {
  state.dnaStep = step;
  state.dnaCodonIndex = 0;
  state.dnaMutatedIndex = -1;
  state.dnaMutation = null;
  state.dnaMutations = [];
  updateDnaOutputs();
  els.modeMetric.textContent = step === "translate" ? "Translation" : "Transcription";
  addChatMessage("system", step === "translate" ? "Translation mode: codons are lined up under amino acids." : "Transcription mode: DNA is copied into mRNA.");
}

function ensureDnaOriginal(dna) {
  if (!state.dnaOriginal) state.dnaOriginal = dna;
}

function clampDnaIndex(index, dna) {
  return Math.min(Math.max(index, 0), Math.max(dna.length - 1, 0));
}

function selectedDnaIndex(dna, options = {}) {
  if (Number.isInteger(options.index)) return clampDnaIndex(options.index, dna);
  const visibleLength = Math.min(dna.length, 24);
  if (options.random) {
    const used = new Set((state.dnaMutations || []).map((mutation) => mutation.highlightIndex));
    if (state.dnaMutatedIndex >= 0) used.add(state.dnaMutatedIndex);
    const candidates = Array.from({ length: visibleLength }, (_, index) => index)
      .filter((index) => !used.has(index));
    const pool = candidates.length ? candidates : Array.from({ length: visibleLength }, (_, index) => index);
    return pool[Math.floor(Math.random() * pool.length)] || 0;
  }
  if (options.useSelection !== false) {
    if (state.dnaSelected?.type === "base") return clampDnaIndex(state.dnaSelected.index, dna);
    if (state.dnaSelected?.type === "codon") return clampDnaIndex(state.dnaSelected.index * 3, dna);
    if (state.dnaHover?.type === "base") return clampDnaIndex(state.dnaHover.index, dna);
    if (state.dnaHover?.type === "codon") return clampDnaIndex(state.dnaHover.index * 3, dna);
  }
  return clampDnaIndex(Math.floor(dna.length / 2), dna);
}

function rememberDnaMutation(mutation) {
  state.dnaMutations = [...(state.dnaMutations || []), mutation]
    .slice(-10)
    .map((item) => ({
      ...item,
      highlightIndex: Math.max(0, Math.min(item.highlightIndex, Math.max(els.dnaInput.value.length - 1, 0))),
    }));
}

function applyDnaMutation(kind = "substitution", options = {}) {
  const dna = cleanDnaSequence() || "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG";
  ensureDnaOriginal(dna);
  const bases = ["A", "T", "C", "G"];
  const visibleLength = Math.min(dna.length, 24);
  const index = Math.min(selectedDnaIndex(dna, options), Math.max(visibleLength - 1, 0));
  const current = dna[index] || "";
  const nextBase = bases[(bases.indexOf(current) + 1) % bases.length] || "A";
  let nextSequence = dna;
  let mutationLabel = "substitution";
  let highlightIndex = index;
  if (kind === "insertion") {
    nextSequence = dna.slice(0, index + 1) + nextBase + dna.slice(index + 1);
    mutationLabel = "insertion";
    highlightIndex = index + 1;
  } else if (kind === "deletion" && dna.length > 1) {
    nextSequence = dna.slice(0, index) + dna.slice(index + 1);
    mutationLabel = "deletion";
    highlightIndex = Math.min(index, nextSequence.length - 1);
  } else {
    nextSequence = dna.slice(0, index) + nextBase + dna.slice(index + 1);
  }
  els.dnaInput.value = nextSequence.slice(0, 72);
  state.dnaStep = "translate";
  state.dnaCodonIndex = Math.floor(highlightIndex / 3);
  state.dnaMutatedIndex = highlightIndex;
  state.dnaMutation = {
    type: mutationLabel,
    index,
    highlightIndex,
    position: index + 1,
    from: current,
    to: mutationLabel === "deletion" ? "" : nextBase,
    codonNumber: Math.floor(index / 3) + 1,
    beforeLength: dna.length,
    afterLength: nextSequence.length,
  };
  rememberDnaMutation(state.dnaMutation);
  state.dnaSelected = { type: "base", index: Math.min(highlightIndex, els.dnaInput.value.length - 1) };
  updateDnaOutputs();
  els.modeMetric.textContent = "Mutation";
  addChatMessage("system", `DNA ${mutationLabel} at base ${index + 1}.`);
}

function mutateDnaSequence() {
  applyDnaMutation("substitution", { random: true, useSelection: false });
}

function restoreDnaSequence() {
  if (!state.dnaOriginal) state.dnaOriginal = cleanDnaSequence();
  els.dnaInput.value = state.dnaOriginal || "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG";
  state.dnaMutatedIndex = -1;
  state.dnaMutation = null;
  state.dnaMutations = [];
  state.dnaSelected = null;
  state.dnaHover = null;
  state.dnaStep = "transcribe";
  updateDnaOutputs();
  addChatMessage("system", "DNA sequence restored to the saved original.");
}

function analyzeDnaWithAi() {
  const analysis = getDnaAnalysis();
  const mutationText = analysis.mutation
    ? ` Explain the mutation at base ${analysis.mutation.position}, from ${analysis.mutation.from} to ${analysis.mutation.to}, in codon ${analysis.mutation.codonNumber}.`
    : " Also say whether there is a start codon and a stop codon.";
  els.chatInput.value = `Analyze this DNA coding strand: ${analysis.codingStrand}. Transcribe it, translate it, detect what is in it, and explain what the protein means.${mutationText}`;
  resizeChatInput();
  els.chatForm.requestSubmit();
}

function clear() {
  const { width, height } = view();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#101720";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#233044";
  ctx.lineWidth = 1;
  for (let i = 1; i < 8; i += 1) {
    const x = (width * i) / 8;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let i = 1; i < 5; i += 1) {
    const y = (height * i) / 5;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

function drawText(text, x, y, color = "#a8b3c4", size = 15) {
  ctx.fillStyle = color;
  ctx.font = `${size}px system-ui, sans-serif`;
  ctx.fillText(text, x, y);
}

function baseColor(base) {
  return { A: "#73e3a4", T: "#ffc857", C: "#46c2ff", G: "#ff8fab", U: "#bda8ff" }[base] || "#eef3fb";
}

function roundedRectPath(x, y, width, height, radius = 8) {
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, width, height, radius);
    return;
  }
  const r = Math.min(radius, width / 2, height / 2);
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
}

function drawDnaLab() {
  const { width, height } = view();
  const dna = cleanDnaSequence() || "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG";
  const mrna = transcribeDna(dna);
  const codons = codonsFromMrna(mrna);
  const protein = translateMrna(mrna);
  const visible = dna.slice(0, Math.min(24, dna.length));
  state.dnaHotspots = [];
  const startX = width * 0.12;
  const endX = width * 0.88;
  const midY = height * 0.33;
  const step = (endX - startX) / Math.max(visible.length - 1, 1);
  const phase = state.t * 0.055;
  const mutation = state.dnaMutation;
  const mutationHistory = (state.dnaMutations || [])
    .filter((item) => Number.isInteger(item.highlightIndex))
    .map((item) => ({
      ...item,
      visualIndex: Math.min(Math.max(item.highlightIndex, 0), Math.max(visible.length - 1, 0)),
    }));
  const frameShiftMutations = mutationHistory.filter((item) => item.type === "insertion" || item.type === "deletion");
  const frameShiftStart = frameShiftMutations.length
    ? Math.min(...frameShiftMutations.map((item) => item.visualIndex))
    : null;
  const frameShift = mutation && (mutation.type === "insertion" || mutation.type === "deletion");
  const mutationVisualIndex = Math.min(
    mutation?.highlightIndex ?? state.dnaMutatedIndex,
    Math.max(visible.length - 1, 0),
  );

  drawText("DNA opens -> mRNA copies -> ribosome reads codons", 24, 30, "#ffc857");
  drawText("Hover bases for details. Click a base to mutate it. Click a codon to select it.", 24, 54, "#9fb1c4", 13);

  if (mutation && mutationVisualIndex >= 0 && mutationVisualIndex < visible.length) {
    const bandX = startX + mutationVisualIndex * step - step * 0.5;
    ctx.fillStyle = frameShift ? "rgba(255, 206, 107, 0.08)" : "rgba(124, 242, 189, 0.08)";
    ctx.fillRect(Math.max(0, bandX), midY - 86, endX - Math.max(0, bandX) + step, height * 0.55);
    ctx.strokeStyle = frameShift ? "rgba(255, 206, 107, 0.5)" : "rgba(124, 242, 189, 0.45)";
    ctx.setLineDash([8, 8]);
    ctx.beginPath();
    ctx.moveTo(startX + mutationVisualIndex * step, midY - 92);
    ctx.lineTo(startX + mutationVisualIndex * step, height * 0.9);
    ctx.stroke();
    ctx.setLineDash([]);
    drawText(
      frameShift ? "frameshift zone" : "changed base",
      Math.min(startX + mutationVisualIndex * step + 10, width - 150),
      midY - 94,
      frameShift ? "#ffce6b" : "#7cf2bd",
      13,
    );
  }
  mutationHistory.forEach((item, markerIndex) => {
    const x = startX + item.visualIndex * step;
    const isFrameMarker = item.type === "insertion" || item.type === "deletion";
    ctx.strokeStyle = isFrameMarker ? "rgba(255, 206, 107, 0.62)" : "rgba(124, 242, 189, 0.62)";
    ctx.setLineDash(markerIndex === mutationHistory.length - 1 ? [] : [4, 8]);
    ctx.lineWidth = markerIndex === mutationHistory.length - 1 ? 2.2 : 1.4;
    ctx.beginPath();
    ctx.moveTo(x, midY - 74);
    ctx.lineTo(x, midY + 74);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = isFrameMarker ? "#ffce6b" : "#7cf2bd";
    ctx.font = "760 10px Aptos, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${item.position}`, x, midY - 80 - (markerIndex % 2) * 14);
  });

  ctx.lineWidth = 3;
  ctx.strokeStyle = "rgba(70, 194, 255, 0.72)";
  ctx.beginPath();
  for (let i = 0; i < visible.length; i += 1) {
    const x = startX + i * step;
    const y = midY + Math.sin(i * 0.85 + phase) * 42;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  ctx.strokeStyle = "rgba(115, 227, 164, 0.7)";
  ctx.beginPath();
  for (let i = 0; i < visible.length; i += 1) {
    const x = startX + i * step;
    const y = midY - Math.sin(i * 0.85 + phase) * 42;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  for (let i = 0; i < visible.length; i += 1) {
    const base = visible[i];
    const complement = { A: "T", T: "A", C: "G", G: "C" }[base] || "";
    const x = startX + i * step;
    const y1 = midY + Math.sin(i * 0.85 + phase) * 42;
    const y2 = midY - Math.sin(i * 0.85 + phase) * 42;
    const markerMutation = mutationHistory.find((item) => item.visualIndex === i)
      || (i === state.dnaMutatedIndex ? mutation : null);
    const isMutated = Boolean(markerMutation);
    const isHovered = state.dnaHover?.type === "base" && state.dnaHover.index === i;
    const isSelected = state.dnaSelected?.type === "base" && state.dnaSelected.index === i;
    const isFrameshiftBase = frameShiftStart !== null && i >= frameShiftStart;
    state.dnaHotspots.push({ type: "base", index: i, x: x - 18, y: Math.min(y1, y2) - 18, w: 36, h: Math.abs(y2 - y1) + 36 });
    ctx.strokeStyle = isFrameshiftBase ? "rgba(255, 206, 107, 0.45)" : "rgba(248, 251, 255, 0.28)";
    ctx.lineWidth = isFrameshiftBase ? 2.4 : 1.6;
    ctx.beginPath();
    ctx.moveTo(x, y1);
    ctx.lineTo(x, y2);
    ctx.stroke();
    if (isMutated || isHovered || isSelected || isFrameshiftBase) {
      ctx.fillStyle = isHovered
        ? "rgba(124, 242, 189, 0.22)"
        : isFrameshiftBase
          ? "rgba(255, 206, 107, 0.16)"
          : "rgba(255, 200, 87, 0.28)";
      ctx.beginPath();
      ctx.arc(x, y1, isHovered ? 24 : 20, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = isMutated ? (markerMutation?.type === "insertion" ? "#7cf2bd" : "#ffc857") : baseColor(base);
    ctx.beginPath();
    ctx.arc(x, y1, isHovered ? 14 : 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#071b3a";
    ctx.font = "700 12px Aptos, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(base, x, y1 + 4);
    ctx.fillStyle = baseColor(complement);
    ctx.beginPath();
    ctx.arc(x, y2, isHovered ? 14 : 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#071b3a";
    ctx.fillText(complement, x, y2 + 4);
    if (isMutated && markerMutation) {
      ctx.fillStyle = markerMutation.type === "deletion" ? "#ff8fab" : "#ffce6b";
      ctx.font = "760 11px Aptos, system-ui, sans-serif";
      const label =
        markerMutation.type === "insertion"
          ? `+${markerMutation.to}`
          : markerMutation.type === "deletion"
            ? `-${markerMutation.from}`
            : `${markerMutation.from}->${markerMutation.to}`;
      ctx.fillText(label, x, y1 - 24);
    }
  }
  ctx.textAlign = "left";

  const mrnaY = height * 0.58;
  const shownMrna = mrna.slice(0, Math.min(24, mrna.length));
  ctx.strokeStyle = "#bda8ff";
  ctx.lineWidth = 4;
  ctx.beginPath();
  for (let i = 0; i < shownMrna.length; i += 1) {
    const x = startX + i * step;
    const y = mrnaY + Math.sin(i * 0.65 + phase * 1.5) * 12;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  for (let i = 0; i < shownMrna.length; i += 1) {
    const x = startX + i * step;
    const y = mrnaY + Math.sin(i * 0.65 + phase * 1.5) * 12;
    const isFrameshiftMrna = frameShiftStart !== null && i >= frameShiftStart;
    if (isFrameshiftMrna) {
      ctx.fillStyle = "rgba(255, 206, 107, 0.18)";
      ctx.beginPath();
      ctx.arc(x, y, 15, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = isFrameshiftMrna ? "#ffce6b" : baseColor(shownMrna[i]);
    ctx.beginPath();
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#071b3a";
    ctx.font = "700 11px Aptos, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(shownMrna[i], x, y + 4);
  }
  ctx.textAlign = "left";

  const ribosomeX = startX + ((state.t * 0.35) % Math.max(step * Math.max(codons.length * 3, 1), 1));
  ctx.fillStyle = "rgba(255, 200, 87, 0.22)";
  ctx.strokeStyle = "#ffc857";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.ellipse(Math.min(ribosomeX, endX), mrnaY, 54, 30, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  drawText("ribosome", Math.min(ribosomeX + 45, width - 100), mrnaY + 7, "#ffc857", 14);

  const codonY = height * 0.78;
  const maxCodons = Math.min(codons.length, 7);
  const codonGap = Math.min(104, (endX - startX) / Math.max(maxCodons, 1));
  const codonW = Math.min(88, codonGap - 10);
  for (let i = 0; i < maxCodons; i += 1) {
    const x = startX + i * codonGap;
    const isActiveCodon = i === state.dnaCodonIndex % Math.max(maxCodons, 1);
    const isMutatedCodon = mutationHistory.some((item) => Math.floor(item.visualIndex / 3) === i);
    const isHoveredCodon = state.dnaHover?.type === "codon" && state.dnaHover.index === i;
    const isSelectedCodon = state.dnaSelected?.type === "codon" && state.dnaSelected.index === i;
    const isFrameshiftCodon = frameShiftStart !== null && i >= Math.floor(frameShiftStart / 3);
    state.dnaHotspots.push({ type: "codon", index: i, x, y: codonY, w: codonW, h: 62 });
    ctx.fillStyle = isHoveredCodon
      ? "rgba(124, 242, 189, 0.18)"
      : isFrameshiftCodon
        ? "rgba(255, 206, 107, 0.16)"
      : isActiveCodon || isSelectedCodon
        ? "rgba(255, 200, 87, 0.24)"
        : "rgba(16, 37, 66, 0.86)";
    ctx.strokeStyle = isHoveredCodon ? "#7cf2bd" : isFrameshiftCodon ? "rgba(255, 206, 107, 0.68)" : "rgba(99, 135, 170, 0.68)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.rect(x, codonY, codonW, 62);
    ctx.fill();
    ctx.stroke();
    if (isMutatedCodon || isSelectedCodon) {
      ctx.strokeStyle = isSelectedCodon ? "#7cf2bd" : "#ffc857";
      ctx.lineWidth = 3;
      ctx.strokeRect(x + 2, codonY + 2, codonW - 4, 58);
    }
    const bases = codons[i].split("");
    bases.forEach((base, baseIndex) => {
      const bx = x + 16 + baseIndex * ((codonW - 32) / 2);
      ctx.fillStyle = baseColor(base);
      ctx.beginPath();
      ctx.arc(bx, codonY + 20, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#071b3a";
      ctx.font = "700 10px Aptos, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(base, bx, codonY + 24);
    });
    ctx.textAlign = "center";
    ctx.fillStyle = isFrameshiftCodon ? "#ffce6b" : isActiveCodon ? "#ffc857" : "#73e3a4";
    ctx.font = "700 13px Aptos, system-ui, sans-serif";
    ctx.fillText(CODON_TABLE[codons[i]] || "?", x + codonW / 2, codonY + 49);
  }
  ctx.textAlign = "left";
  if (state.t % 45 === 0) state.dnaCodonIndex = (state.dnaCodonIndex + 1) % Math.max(codons.length, 1);
  drawText(`Protein: ${protein.join(" - ") || "waiting for complete codons"}`, 24, height - 24, "#a8b3c4", 15);
  if (state.dnaHover) {
    const label = state.dnaHover.type === "base"
      ? `Base ${state.dnaHover.index + 1}: ${dna[state.dnaHover.index] || "?"} -> ${mrna[state.dnaHover.index] || "?"}`
      : `Codon ${state.dnaHover.index + 1}: ${codons[state.dnaHover.index] || "?"} -> ${CODON_TABLE[codons[state.dnaHover.index]] || "?"}`;
    const tooltipX = Math.min(width - 260, Math.max(18, state.dnaHover.x + 12));
    const tooltipY = Math.max(64, state.dnaHover.y - 36);
    ctx.fillStyle = "rgba(5, 18, 33, 0.92)";
    ctx.strokeStyle = "rgba(124, 242, 189, 0.5)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    roundedRectPath(tooltipX, tooltipY, 242, 32, 7);
    ctx.fill();
    ctx.stroke();
    drawText(label, tooltipX + 10, tooltipY + 21, "#f3f7fb", 13);
  }
  if (state.dnaMutation) {
    const mutation = state.dnaMutation;
    const originalLength = mutation.beforeLength || (state.dnaOriginal ? state.dnaOriginal.length : dna.length);
    const frameShift = mutation.type === "insertion" || mutation.type === "deletion";
    const panelX = Math.max(18, width - 330);
    const panelY = 18;
    ctx.fillStyle = "rgba(5, 18, 33, 0.9)";
    ctx.strokeStyle = frameShift ? "#ffce6b" : "#7cf2bd";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    roundedRectPath(panelX, panelY, 306, 110, 8);
    ctx.fill();
    ctx.stroke();
    drawText(`Mutation simulator: ${mutation.type}`, panelX + 12, panelY + 23, frameShift ? "#ffce6b" : "#7cf2bd", 14);
    drawText(`Base ${mutation.position}: ${mutation.from || "gap"} -> ${mutation.to || "deleted"}`, panelX + 12, panelY + 46, "#f3f7fb", 13);
    drawText(`Length ${originalLength} -> ${dna.length}${frameShift ? "  |  frameshift risk" : ""}`, panelX + 12, panelY + 69, "#9fb1c4", 13);
    drawText(frameShift ? "Downstream codons are recolored." : "One codon may change amino acid.", panelX + 12, panelY + 88, "#9fb1c4", 12);
  }
}

function drawDoubleSlit(settings) {
  const { width, height } = view();
  const wallX = width * 0.34;
  const screenX = width * 0.88;
  const center = height * 0.5;
  const sep = settings.separation * 26;
  const slitH = 46;

  if (settings.wave) {
    for (let r = 35 + (state.t * 1.8) % 80; r < width * 0.65; r += 80) {
      drawArc(wallX, center - sep, r, "rgba(70, 194, 255, 0.18)");
      drawArc(wallX, center + sep, r, "rgba(70, 194, 255, 0.18)");
    }
  }

  ctx.strokeStyle = "#73e3a4";
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.moveTo(wallX, 40);
  ctx.lineTo(wallX, center - sep - slitH / 2);
  ctx.moveTo(wallX, center - sep + slitH / 2);
  ctx.lineTo(wallX, center + sep - slitH / 2);
  ctx.moveTo(wallX, center + sep + slitH / 2);
  ctx.lineTo(wallX, height - 40);
  ctx.stroke();

  ctx.strokeStyle = "#f8fbff";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(screenX, 42);
  ctx.lineTo(screenX, height - 42);
  ctx.stroke();

  drawIntensityCurve(screenX, center, height * 0.42);
  drawHits();
  drawText(settings.whichPath ? "which-path detector ON: no stripes" : "which-path hidden: interference stripes", 24, 30, "#ffc857");
}

function drawArc(x, y, radius, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(x, y, radius, -0.72, 0.72);
  ctx.stroke();
}

function drawIntensityCurve(screenX, center, scale) {
  if (!state.doublePattern.length) return;
  ctx.strokeStyle = "#46c2ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  state.doublePattern.forEach((p, i) => {
    const y = center + (p.y / 3) * scale;
    const x = screenX - 12 - p.intensity * 90;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawHits() {
  if (!els.showParticles.checked) return;
  ctx.fillStyle = "#f8fbff";
  for (const hit of state.hits) {
    ctx.globalAlpha = hit.alpha ?? 0.9;
    ctx.beginPath();
    ctx.arc(hit.x, hit.y, hit.r ?? 2.2, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

function sampleDoubleHit() {
  const { width, height } = view();
  if (!state.doublePattern.length) return;
  const total = state.doublePattern.reduce((sum, p) => sum + p.intensity, 0);
  let target = Math.random() * total;
  let chosen = state.doublePattern[0];
  for (const point of state.doublePattern) {
    target -= point.intensity;
    if (target <= 0) {
      chosen = point;
      break;
    }
  }
  const screenX = width * 0.88;
  const center = height * 0.5;
  const scale = height * 0.42;
  state.hits.push({
    x: screenX + (Math.random() - 0.5) * 9,
    y: center + (chosen.y / 3) * scale + (Math.random() - 0.5) * 4,
    r: 1.8 + Math.random() * 1.6,
  });
  if (state.hits.length > 1600) state.hits.splice(0, state.hits.length - 1600);
}

function drawLight(settings) {
  const { width, height } = view();
  const source = { x: width * 0.16, y: height * 0.5 };
  const screenX = width * 0.86;

  if (settings.wave) {
    for (let r = 25 + (state.t * 2.6) % 70; r < width; r += 70) {
      ctx.strokeStyle = `rgba(70, 194, 255, ${0.28 - Math.min(r / width, 0.8) * 0.18})`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(source.x, source.y, r, -0.72, 0.72);
      ctx.stroke();
    }
  }

  ctx.fillStyle = "#ffc857";
  ctx.beginPath();
  ctx.arc(source.x, source.y, 9, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "#73e3a4";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(screenX, 44);
  ctx.lineTo(screenX, height - 44);
  ctx.stroke();

  if (settings.particles) {
    for (const photon of state.photons) {
      photon.x += photon.vx;
      photon.y += photon.vy;
      ctx.fillStyle = "#f8fbff";
      ctx.beginPath();
      ctx.arc(photon.x, photon.y, 3, 0, Math.PI * 2);
      ctx.fill();
      if (photon.x > screenX) {
        state.hits.push({ x: screenX + Math.random() * 6, y: photon.y, r: 2.2, alpha: 0.92 });
        photon.dead = true;
      }
    }
    state.photons = state.photons.filter((p) => !p.dead && p.x < width + 40);
    drawHits();
  }

  drawText("rings = wavefronts, dots = photon detections", 24, 30, "#ffc857");
}

function spawnPhoton() {
  const { width, height } = view();
  const yTarget = height * (0.22 + Math.random() * 0.56);
  const source = { x: width * 0.16, y: height * 0.5 };
  const dx = width * 0.7 - source.x;
  state.photons.push({
    x: source.x,
    y: source.y,
    vx: 5.2,
    vy: ((yTarget - source.y) / dx) * 5.2,
  });
}

function drawTwoPlaces(settings) {
  const { width, height } = view();
  const left = { x: width * 0.35, y: height * 0.5 };
  const right = { x: width * 0.65, y: height * 0.5 };
  const pulse = Math.sin(state.t * 0.04) * 8;

  if (settings.wave) {
    drawLobe(left.x, left.y, 88 + pulse, "#46c2ff");
    drawLobe(right.x, right.y, 88 - pulse, "#46c2ff");
    ctx.strokeStyle = "rgba(255, 200, 87, 0.55)";
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 10]);
    ctx.beginPath();
    ctx.moveTo(left.x + 75, left.y);
    ctx.lineTo(right.x - 75, right.y);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  if (settings.particles) {
    for (let i = 0; i < settings.rate; i += 1) {
      if (Math.random() < 0.08) {
        const center = Math.random() < 0.5 ? left : right;
        state.hits.push({
          x: center.x + randomNormal() * 36,
          y: center.y + randomNormal() * 30,
          r: 2,
          alpha: 0.75,
        });
      }
    }
    if (state.hits.length > 400) state.hits.splice(0, state.hits.length - 400);
    drawHits();
  }
  drawText("one state, two separated places to detect it", 24, 30, "#ffc857");
}

function drawLobe(x, y, radius, color) {
  const gradient = ctx.createRadialGradient(x, y, 8, x, y, radius);
  gradient.addColorStop(0, `${color}cc`);
  gradient.addColorStop(1, `${color}00`);
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.ellipse(x, y, radius * 1.25, radius * 0.72, 0, 0, Math.PI * 2);
  ctx.fill();
}

function drawPacket(settings) {
  const { width, height } = view();
  const base = height * 0.62;
  const barrierX = width * 0.58;
  const packetX = width * 0.16 + ((state.t * 2.0) % (width * 0.72));
  const reflected = Math.max(0, (packetX - barrierX) / 180) * settings.barrier;
  const transmittedAlpha = Math.max(0.2, 1 - settings.barrier * 0.72);

  ctx.strokeStyle = "#73e3a4";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(barrierX, base);
  ctx.lineTo(barrierX, base - 210 * settings.barrier);
  ctx.lineTo(barrierX + 34, base - 210 * settings.barrier);
  ctx.lineTo(barrierX + 34, base);
  ctx.stroke();

  if (settings.wave) {
    drawPacketCurve(packetX, base, 1, "#46c2ff");
    if (reflected > 0) drawPacketCurve(barrierX - reflected * 115, base, 0.55 * reflected, "#ffc857");
    if (packetX > barrierX) drawPacketCurve(packetX + 56, base, transmittedAlpha, "#46c2ff");
  }

  if (settings.particles && Math.random() < settings.rate / 90) {
    const passed = packetX > barrierX && Math.random() > settings.barrier;
    state.hits.push({
      x: passed ? barrierX + 90 + Math.random() * 180 : packetX + randomNormal() * 28,
      y: base - 24 - Math.random() * 96,
      r: 2.4,
      alpha: 0.85,
    });
    if (state.hits.length > 500) state.hits.splice(0, state.hits.length - 500);
  }
  drawHits();
  drawText("barrier height controls reflection vs tunneling", 24, 30, "#ffc857");
}

function drawPacketCurve(cx, base, alpha, color) {
  const { width } = view();
  ctx.strokeStyle = color;
  ctx.globalAlpha = alpha;
  ctx.lineWidth = 3;
  ctx.beginPath();
  for (let i = 0; i < 220; i += 1) {
    const x = cx - 130 + i * (260 / 219);
    const env = Math.exp(-((x - cx) ** 2) / 2400);
    const y = base - env * (110 + Math.sin(i * 0.3 + state.t * 0.1) * 20);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = "#344154";
  ctx.beginPath();
  ctx.moveTo(0, base);
  ctx.lineTo(width, base);
  ctx.stroke();
}

function randomNormal() {
  let u = 0;
  let v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function fireParticles(count = 20) {
  if (state.mode === "double-slit") {
    for (let i = 0; i < count; i += 1) sampleDoubleHit();
  } else if (state.mode === "light") {
    for (let i = 0; i < count; i += 1) spawnPhoton();
  } else if (state.mode === "dna") {
    state.dnaStep = "translate";
    const codonCount = codonsFromMrna(transcribeDna(cleanDnaSequence())).length || 1;
    state.dnaCodonIndex = (state.dnaCodonIndex + 1) % codonCount;
  } else {
    for (let i = 0; i < count; i += 1) {
      state.hits.push({ x: 80 + Math.random() * 400, y: 80 + Math.random() * 260, r: 2, alpha: 0.7 });
    }
  }
  updateLabels();
}

async function explain() {
  const settings = getSettings();
  const params = new URLSearchParams({
    mode: state.mode,
    particles: settings.particles,
    wave: settings.wave,
    whichPath: settings.whichPath,
  });
  openExplanationModal("Thinking about the current setup...", "Preparing explanation...");
  els.aiText.textContent = "Thinking about the current setup...";
  try {
    const res = await fetch(apiUrl(`/api/explain?${params}`));
    const data = await res.json();
    const source = chatSourceLabel(data.source);
    const text = data.text || modes[state.mode].text;
    els.aiText.textContent = `${source}: ${text}`;
    setExplanationModal(text, `${source} explanation for ${modes[state.mode].title}`);
  } catch (error) {
    const text = error.message || "OpenAI explanation is unavailable right now.";
    els.aiText.textContent = `AI unavailable: ${text}`;
    setExplanationModal(text, `OpenAI unavailable for ${modes[state.mode].title}`);
  }
}

async function exampleProblem() {
  const settings = getSettings();
  const params = new URLSearchParams({
    mode: state.mode,
    particles: settings.particles,
    wave: settings.wave,
    whichPath: settings.whichPath,
    separation: settings.separation,
    wavelength: settings.wavelength,
    slitWidth: settings.slitWidth,
  });
  openExplanationModal("Generating a new practice problem with OpenAI...", "OpenAI problem generator", "Example Problem");
  els.aiText.textContent = "OpenAI is writing an example problem...";
  els.exampleProblem.disabled = true;
  try {
    const res = await fetch(apiUrl(`/api/problem?${params}`), { cache: "no-store" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "OpenAI could not create a problem.");
    const text = data.text || "OpenAI returned an empty problem. Try again.";
    els.aiText.textContent = "OpenAI generated a practice problem.";
    setExplanationModal(text, `OpenAI practice problem for ${modes[state.mode].title}`, "Example Problem");
  } catch (error) {
    const message = error.message || "OpenAI is unavailable right now.";
    els.aiText.textContent = message;
    setExplanationModal(message, "OpenAI problem generator unavailable", "Example Problem");
  } finally {
    els.exampleProblem.disabled = false;
    els.exampleProblem.focus();
  }
}

function openExplanationModal(text, source, title = modes[state.mode].title) {
  els.modalTitle.textContent = title;
  els.modalSource.textContent = source;
  els.modalText.textContent = text;
  els.explainModal.classList.remove("hidden");
  els.closeModal.focus();
}

function setExplanationModal(text, source, title = modes[state.mode].title) {
  els.modalTitle.textContent = title;
  els.modalSource.textContent = source;
  els.modalText.textContent = text;
}

function closeExplanationModal() {
  els.explainModal.classList.add("hidden");
  els.explain.focus();
}

function showPage(page) {
  const pageMap = {
    home: document.querySelector("#homePage"),
    lab: document.querySelector(".app-shell"),
    login: document.querySelector("#loginPage"),
    settings: document.querySelector("#settingsPage"),
    subscriptions: document.querySelector("#subscriptionsPage"),
  };
  Object.entries(pageMap).forEach(([key, el]) => {
    el.classList.toggle("hidden", key !== page);
  });
  if (page === "lab") resizeCanvas();
}

function applyUser(user) {
  state.user = user;
  els.accountName.textContent = user ? `${user.name} · ${user.plan}` : "Guest";
  els.loginNav.classList.toggle("hidden", Boolean(user));
  els.logoutNav.classList.toggle("hidden", !user);
  els.settingsHint.textContent = user ? `Signed in as ${user.email}` : "Login to save settings.";
  els.settingApiBase.value = API_BASE;
  if (user?.settings) {
    els.settingParticles.checked = Boolean(user.settings.particles);
    els.settingWave.checked = Boolean(user.settings.wave);
    els.settingTheme.value = user.settings.theme || "dark";
    els.showParticles.checked = Boolean(user.settings.particles);
    els.showWave.checked = Boolean(user.settings.wave);
  }
}

async function refreshUser() {
  try {
    const res = await fetch(apiUrl("/api/me"), { cache: "no-store" });
    const data = await res.json();
    applyUser(data.user);
  } catch {
    applyUser(null);
  }
}

async function authRequest(path, payload) {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed.");
  return data;
}

async function loginOrSignup(kind) {
  els.authMessage.textContent = "Working...";
  try {
    const data = await authRequest(kind === "login" ? "/api/login" : "/api/signup", {
      name: els.authName.value,
      email: els.authEmail.value,
      password: els.authPassword.value,
    });
    applyUser(data.user);
    els.authPassword.value = "";
    els.authMessage.textContent = kind === "login" ? "Logged in." : "Account created.";
    showPage("lab");
  } catch (error) {
    els.authMessage.textContent = error.message;
  }
}

async function logout() {
  await authRequest("/api/logout", {});
  applyUser(null);
  showPage("home");
}

async function saveSettings(event) {
  event.preventDefault();
  els.settingsMessage.textContent = "Saving...";
  const nextApiBase = els.settingApiBase.value.trim().replace(/\/$/, "");
  if (nextApiBase) localStorage.setItem("quantumApiBase", nextApiBase);
  else localStorage.removeItem("quantumApiBase");
  if (nextApiBase !== API_BASE) {
    els.settingsMessage.textContent = "Backend URL saved. Reload the page to connect.";
    return;
  }
  try {
    const data = await authRequest("/api/settings", {
      settings: {
        particles: els.settingParticles.checked,
        wave: els.settingWave.checked,
        theme: els.settingTheme.value,
      },
    });
    applyUser(data.user);
    els.settingsMessage.textContent = nextApiBase !== API_BASE
      ? "Settings saved. Reload the page to use the backend URL."
      : "Settings saved.";
  } catch (error) {
    els.settingsMessage.textContent = error.message;
  }
}

async function choosePlan(plan) {
  els.planMessage.textContent = "Updating plan...";
  try {
    const data = await authRequest("/api/subscription", { plan });
    applyUser(data.user);
    els.planMessage.textContent = data.message || "Plan updated.";
  } catch (error) {
    els.planMessage.textContent = error.message;
    if (error.message.includes("Login")) showPage("login");
  }
}

function addChatMessage(role, content) {
  const message = document.createElement("div");
  message.className = `chat-message ${role}`;
  const hasCode = isCodeAnswer(content);
  if (hasCode) message.classList.add("has-code");
  const text = document.createElement("div");
  text.className = "chat-message-text";
  text.textContent = content;
  message.dataset.copyText = hasCode ? extractCode(content) : content;
  message.appendChild(text);
  if (role === "assistant" && hasCode) ensureCopyButton(message);
  els.chatMessages.appendChild(message);
  els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
  return message;
}

function addVisualMessage(visual) {
  const message = document.createElement("div");
  message.className = "chat-message assistant visual-message";

  const title = document.createElement("h3");
  title.textContent = visual.title || "AI Visual";
  message.appendChild(title);

  const frame = document.createElement("div");
  frame.className = "visual-frame";
  frame.innerHTML = visual.svg || "";
  message.appendChild(frame);

  if (visual.caption) {
    const caption = document.createElement("p");
    caption.className = "visual-caption";
    caption.textContent = visual.caption;
    message.appendChild(caption);
  }

  if (visual.explanation && visual.explanation !== visual.caption) {
    const explanation = document.createElement("p");
    explanation.className = "visual-explanation";
    explanation.textContent = visual.explanation;
    message.appendChild(explanation);
  }

  els.chatMessages.appendChild(message);
  els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
  return message;
}

function isCodeAnswer(content) {
  return content.includes("```");
}

function extractCode(content) {
  const match = content.match(/```(?:[a-zA-Z0-9_+-]+)?\n([\s\S]*?)```/);
  return match ? match[1].trimEnd() : content;
}

function ensureCopyButton(message) {
  if (message.querySelector(".copy-message")) return;
  const copyButton = document.createElement("button");
  copyButton.className = "copy-message";
  copyButton.type = "button";
  copyButton.textContent = "Copy";
  copyButton.addEventListener("click", () => copyChatMessage(message, copyButton));
  message.appendChild(copyButton);
}

async function copyChatMessage(message, button) {
  const text = message.dataset.copyText || "";
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied";
    setTimeout(() => {
      button.textContent = "Copy";
    }, 1400);
  } catch {
    button.textContent = "Copy failed";
    setTimeout(() => {
      button.textContent = "Copy";
    }, 1600);
  }
}

function updateChatMessage(message, content) {
  const text = message.querySelector(".chat-message-text");
  if (text) text.textContent = content;
  message.classList.remove("thinking");
  const hasCode = isCodeAnswer(content);
  message.dataset.copyText = hasCode ? extractCode(content) : content;
  message.classList.toggle("has-code", hasCode);
  if (hasCode && message.classList.contains("assistant")) {
    ensureCopyButton(message);
  } else {
    message.querySelector(".copy-message")?.remove();
  }
}

function updatePhotoPreview() {
  if (!state.attachedImage) {
    els.photoPreview.classList.add("hidden");
    els.photoPreview.textContent = "";
    els.removePhoto.classList.add("hidden");
    return;
  }
  const sizeKb = Math.max(1, Math.round(state.attachedImage.size / 1024));
  els.photoPreview.classList.remove("hidden");
  els.photoPreview.textContent = `${state.attachedImage.name} attached (${sizeKb} KB)`;
  els.removePhoto.classList.remove("hidden");
}

function clearAttachedPhoto() {
  state.attachedImage = null;
  els.photoInput.value = "";
  updatePhotoPreview();
}

function handlePhotoSelect() {
  const file = els.photoInput.files?.[0];
  if (!file) return;
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
    addChatMessage("system", "Use a PNG, JPG, or WEBP image for homework photos.");
    clearAttachedPhoto();
    return;
  }
  if (file.size > MAX_HOMEWORK_IMAGE_BYTES) {
    addChatMessage("system", "That image is too large. Use a photo under 3 MB.");
    clearAttachedPhoto();
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    state.attachedImage = {
      name: file.name,
      size: file.size,
      type: file.type,
      dataUrl: String(reader.result || ""),
    };
    updatePhotoPreview();
    els.chatInput.placeholder = "Ask what to solve from the photo...";
  };
  reader.onerror = () => {
    addChatMessage("system", "Could not read that photo. Try another image.");
    clearAttachedPhoto();
  };
  reader.readAsDataURL(file);
}

function localBrowserChatReply(message) {
  const lower = message.toLowerCase();
  const simulatorTerms = [
    "experiment",
    "simulation",
    "simulator",
    "mode",
    "control",
    "slider",
    "particle",
    "wave",
    "interference",
    "slit",
    "photon",
    "superposition",
    "tunnel",
    "barrier",
    "dna",
    "mrna",
    "codon",
    "transcription",
    "translation",
  ];
  const asksSimulator = simulatorTerms.some((word) => lower.includes(word)) || /\b(this|that|current)\b/.test(lower);
  if (wantsVisualRequest(message)) {
    return "OpenAI visual generation is required for visuals. Check the API key, billing, and connection, then try Generate Visual again.";
  }
  if (wantsExampleProblemRequest(message)) {
    return "Problem:\nIn the current quantum mode, describe what changes when you adjust one control, then predict what the particle detections should do.\n\nHint:\nConnect the visible wave pattern to where detections become more likely.\n\nAnswer:\nThe wave pattern represents probability. When a control changes the wave shape, the dots collect more often where that new wave pattern is strongest.";
  }
  if (lower.includes("code") || lower.includes("loop") || lower.includes("if statement") || lower.includes("data structure") || lower.includes("array") || lower.includes("list") || lower.includes("dictionary")) {
    return "OpenAI can write and format code when it is connected. Ask for a language and a task, like: write Python code that uses input(), a list, a for loop, and an if statement.";
  }
  if ((lower.includes("what") || lower.includes("explain")) && asksSimulator) {
    return modes[state.mode].text;
  }
  if (lower.includes("control") || lower.includes("slider")) {
    return "Use the sliders to change the simulation parameters. In Double Slit, separation and wavelength reshape the stripe pattern; in Wave Packet, barrier height changes reflection and tunneling.";
  }
  if (lower.includes("particle") || lower.includes("dot")) {
    return "The dots are sampled detection events. The smooth wave shows the probability pattern that guides where many detections tend to collect.";
  }
  if (lower.includes("dna") || lower.includes("mrna") || lower.includes("codon") || lower.includes("transcription") || lower.includes("translation") || state.mode === "dna") {
    return "DNA Lab transcribes the coding DNA strand into mRNA by changing T to U. Translation reads the mRNA three bases at a time, turning codons like AUG into amino acids like Met until a stop codon ends the chain.";
  }
  return "OpenAI is needed for a full answer about a separate topic. The current experiment should not control that answer; check the API key or connection and ask again.";
}

function wantsVisualRequest(message) {
  const lower = message.toLowerCase();
  return (
    ["visual", "diagram", "draw", "picture", "image", "illustration", "graph", "plot"].some((word) => lower.includes(word))
    || /\by\s*=/.test(lower)
    || /\bf\s*\(\s*x\s*\)\s*=/.test(lower)
  );
}

function wantsExampleProblemRequest(message) {
  const lower = message.toLowerCase();
  const asksForExample = ["example", "practice", "sample"].some((word) => lower.includes(word));
  const asksForProblem = ["problem", "question", "exercise"].some((word) => lower.includes(word));
  if (!asksForExample || !asksForProblem) return false;
  return /\b(this|current|simulator|simulation|experiment|mode|double slit|wave packet|light mode|dna lab)\b/.test(lower);
}

function visualQueryParams(topic = "") {
  const requestedTopic = topic.trim();
  return new URLSearchParams({
    mode: state.mode,
    particles: String(els.showParticles.checked),
    wave: String(els.showWave.checked),
    whichPath: String(els.whichPath.checked),
    separation: els.slitSeparation.value,
    wavelength: els.wavelength.value,
    slitWidth: els.slitWidth.value,
    barrierHeight: els.barrierHeight.value,
    topic: requestedTopic,
  });
}

async function fetchAiVisual(topic = "") {
  const res = await fetch(apiUrl(`/api/visual?${visualQueryParams(topic).toString()}`), { cache: "no-store" });
  const data = await res.json();
  if (!res.ok || !data.svg) throw new Error(data.error || "OpenAI could not generate a visual.");
  return data;
}

async function generateVisual(topic = "") {
  if (state.chatWaiting) return;
  state.chatWaiting = true;
  els.generateVisual.disabled = true;
  els.chatSend.disabled = true;
  els.attachPhoto.disabled = true;
  els.chatSource.textContent = "Drawing...";
  addChatMessage("user", topic || `Generate an AI visual for ${modes[state.mode].title}.`);
  addChatMessage("assistant", "Generating visual with OpenAI...");
  const pending = els.chatMessages.lastElementChild;
  pending.classList.add("thinking");
  try {
    const visual = await fetchAiVisual(topic);
    pending.remove();
    addVisualMessage(visual);
    const sourceName = visual.source === "graph" ? "Graph" : "OpenAI";
    els.aiText.textContent = visual.source === "graph"
      ? `Generated a function graph and explanation.`
      : `OpenAI generated a visual for ${topic.trim() || modes[state.mode].title}.`;
    els.chatSource.textContent = sourceName;
  } catch (error) {
    updateChatMessage(pending, error.message || "OpenAI visual generation is unavailable.");
    els.chatSource.textContent = "AI unavailable";
  } finally {
    state.chatWaiting = false;
    els.generateVisual.disabled = false;
    els.chatSend.disabled = false;
    els.attachPhoto.disabled = false;
  }
}

function problemComplexity(message) {
  const lower = message.toLowerCase();
  return ["complex", "advanced", "hard", "multi-step", "multistep"].some((word) => lower.includes(word)) ? "complex" : "beginner";
}

async function fetchProblemForChat(message) {
  const query = new URLSearchParams({
    mode: state.mode,
    particles: String(els.showParticles.checked),
    wave: String(els.showWave.checked),
    whichPath: String(els.whichPath.checked),
    separation: els.slitSeparation.value,
    wavelength: els.wavelength.value,
    slitWidth: els.slitWidth.value,
    complexity: problemComplexity(message),
    topic: message,
  });
  const res = await fetch(apiUrl(`/api/problem?${query.toString()}`), { cache: "no-store" });
  const data = await res.json();
  if (!res.ok || data.error) throw new Error(data.error || "Could not create an example problem.");
  return {
    reply: data.text || data.error || localBrowserChatReply(message),
    source: data.source || "local",
    note: data.note || "",
  };
}

function chatSourceLabel(source) {
  if (source === "openai") return "OpenAI";
  if (source === "openai-error") return "OpenAI error";
  if (source === "graph") return "Graph";
  if (source === "local") return "Local";
  return source || "Ready";
}

function resizeChatInput() {
  els.chatInput.style.height = "auto";
  els.chatInput.style.height = `${Math.min(els.chatInput.scrollHeight, 130)}px`;
}

function resetChatInput() {
  els.chatInput.value = "";
  resizeChatInput();
}

function handleChatInputKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    els.chatForm.requestSubmit();
  }
}

async function sendChatMessage(event) {
  event.preventDefault();
  if (state.chatWaiting) return;
  const attachedImage = state.attachedImage;
  const typedMessage = els.chatInput.value.trim();
  const message = typedMessage || (attachedImage ? "Solve this physics or calculus homework problem step by step." : "");
  if (!message && !attachedImage) {
    els.chatInput.focus();
    return;
  }

  resetChatInput();
  if (attachedImage) clearAttachedPhoto();
  addChatMessage("user", attachedImage ? `${message}\n[Photo attached: ${attachedImage.name}]` : message);
  state.chatHistory.push({ role: "user", content: message });
  state.chatWaiting = true;
  els.chatSend.disabled = true;
  els.attachPhoto.disabled = true;
  els.generateVisual.disabled = true;
  els.chatSource.textContent = "Thinking...";
  addChatMessage("assistant", attachedImage ? "Reading the photo and solving..." : "Thinking...");
  const pending = els.chatMessages.lastElementChild;
  pending.classList.add("thinking");

  try {
    if (!attachedImage && wantsVisualRequest(message)) {
      const visual = await fetchAiVisual(message);
      pending.remove();
      addVisualMessage(visual);
      state.chatHistory.push({ role: "assistant", content: `[AI visual generated: ${visual.title || "Physics Visual"}]` });
      els.chatSource.textContent = visual.source === "graph" ? "Graph" : "OpenAI";
      return;
    }

    if (!attachedImage && wantsExampleProblemRequest(message)) {
      const problem = await fetchProblemForChat(message);
      updateChatMessage(pending, problem.reply);
      state.chatHistory.push({ role: "assistant", content: problem.reply });
      els.chatSource.textContent = chatSourceLabel(problem.source);
      return;
    }

    const res = await fetch(apiUrl("/api/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        mode: state.mode,
        settings: getSettings(),
        history: state.chatHistory.slice(-8),
        image: attachedImage
          ? {
              name: attachedImage.name,
              type: attachedImage.type,
              dataUrl: attachedImage.dataUrl,
            }
          : null,
      }),
    });
    const data = await res.json();
    const reply = data.reply || localBrowserChatReply(message);
    updateChatMessage(pending, reply);
    state.chatHistory.push({ role: "assistant", content: reply });
    els.chatSource.textContent = chatSourceLabel(data.source);
    if (data.note) addChatMessage("system", data.note);
  } catch (error) {
    if (wantsVisualRequest(message)) {
      updateChatMessage(pending, error.message || "OpenAI visual generation is unavailable.");
      state.chatHistory.push({ role: "assistant", content: "OpenAI visual generation is unavailable." });
      els.chatSource.textContent = "AI unavailable";
      return;
    }
    const reply = error.message || "OpenAI is unavailable right now. No local fallback was used.";
    updateChatMessage(pending, reply);
    state.chatHistory.push({ role: "assistant", content: reply });
    els.chatSource.textContent = "AI unavailable";
  } finally {
    state.chatHistory = state.chatHistory.slice(-10);
    state.chatWaiting = false;
    els.chatSend.disabled = false;
    els.attachPhoto.disabled = false;
    els.generateVisual.disabled = false;
    els.chatInput.focus();
  }
}

async function tick() {
  const settings = getSettings();
  updateLabels();
  if (!state.paused) state.t += 1;
  if (state.mode === "double-slit") await updateDoublePattern();

  if (!state.paused && settings.particles) {
    if (state.mode === "double-slit") {
      for (let i = 0; i < settings.rate; i += 1) {
        if (Math.random() < 0.2) sampleDoubleHit();
      }
    } else if (state.mode === "light") {
      for (let i = 0; i < settings.rate; i += 1) {
        if (Math.random() < 0.04) spawnPhoton();
      }
    }
  }

  clear();
  if (state.mode === "double-slit") drawDoubleSlit(settings);
  else if (state.mode === "light") drawLight(settings);
  else if (state.mode === "two-places") drawTwoPlaces(settings);
  else if (state.mode === "dna") drawDnaLab();
  else drawPacket(settings);

  requestAnimationFrame(tick);
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});

document.querySelectorAll("[data-page]").forEach((button) => {
  button.addEventListener("click", () => showPage(button.dataset.page));
});

[
  els.showParticles,
  els.showWave,
  els.whichPath,
  els.slitSeparation,
  els.wavelength,
  els.slitWidth,
  els.particleRate,
  els.barrierHeight,
].forEach((input) => {
  input.addEventListener("input", () => {
    if (input === els.whichPath || input === els.slitSeparation || input === els.wavelength || input === els.slitWidth) {
      state.lastPatternKey = "";
      state.hits = [];
    }
    updateLabels();
  });
});

els.playPause.addEventListener("click", () => {
  state.paused = !state.paused;
  updateLabels();
});
els.reset.addEventListener("click", reset);
els.fire.addEventListener("click", () => fireParticles(20));
els.explain.addEventListener("click", explain);
els.exampleProblem.addEventListener("click", exampleProblem);
els.generateVisual.addEventListener("click", () => generateVisual());
els.dnaInput.addEventListener("input", () => {
  state.dnaMutatedIndex = -1;
  state.dnaMutation = null;
  state.dnaMutations = [];
  updateDnaOutputs();
});
els.transcribeDna.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
  setDnaStep("transcribe");
});
els.translateDna.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
  setDnaStep("translate");
});
els.mutateDna.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
  mutateDnaSequence();
});
els.substituteDna.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
  applyDnaMutation("substitution", { random: true, useSelection: false });
});
els.insertDna.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
  applyDnaMutation("insertion", { random: true, useSelection: false });
});
els.deleteDna.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
  applyDnaMutation("deletion", { random: true, useSelection: false });
});
els.restoreDna.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
  restoreDnaSequence();
});
els.analyzeDna.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation?.();
  analyzeDnaWithAi();
});
canvas.addEventListener("mousemove", handleCanvasPointerMove);
canvas.addEventListener("mouseleave", () => setDnaHover(null));
canvas.addEventListener("click", handleCanvasClick);
els.attachPhoto.addEventListener("click", () => els.photoInput.click());
els.photoInput.addEventListener("change", handlePhotoSelect);
els.removePhoto.addEventListener("click", clearAttachedPhoto);
els.chatInput.addEventListener("input", resizeChatInput);
els.chatInput.addEventListener("keydown", handleChatInputKeydown);
els.chatForm.addEventListener("submit", sendChatMessage);
els.loginSubmit.addEventListener("click", () => loginOrSignup("login"));
els.signupSubmit.addEventListener("click", () => loginOrSignup("signup"));
els.authForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loginOrSignup("login");
});
els.logoutNav.addEventListener("click", logout);
els.settingsForm.addEventListener("submit", saveSettings);
document.querySelectorAll(".plan-button").forEach((button) => {
  button.addEventListener("click", () => choosePlan(button.dataset.plan));
});
els.closeModal.addEventListener("click", closeExplanationModal);
els.explainModal.addEventListener("click", (event) => {
  if (event.target === els.explainModal) closeExplanationModal();
});
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.explainModal.classList.contains("hidden")) {
    closeExplanationModal();
  }
});
window.addEventListener("resize", resizeCanvas);

resizeCanvas();
Promise.all([checkBackend(), refreshUser()]).then(() => {
  resizeChatInput();
  reset();
  showPage("home");
  els.aiText.textContent = "Click Explain This for a plain-English read on the current setup.";
  addChatMessage("assistant", "Hi. Ask me about the active quantum experiment or any control on the screen.");
  requestAnimationFrame(tick);
});
