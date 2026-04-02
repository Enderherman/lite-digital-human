const SAMPLE_SCRIPTS = [
  "大家好，欢迎来到本地数字人 Demo。我们先把文本、语音和视频预览跑通，下一步再接入 MuseTalk 和 CosyVoice。",
  "今天先展示一个可运行的最小闭环：输入文案，生成语音，再输出一个可预览的视频文件。",
  "后续我们会把 ASR、商品话术和直播推流逐步补进来，但第一步先把链路稳定住。"
];

const els = {
  input: document.getElementById("script-input"),
  speakBtn: document.getElementById("speak-btn"),
  stopBtn: document.getElementById("stop-btn"),
  jobsList: document.getElementById("jobs-list"),
  metricsGrid: document.getElementById("metrics-grid"),
  previewVideo: document.getElementById("preview-video"),
  videoEmpty: document.getElementById("video-empty"),
  stageList: document.getElementById("stage-list"),
  sampleRow: document.getElementById("sample-row"),
  clock: document.getElementById("clock"),
  connectionState: document.getElementById("connection-state"),
};

const appState = {
  currentJobId: "",
  pollTimer: null,
  jobs: [],
  metrics: null,
};

function formatMs(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  const n = Number(value);
  if (!Number.isFinite(n)) {
    return "-";
  }
  if (n >= 1000) {
    return `${(n / 1000).toFixed(2)} s`;
  }
  return `${n.toFixed(0)} ms`;
}

function formatTime(iso) {
  if (!iso) {
    return "-";
  }
  return iso.replace("T", " ");
}

function stageStates(job) {
  if (!job) {
    return [
      ["输入脚本", "ready"],
      ["TTS 生成", "idle"],
      ["口型合成", "idle"],
      ["预览输出", "idle"],
    ];
  }
  if (job.status === "queued") {
    return [
      ["输入脚本", "done"],
      ["TTS 生成", "queued"],
      ["口型合成", "queued"],
      ["预览输出", "queued"],
    ];
  }
  if (job.status === "running") {
    return [
      ["输入脚本", "done"],
      ["TTS 生成", "running"],
      ["口型合成", "running"],
      ["预览输出", "running"],
    ];
  }
  if (job.status === "succeeded") {
    return [
      ["输入脚本", "done"],
      ["TTS 生成", "done"],
      ["口型合成", "done"],
      ["预览输出", "done"],
    ];
  }
  return [
    ["输入脚本", "done"],
    ["TTS 生成", job.status],
    ["口型合成", job.status],
    ["预览输出", job.status],
  ];
}

function renderStages(job) {
  const rows = stageStates(job).map(([name, status]) => {
    return `
      <div class="stage-item">
        <span class="stage-name">${name}</span>
        <span class="stage-status">${status}</span>
      </div>
    `;
  });
  els.stageList.innerHTML = rows.join("");
}

function metricCard(label, value) {
  return `
    <div class="metric">
      <div class="metric-label">${label}</div>
      <div class="metric-value">${value}</div>
    </div>
  `;
}

function renderMetrics(metrics) {
  if (!metrics) {
    els.metricsGrid.innerHTML = "";
    return;
  }
  els.metricsGrid.innerHTML = [
    metricCard("总任务数", metrics.total_jobs ?? 0),
    metricCard("运行中", metrics.running ?? 0),
    metricCard("平均 TTS", formatMs(metrics.average_tts_ms)),
    metricCard("平均合成", formatMs(metrics.average_render_ms)),
    metricCard("平均总耗时", formatMs(metrics.average_total_ms)),
    metricCard("活跃任务", metrics.active_job_id || "-"),
  ].join("");
}

function renderJobs(jobs) {
  if (!jobs.length) {
    els.jobsList.innerHTML = `<div class="job-item"><div>还没有任务。提交一段文案后，这里会显示最近的生成记录。</div></div>`;
    return;
  }
  els.jobsList.innerHTML = jobs
    .map((job) => {
      const isCurrent = job.job_id === appState.currentJobId;
      const badgeClass = job.status || "queued";
      return `
        <article class="job-item">
          <div>
            <div class="job-id">${job.job_id}${isCurrent ? "  ·  active" : ""}</div>
            <div class="job-meta">
              ${formatTime(job.created_at_iso)} · TTS ${formatMs(job.tts_ms)} · 合成 ${formatMs(job.render_ms)} · 总计 ${formatMs(job.total_ms)}
            </div>
            <div class="job-text">${job.text}</div>
          </div>
          <div class="badge ${badgeClass}">${job.status}</div>
        </article>
      `;
    })
    .join("");
}

