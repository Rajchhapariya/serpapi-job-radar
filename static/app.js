document.addEventListener("DOMContentLoaded", () => {
  // Elements
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
  const statOnSiteJobs = document.getElementById("statOnSiteJobs");
  const statLatency = document.getElementById("statLatency");

  // Analytics elements
  const skillsChart = document.getElementById("skillsChart");
  const platformsList = document.getElementById("platformsList");
  const companiesList = document.getElementById("companiesList");

  // Jobs elements
  const jobsContainer = document.getElementById("jobsContainer");
  const filterKeyword = document.getElementById("filterKeyword");
  const filterWorkType = document.getElementById("filterWorkType");

  // Resume Matcher elements
  const resumeInput = document.getElementById("resumeInput");
  const matchBtn = document.getElementById("matchBtn");
  const matcherResults = document.getElementById("matcherResults");

  // Initialize
  checkHealth();
  refreshDashboard();

  // Search Handler
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
    searchBtnText.textContent = "Querying SerpApi...";
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
      searchNotification.textContent = `[${data.source.toUpperCase()}] ${data.message} (${data.retrieved_count} retrieved, ${data.stored_count} stored in DuckDB).`;

      await refreshDashboard();
    } catch (err) {
      searchNotification.style.display = "block";
      searchNotification.textContent = `Error querying API: ${err.message}`;
    } finally {
      searchBtn.disabled = false;
      searchBtnText.textContent = "Run Live Query";
    }
  });

  // Filter Listeners
  filterKeyword.addEventListener("input", debounce(loadJobs, 250));
  filterWorkType.addEventListener("change", loadJobs);

  // Resume Matcher Handler
  matchBtn.addEventListener("click", async () => {
    const text = resumeInput.value.trim();
    if (!text) {
      matcherResults.innerHTML =
        '<p class="empty-state">Please paste resume text before analyzing.</p>';
      return;
    }

    matchBtn.disabled = true;
    matchBtn.textContent = "Analyzing...";

    try {
      const res = await fetch("/api/match-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_text: text }),
      });
      const data = await res.json();
      renderMatchResults(data);
    } catch (err) {
      matcherResults.innerHTML = `<p class="empty-state">Analysis failed: ${err.message}</p>`;
    } finally {
      matchBtn.disabled = false;
      matchBtn.textContent = "Analyze Match Score";
    }
  });

  // Functions
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      const dot = apiStatusPill.querySelector(".status-dot");

      if (data.serpapi_configured) {
        apiStatusText.textContent = "SerpApi: Live Connected";
        dot.className = "status-dot";
      } else {
        apiStatusText.textContent = "SerpApi: Demo Dataset Mode";
        dot.className = "status-dot warning";
      }
    } catch (e) {
      apiStatusText.textContent = "Backend: Unreachable";
    }
  }

  async function refreshDashboard() {
    await Promise.all([loadAnalytics(), loadJobs()]);
  }

  async function loadAnalytics() {
    try {
      const res = await fetch("/api/analytics");
      const data = await res.json();

      statTotalJobs.textContent = data.total_jobs;
      statRemoteJobs.textContent = data.remote_jobs;
      statOnSiteJobs.textContent = data.on_site_jobs;

      const pct =
        data.total_jobs > 0
          ? Math.round((data.remote_jobs / data.total_jobs) * 100)
          : 0;
      statRemotePercent.textContent = `${pct}% of total openings`;

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
        '<p class="empty-state">No skill distributions extracted yet.</p>';
      return;
    }

    const maxCount = Math.max(...skills.map((s) => s.count), 1);
    skillsChart.innerHTML = skills
      .map((item) => {
        const widthPct = Math.round((item.count / maxCount) * 100);
        return `
        <div class="skill-row">
          <div class="skill-info">
            <span>${escapeHtml(item.skill)}</span>
            <span class="stat-badge-count">${item.count} mentions</span>
          </div>
          <div class="skill-bar-wrap">
            <div class="skill-bar-fill" style="width: ${widthPct}%;"></div>
          </div>
        </div>
      `;
      })
      .join("");
  }

  function renderPlatforms(platforms) {
    if (!platforms || platforms.length === 0) {
      platformsList.innerHTML = '<p class="empty-state">No platform data.</p>';
      return;
    }

    platformsList.innerHTML = platforms
      .map(
        (p) => `
      <div class="stat-badge-item">
        <span>${escapeHtml(p.platform)}</span>
        <span class="stat-badge-count">${p.count}</span>
      </div>
    `,
      )
      .join("");
  }

  function renderCompanies(companies) {
    if (!companies || companies.length === 0) {
      companiesList.innerHTML = '<p class="empty-state">No company data.</p>';
      return;
    }

    companiesList.innerHTML = companies
      .map(
        (c) => `
      <div class="stat-badge-item">
        <span>${escapeHtml(c.company_name)}</span>
        <span class="stat-badge-count">${c.count}</span>
      </div>
    `,
      )
      .join("");
  }

  async function loadJobs() {
    const keyword = filterKeyword.value.trim();
    const locationType = filterWorkType.value;

    const params = new URLSearchParams();
    if (keyword) params.append("keyword", keyword);
    if (locationType) params.append("location_type", locationType);

    try {
      const res = await fetch(`/api/jobs?${params.toString()}`);
      const data = await res.json();
      renderJobs(data.jobs);
    } catch (e) {
      jobsContainer.innerHTML = `<p class="empty-state">Error loading jobs: ${e.message}</p>`;
    }
  }

  function renderJobs(jobs) {
    if (!jobs || jobs.length === 0) {
      jobsContainer.innerHTML =
        '<p class="empty-state">No jobs matching your filter criteria.</p>';
      return;
    }

    jobsContainer.innerHTML = jobs
      .map((job) => {
        const isRemote =
          job.work_from_home ||
          (job.location && job.location.toLowerCase().includes("remote"));
        const applyBtn = job.apply_link
          ? `<a href="${escapeHtml(job.apply_link)}" target="_blank" rel="noopener noreferrer" class="apply-link">Apply on Portal</a>`
          : '<span class="badge">Direct Listing</span>';

        return `
        <article class="job-card">
          <div class="job-header">
            <div>
              <h3 class="job-title">${escapeHtml(job.title)}</h3>
              <div class="job-company">${escapeHtml(job.company_name)}</div>
            </div>
            <div class="job-badges">
              ${isRemote ? '<span class="badge badge-remote">REMOTE</span>' : '<span class="badge">ON-SITE</span>'}
              <span class="badge">${escapeHtml(job.via || "Direct")}</span>
              ${job.salary ? `<span class="badge badge-salary">${escapeHtml(job.salary)}</span>` : ""}
            </div>
          </div>
          <p class="job-description-snippet">${escapeHtml(truncate(job.description, 220))}</p>
          <div class="job-actions">
            <span class="job-posted">${escapeHtml(job.location || "Location Not Specified")} &bull; ${escapeHtml(job.posted_at || "Recently Indexed")}</span>
            ${applyBtn}
          </div>
        </article>
      `;
      })
      .join("");
  }

  function renderMatchResults(data) {
    const matchedHtml =
      data.matched_skills.length > 0
        ? data.matched_skills
            .map(
              (s) => `<span class="pill pill-matched">${escapeHtml(s)}</span>`,
            )
            .join("")
        : '<span class="empty-state" style="padding: 0;">None detected</span>';

    const missingHtml =
      data.missing_skills.length > 0
        ? data.missing_skills
            .map(
              (s) => `<span class="pill pill-missing">${escapeHtml(s)}</span>`,
            )
            .join("")
        : '<span class="empty-state" style="padding: 0;">None</span>';

    matcherResults.innerHTML = `
      <div class="score-display">
        <span class="score-number">${data.match_score_percentage}%</span>
        <span class="score-label">Skill Alignment Score</span>
      </div>
      <div class="tags-group">
        <div class="tags-group-title">Matched Technical Skills</div>
        <div class="pill-container">${matchedHtml}</div>
      </div>
      <div class="tags-group">
        <div class="tags-group-title">High-Demand Missing Keywords</div>
        <div class="pill-container">${missingHtml}</div>
      </div>
    `;
  }

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
