const samples = {
  orbit: {
    file: "orbit.manim",
    label: "ORBIT",
    caption: "circular path / r = 3",
    source: `OBJECTS:
    earth: { object: { type: "circle",
        radius: 1, color: BLUE } }
    moon: { object: { type: "dot",
        radius: 0.2, color: GOLD } }

SCENE "Orbit":
    PLACE earth AT (0, 0);
    PLACE moon AT (3, 0);
    CIRCULATE moon AROUND earth
        RADIUS 3 OMEGA 1 FOR 6;`
  },
  transform: {
    file: "transform.manim",
    label: "TRANSFORM",
    caption: "morph / source → target",
    source: `OBJECTS:
    square: { object: { type: "square",
        side_length: 2, color: BLUE } }
    circle: { object: { type: "circle",
        radius: 1.2, color: CYAN } }

SCENE "Morph":
    PLACE square AT (0, 0);
    TRANSFORM square TO circle
        FOR 2;`
  },
  voice: {
    file: "voiceover.manim",
    label: "VOICE-OVER",
    caption: "audio / gTTS + scene timeline",
    source: `OBJECTS:
    dot: { object: { type: "dot",
        radius: 0.25, color: CYAN } }

SCENE "Narrated":
    PLACE dot AT (-3, 0);
    SPEAK "Let's animate this" DO:
        MOVE dot TO (3, 0) FOR 2;`
  }
};

const code = document.querySelector("#demo-code");
const stage = document.querySelector("#preview-stage");
const runButton = document.querySelector("#run-preview");
const tabs = [...document.querySelectorAll(".demo-tab")];
let activeSample = "orbit";
let runTimer;

function escapeHTML(value) {
  return value.replace(/[&<>"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"
  })[char]);
}

function colorize(value) {
  return escapeHTML(value)
    .replace(/("[^"]*")/g, '<span class="syntax-string">$1</span>')
    .replace(/\b(OBJECTS|SCENE|PLACE|AT|FADE_IN|FADE_OUT|FOR|WAIT|MOVE|TOWARD|CIRCULATE|AROUND|RADIUS|OMEGA|SPEAK|DO|ROTATE|BY|TRANSFORM|TO|RATE|LINEAR)\b/g, '<span class="syntax-keyword">$1</span>')
    .replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="syntax-number">$1</span>');
}

function selectSample(name) {
  const sample = samples[name];
  if (!sample) return;
  activeSample = name;
  stage.dataset.demo = name;
  stage.classList.remove("running");
  document.querySelector("#demo-filename").textContent = sample.file;
  document.querySelector("#preview-name").textContent = sample.label;
  document.querySelector("#preview-caption").textContent = sample.caption;
  code.innerHTML = colorize(sample.source);
  tabs.forEach((tab) => {
    const active = tab.dataset.demo === name;
    tab.classList.toggle("selected", active);
    tab.setAttribute("aria-selected", String(active));
  });
  document.querySelector("#run-status").textContent = "READY · 0 ERRORS";
  runButton.innerHTML = "<span>▶</span> RUN PREVIEW";
}

tabs.forEach((tab) => tab.addEventListener("click", () => selectSample(tab.dataset.demo)));

runButton.addEventListener("click", () => {
  window.clearTimeout(runTimer);
  stage.classList.remove("running");
  void stage.offsetWidth;
  stage.classList.add("running");
  document.querySelector("#run-status").textContent = "RUNNING · 24 FPS";
  runButton.innerHTML = "<span>↻</span> RE-RUN";
  runTimer = window.setTimeout(() => {
    document.querySelector("#run-status").textContent = "COMPLETE · 0 ERRORS";
  }, 2600);
});

document.querySelector("#copy-code").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText(samples[activeSample].source);
    button.innerHTML = "COPIED <b>✓</b>";
  } catch {
    const range = document.createRange();
    range.selectNodeContents(code);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    button.innerHTML = "SELECTED <b>✓</b>";
  }
  window.setTimeout(() => {
    button.innerHTML = "COPY SOURCE <b>⧉</b>";
  }, 1600);
});

const compileSteps = [...document.querySelectorAll(".track-step")];
if ("IntersectionObserver" in window) {
  const stepObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in-view");
      }
    });
  }, { threshold: 0.35 });
  compileSteps.forEach((step) => stepObserver.observe(step));
}

const progress = document.querySelector("#scroll-progress");
function updateProgress() {
  const range = document.documentElement.scrollHeight - window.innerHeight;
  progress.style.width = `${range > 0 ? (window.scrollY / range) * 100 : 0}%`;
}
window.addEventListener("scroll", updateProgress, { passive: true });
window.addEventListener("resize", updateProgress);
updateProgress();

const menuButton = document.querySelector("#menu-button");
const navigation = document.querySelector("#site-nav");
menuButton.addEventListener("click", () => {
  const open = menuButton.getAttribute("aria-expanded") !== "true";
  menuButton.setAttribute("aria-expanded", String(open));
  menuButton.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  menuButton.textContent = open ? "×" : "☰";
  navigation.classList.toggle("open", open);
});
navigation.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    navigation.classList.remove("open");
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "Open menu");
    menuButton.textContent = "☰";
  });
});

document.querySelector("#copy-command").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText("python source.py examples/orbit.manim -o orbit.py");
    button.textContent = "✓";
  } catch {
    button.textContent = "$";
  }
  window.setTimeout(() => { button.textContent = "⧉"; }, 1600);
});

selectSample("orbit");