function setPreview(job) {
  if (!job || job.status !== "succeeded") {
    els.previewVideo.removeAttribute("src");
    els.previewVideo.load();
    els.videoEmpty.style.display = "grid";
    return;
  }
  const cacheBuster = `t=${Date.now()}`;
  els.previewVideo.src = `${job.video_url}?${cacheBuster}`;
  els.previewVideo.load();
  els.videoEmpty.style.display = "none";
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.detail || `Request failed: ${response.status}`);
  }
  return data;
}

async function refreshJob(jobId) {
  if (!jobId) {
    return null;
  }
  const job = await fetchJson(`/api/status?job_id=${encodeURIComponent(jobId)}`);
  appState.currentJobId = job.job_id;
  renderStages(job);
  setPreview(job);
  return job;
}

async function refreshDashboard() {
  const [metrics, jobs] = await Promise.all([
    fetchJson("/api/metrics"),
    fetchJson("/api/jobs?limit=10"),
  ]);
  appState.metrics = metrics;
  appState.jobs = jobs.jobs || [];
  renderMetrics(metrics);
  renderJobs(appState.jobs);
  const active = appState.jobs.find((job) => job.status === "running" || job.status === "queued");
  if (active) {
    appState.currentJobId = active.job_id;
    renderStages(active);
  } else if (appState.jobs[0]) {
    renderStages(appState.jobs[0]);
  } else {
    renderStages(null);
  }
  if (appState.currentJobId) {
    const job = appState.jobs.find((item) => item.job_id === appState.currentJobId);
    if (job) {
      setPreview(job);
    }
  }
}

async function submitSpeak() {
  const text = els.input.value.trim();
  if (!text) {
    window.alert("请输入一段口播文本。");
    return;
  }
  els.speakBtn.disabled = true;
  els.speakBtn.textContent = "生成中...";
  try {
    const result = await fetchJson("/api/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    appState.currentJobId = result.job.job_id;
    await refreshDashboard();
    await refreshJob(appState.currentJobId);
    startPolling();
  } catch (error) {
    window.alert(error.message);
  } finally {
    els.speakBtn.disabled = false;
    els.speakBtn.textContent = "开始播报";
  }
}

async function stopCurrent() {
  try {
    const payload = appState.currentJobId ? { job_id: appState.currentJobId } : {};
    await fetchJson("/api/stop", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await refreshDashboard();
  } catch (error) {
    window.alert(error.message);
  }
}

function startPolling() {
  if (appState.pollTimer) {
    clearInterval(appState.pollTimer);
  }
  appState.pollTimer = window.setInterval(async () => {
    try {
      const job = appState.currentJobId ? await refreshJob(appState.currentJobId) : null;
      await refreshDashboard();
      if (job && ["succeeded", "failed", "cancelled"].includes(job.status)) {
        clearInterval(appState.pollTimer);
        appState.pollTimer = null;
      }
    } catch (error) {
      console.warn(error);
    }
  }, 1000);
}

function renderSamples() {
  els.sampleRow.innerHTML = SAMPLE_SCRIPTS.map((text, index) => {
    return `<button class="sample-chip" data-sample-index="${index}">${text.slice(0, 16)}...</button>`;
  }).join("");
  els.sampleRow.querySelectorAll("[data-sample-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.sampleIndex);
      els.input.value = SAMPLE_SCRIPTS[index];
    });
  });
}

function renderClock() {
  const now = new Date();
  els.clock.textContent = now.toLocaleString("zh-CN", {
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function wireEvents() {
  els.speakBtn.addEventListener("click", submitSpeak);
  els.stopBtn.addEventListener("click", stopCurrent);
}

async function boot() {
  renderSamples();
  wireEvents();
  els.input.value = SAMPLE_SCRIPTS[0];
  renderStages(null);
  renderClock();
  setInterval(renderClock, 1000);
  try {
    await refreshDashboard();
    els.connectionState.textContent = "LOCAL SERVER READY";
  } catch (error) {
    els.connectionState.textContent = "OFFLINE";
    console.warn(error);
  }
}

boot();
