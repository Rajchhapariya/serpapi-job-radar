document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const apiStatusPill = document.getElementById("apiStatusPill");
  const apiStatusText = document.getElementById("apiStatusText");
  const searchForm = document.getElementById("searchForm");
  const searchBtn = document.getElementById("searchBtn");
  const searchBtnText = document.getElementById("searchBtnText");
  const searchNotification = document.getElementById("searchNotification");

  // Metrics elements
  const statTotalJobs = document.getElementById("statTotalJobs");
  const statRemoteJobs = document.getElementById("statRemoteJobs");
  const statRemotePercent = document.getElementById("statRemotePercent");
  const statSalaryJobs = document.getElementById("statSalaryJobs");
  const statSalaryPercent = document.getElementById("statSalaryPercent");
  const statLatency = document.getElementById("statLatency");

  // Analytics elements
  const skillsChart = document.getElementById("skillsChart");
  const platformsList = document.getElementById("platformsList");
  const companiesList = document.getElementById("companiesList");

  // Jobs elements
  const jobsContainer = document.getElementById("jobsContainer");
  const filterKeyword = document.getElementById("filterKeyword");
  const filterWorkType = document.getElementById("filterWorkType");
  const filterSort = document.getElementById("filterSort");

  // Resume Matcher elements
  const resumeInput = document.getElementById("resumeInput");
  const matchBtn = document.getElementById("matchBtn");
  const matcherResults = document.getElementById("matcherResults");

  // Drawer elements
  const jobDetailDrawer = document.getElementById("jobDetailDrawer");
  const drawerBackdrop = document.getElementById("drawerBackdrop");
  const closeDrawerBtn = document.getElementById("closeDrawerBtn");
  const drawerJobTitle = document.getElementById("drawerJobTitle");
  const drawerJobCompany = document.getElementById("drawerJobCompany");
  const drawerBadges = document.getElementById("drawerBadges");
  const drawerLocation = document.getElementById("drawerLocation");
  const drawerSalary = document.getElementById("drawerSalary");
  const drawerSalaryWrap = document.getElementById("drawerSalaryWrap");
  const drawerDescription = document.getElementById("drawerDescription");
  const drawerApplyBtn = document.getElementById("drawerApplyBtn");

  // Radar Canvas Elements
  const mainRadarCanvas = document.getElementById("mainRadarCanvas");
  const headerRadarCanvas = document.getElementById("headerRadarCanvas");

  // Cache of currently fetched jobs for instant drawer lookups
  let cachedJobs = [];

  // Initialize
  initRadarAnimation();
  initSpotlightPhysics();
  initPresetChips();
  initDrawerControls();
  checkHealth();
  refreshDashboard();

  // 1. Sonar Radar Animation Engine (60 FPS)
  function initRadarAnimation() {
    if (!mainRadarCanvas || !headerRadarCanvas) return;

    const ctxMain = mainRadarCanvas.getContext("2d");
    const ctxMini = headerRadarCanvas.getContext("2d");

    let angle = 0;
    const blips = [
      { r: 45, theta: 0.8, alpha: 0 },
      { r: 75, theta: 2.1, alpha: 0 },
      { r: 90, theta: 4.2, alpha: 0 },
      { r: 60, theta: 5.4, alpha: 0 },
    ];

    function draw() {
      // Main Radar
      const w = mainRadarCanvas.width;
      const h = mainRadarCanvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const maxR = cx - 12;

      ctxMain.clearRect(0, 0, w, h);

      // Concentric rings
      ctxMain.strokeStyle = "rgba(14, 165, 233, 0.15)";
      ctxMain.lineWidth = 1;
      for (let r = 25; r <= maxR; r += 26) {
        ctxMain.beginPath();
        ctxMain.arc(cx, cy, r, 0, Math.PI * 2);
        ctxMain.stroke();
      }

      // Crosshairs
      ctxMain.beginPath();
      ctxMain.moveTo(cx - maxR, cy);
      ctxMain.lineTo(cx + maxR, cy);
      ctxMain.moveTo(cx, cy - maxR);
      ctxMain.lineTo(cx, cy + maxR);
      ctxMain.stroke();

      // Sweeping Sector
      ctxMain.save();
      ctxMain.translate(cx, cy);
      ctxMain.rotate(angle);

      const grad = ctxMain.createRadialGradient(0, 0, 0, 0, 0, maxR);
      grad.addColorStop(0, "rgba(56, 189, 248, 0.4)");
      grad.addColorStop(1, "rgba(14, 165, 233, 0)");

      ctxMain.fillStyle = grad;
      ctxMain.beginPath();
      ctxMain.moveTo(0, 0);
      ctxMain.arc(0, 0, maxR, -0.4, 0);
      ctxMain.closePath();
      ctxMain.fill();

      // Sweep Leading Line
      ctxMain.strokeStyle = "#38bdf8";
      ctxMain.lineWidth = 1.5;
      ctxMain.beginPath();
      ctxMain.moveTo(0, 0);
      ctxMain.lineTo(maxR, 0);
      ctxMain.stroke();
      ctxMain.restore();

      // Blip Detection
      blips.forEach((b) => {
        const diff = Math.abs((angle % (Math.PI * 2)) - b.theta);
        if (diff < 0.1) b.alpha = 1.0;
        if (b.alpha > 0.02) {
          const bx = cx + Math.cos(b.theta) * b.r;
          const by = cy + Math.sin(b.theta) * b.r;
          ctxMain.fillStyle = `rgba(56, 189, 248, ${b.alpha})`;
          ctxMain.beginPath();
          ctxMain.arc(bx, by, 3, 0, Math.PI * 2);
          ctxMain.fill();
          b.alpha *= 0.96;
        }
      });

      // Mini Header Radar
      const mw = headerRadarCanvas.width;
      const mh = headerRadarCanvas.height;
      const mcx = mw / 2;
      const mcy = mh / 2;

      ctxMini.clearRect(0, 0, mw, mh);
      ctxMini.strokeStyle = "rgba(56, 189, 248, 0.25)";
      ctxMini.lineWidth = 1;
      ctxMini.beginPath();
      ctxMini.arc(mcx, mcy, 12, 0, Math.PI * 2);
      ctxMini.stroke();

      ctxMini.save();
      ctxMini.translate(mcx, mcy);
      ctxMini.rotate(angle);
      ctxMini.strokeStyle = "#38bdf8";
      ctxMini.lineWidth = 1.2;
      ctxMini.beginPath();
      ctxMini.moveTo(0, 0);
      ctxMini.lineTo(12, 0);
      ctxMini.stroke();
      ctxMini.restore();

      angle += 0.038;
      requestAnimationFrame(draw);
    }

    draw();
  }

  // 2. Interactive Spotlight Physics (Vector Coordinates)
  function initSpotlightPhysics() {
    const cards = document.querySelectorAll(".spotlight-card");
    cards.forEach((card) => {
      card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty("--mouse-x", `${x}px`);
        card.style.setProperty("--mouse-y", `${y}px`);
      });
    });
  }

  // 3. Quick Query Preset Chips
  function initPresetChips() {
    const chips = document.querySelectorAll(".preset-chip");
    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const q = chip.getAttribute("data-query");
        const loc = chip.getAttribute("data-location");
        document.getElementById("queryInput").value = q;
        document.getElementById("locationInput").value = loc;
        searchForm.dispatchEvent(new Event("submit"));
      });
    });
  }

  // 4. Slide-Over Drawer Controls
  function initDrawerControls() {
    closeDrawerBtn.addEventListener("click", closeDrawer);
    drawerBackdrop.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && jobDetailDrawer.classList.contains("is-open")) {
        closeDrawer();
      }
    });
  }

  function openDrawer(job) {
    drawerJobTitle.textContent = job.title;
    drawerJobCompany.textContent = job.company_name;

    const isRemote =
      job.work_from_home ||
      (job.location && job.location.toLowerCase().includes("remote"));
    drawerBadges.innerHTML = `
      ${isRemote ? '<span class="badge badge-remote">REMOTE</span>' : '<span class="badge">ON-SITE</span>'}
      <span class="badge">${escapeHtml(job.via || "Direct Portal")}</span>
      <span class="badge">${escapeHtml(job.schedule_type || "Full-time")}</span>
    `;

    drawerLocation.textContent = job.location || "Location Not Disclosed";

    if (job.salary) {
      drawerSalaryWrap.style.display = "flex";
      drawerSalary.textContent = job.salary;
    } else {
      drawerSalaryWrap.style.display = "none";
    }

    drawerDescription.textContent =
      job.description || "Full job specification available on official portal.";

    if (job.apply_link) {
      drawerApplyBtn.href = job.apply_link;
      drawerApplyBtn.style.display = "inline-flex";
    } else {
      drawerApplyBtn.style.display = "none";
    }

    jobDetailDrawer.classList.add("is-open");
    jobDetailDrawer.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    jobDetailDrawer.classList.remove("is-open");
    jobDetailDrawer.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  // 5. Health Check
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      const dot = apiStatusPill.querySelector(".status-indicator");

      if (data.serpapi_configured) {
        apiStatusText.textContent = "SERPAPI: LIVE";
        dot.className = "status-indicator";
      } else {
        apiStatusText.textContent = "SERPAPI: DEMO CORPUS";
        dot.className = "status-indicator warning";
      }
    } catch (e) {
      apiStatusText.textContent = "BACKEND: OFFLINE";
    }
  }

  // 6. Search Form Submission
  searchForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = document.getElementById("queryInput").value.trim();
    const location = document.getElementById("locationInput").value;
    const num_results = parseInt(
      document.getElementById("resultsLimit").value,
      10,
    );

    if (!query) return;

    searchBtn.disabled = true;
    searchBtnText.textContent = "Scanning SerpApi...";
    searchNotification.style.display = "none";

    const t0 = performance.now();
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, location, num_results }),
      });
      const data = await res.json();
      const elapsed = Math.round(performance.now() - t0);
      statLatency.textContent = `${elapsed} ms`;

      searchNotification.style.display = "block";
      searchNotification.textContent = `[${data.source.toUpperCase()}] ${data.message} (${data.retrieved_count} extracted, ${data.stored_count} indexed into DuckDB).`;

      await refreshDashboard();
    } catch (err) {
      searchNotification.style.display = "block";
      searchNotification.textContent = `Error querying API: ${err.message}`;
    } finally {
      searchBtn.disabled = false;
      searchBtnText.textContent = "Run Live Scan";
    }
  });

  // 7. Filter & Sort Listeners
  filterKeyword.addEventListener("input", debounce(loadJobs, 200));
  filterWorkType.addEventListener("change", loadJobs);
  filterSort.addEventListener("change", loadJobs);

  // 8. Resume ATS Matcher
  matchBtn.addEventListener("click", async () => {
    const text = resumeInput.value.trim();
    if (!text) {
      matcherResults.innerHTML =
        '<p class="ats-empty-state font-mono">Please enter skills or resume text.</p>';
      return;
    }

    matchBtn.disabled = true;
    matchBtn.textContent = "Analyzing Market Alignment...";

    try {
      const res = await fetch("/api/match-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_text: text }),
      });
      const data = await res.json();
      renderAtsResults(data);
    } catch (err) {
      matcherResults.innerHTML = `<p class="ats-empty-state font-mono">Analysis error: ${err.message}</p>`;
    } finally {
      matchBtn.disabled = false;
      matchBtn.textContent = "Calculate Skill Alignment";
    }
  });

  // 9. Dashboard Refresh
  async function refreshDashboard() {
    await Promise.all([loadAnalytics(), loadJobs()]);
  }

  async function loadAnalytics() {
    try {
      const res = await fetch("/api/analytics");
      const data = await res.json();

      statTotalJobs.textContent = data.total_jobs;
      statRemoteJobs.textContent = data.remote_jobs;
      statSalaryJobs.textContent = data.salary_disclosed_jobs || 0;

      const remotePct =
        data.total_jobs > 0
          ? Math.round((data.remote_jobs / data.total_jobs) * 100)
          : 0;
      statRemotePercent.textContent = `${remotePct}%`;

      const salaryPct =
        data.total_jobs > 0
          ? Math.round(
              ((data.salary_disclosed_jobs || 0) / data.total_jobs) * 100,
            )
          : 0;
      statSalaryPercent.textContent = `${salaryPct}%`;

      renderSkills(data.top_skills);
      renderPlatforms(data.top_platforms);
      renderCompanies(data.top_companies);
    } catch (e) {
      console.error("Failed to load analytics", e);
    }
  }

  function renderSkills(skills) {
    if (!skills || skills.length === 0) {
      skillsChart.innerHTML =
        '<p class="empty-state font-mono">No skills extracted yet.</p>';
      return;
    }

    const maxCount = Math.max(...skills.map((s) => s.count), 1);
    skillsChart.innerHTML = skills
      .map((item) => {
        const widthPct = Math.round((item.count / maxCount) * 100);
        return `
        <div class="skill-bar-row">
          <div class="skill-bar-header">
            <span>${escapeHtml(item.skill)}</span>
            <span class="text-cyan">${item.count}</span>
          </div>
          <div class="skill-track">
            <div class="skill-progress-fill" style="width: ${widthPct}%;"></div>
          </div>
        </div>
      `;
      })
      .join("");
  }

  function renderPlatforms(platforms) {
    if (!platforms || platforms.length === 0) {
      platformsList.innerHTML =
        '<p class="empty-state font-mono">No portal data.</p>';
      return;
    }

    platformsList.innerHTML = platforms
      .map(
        (p) => `
      <div class="channel-badge-item">
        <span>${escapeHtml(p.platform)}</span>
        <span class="channel-badge-count">${p.count}</span>
      </div>
    `,
      )
      .join("");
  }

  function renderCompanies(companies) {
    if (!companies || companies.length === 0) {
      companiesList.innerHTML =
        '<p class="empty-state font-mono">No company data.</p>';
      return;
    }

    companiesList.innerHTML = companies
      .map(
        (c) => `
      <div class="channel-badge-item">
        <span>${escapeHtml(c.company_name)}</span>
        <span class="channel-badge-count">${c.count}</span>
      </div>
    `,
      )
      .join("");
  }

  async function loadJobs() {
    const keyword = filterKeyword.value.trim();
    const locationType = filterWorkType.value;
    const sort = filterSort.value;

    const params = new URLSearchParams();
    if (keyword) params.append("keyword", keyword);
    if (locationType) params.append("location_type", locationType);
    if (sort) params.append("sort_by", sort);

    try {
      const res = await fetch(`/api/jobs?${params.toString()}`);
      const data = await res.json();
      cachedJobs = data.jobs || [];
      renderJobs(cachedJobs);
    } catch (e) {
      jobsContainer.innerHTML = `<p class="empty-state font-mono">Error querying DuckDB: ${e.message}</p>`;
    }
  }

  function renderJobs(jobs) {
    if (!jobs || jobs.length === 0) {
      jobsContainer.innerHTML =
        '<p class="empty-state font-mono">No records matching active filters.</p>';
      return;
    }

    jobsContainer.innerHTML = jobs
      .map((job, idx) => {
        const isRemote =
          job.work_from_home ||
          (job.location && job.location.toLowerCase().includes("remote"));

        return `
        <article class="job-stream-card" data-index="${idx}">
          <div class="job-card-header">
            <div>
              <h4 class="job-card-title">${escapeHtml(job.title)}</h4>
              <div class="job-card-company">${escapeHtml(job.company_name)}</div>
            </div>
            <div class="badge-row">
              ${isRemote ? '<span class="badge badge-remote">REMOTE</span>' : '<span class="badge">ON-SITE</span>'}
              <span class="badge">${escapeHtml(job.via || "Direct Portal")}</span>
              ${job.salary ? `<span class="badge badge-salary">${escapeHtml(job.salary)}</span>` : ""}
            </div>
          </div>
          <p class="job-card-snippet">${escapeHtml(truncate(job.description, 200))}</p>
          <div class="job-card-footer">
            <span class="job-card-location">${escapeHtml(job.location || "Location Not Stated")} &bull; ${escapeHtml(job.posted_at || "Indexed")}</span>
            <span class="inspect-trigger">Inspect Details &rarr;</span>
          </div>
        </article>
      `;
      })
      .join("");

    // Attach card click handlers for the inspection drawer
    const cards = jobsContainer.querySelectorAll(".job-stream-card");
    cards.forEach((card) => {
      card.addEventListener("click", () => {
        const index = parseInt(card.getAttribute("data-index"), 10);
        if (cachedJobs[index]) {
          openDrawer(cachedJobs[index]);
        }
      });
    });
  }

  function renderAtsResults(data) {
    const score = data.match_score_percentage || 0;
    const circumference = 2 * Math.PI * 28; // radius 28
    const offset = circumference - (score / 100) * circumference;

    const matchedPills =
      data.matched_skills.length > 0
        ? data.matched_skills
            .map(
              (s) =>
                `<span class="tax-pill pill-matched">${escapeHtml(s)}</span>`,
            )
            .join("")
        : '<span class="text-sub font-mono">None detected</span>';

    const missingPills =
      data.missing_skills.length > 0
        ? data.missing_skills
            .map(
              (s) =>
                `<span class="tax-pill pill-missing">${escapeHtml(s)}</span>`,
            )
            .join("")
        : '<span class="text-sub font-mono">None</span>';

    matcherResults.innerHTML = `
      <div class="ats-gauge-flex">
        <div class="gauge-svg-wrap">
          <svg class="gauge-svg" width="72" height="72" viewBox="0 0 72 72">
            <circle class="gauge-bg" cx="36" cy="36" r="28" stroke-width="6" fill="none" />
            <circle class="gauge-progress" cx="36" cy="36" r="28" stroke-width="6" fill="none"
              stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" />
          </svg>
          <div class="gauge-number">${score}%</div>
        </div>
        <div class="gauge-text-desc">
          <h4>Corpus Skill Alignment</h4>
          <p>Deterministic overlap calculated against active openings.</p>
        </div>
      </div>

      <div class="ats-taxonomy-group">
        <div class="ats-taxonomy-title font-mono">MATCHED PREREQUISITES (${data.matched_skills.length})</div>
        <div class="pill-cloud">${matchedPills}</div>
      </div>

      <div class="ats-taxonomy-group">
        <div class="ats-taxonomy-title font-mono">HIGH-DEMAND GAPS (${data.missing_skills.length})</div>
        <div class="pill-cloud">${missingPills}</div>
      </div>
    `;
  }

  // Helpers
  function truncate(str, len) {
    if (!str) return "No description provided.";
    return str.length > len ? str.slice(0, len) + "..." : str;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }
});
