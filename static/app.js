document.addEventListener("DOMContentLoaded", () => {
  // ==================== DOM ELEMENTS ====================
  // Header status
  const apiStatusPill = document.getElementById("apiStatusPill");
  const apiStatusText = document.getElementById("apiStatusText");

  // Search console elements
  const searchForm = document.getElementById("searchForm");
  const queryInput = document.getElementById("queryInput");
  const queryCharCount = document.getElementById("queryCharCount");
  const queryValidationStatus = document.getElementById(
    "queryValidationStatus",
  );
  const queryErrorMsg = document.getElementById("queryErrorMsg");
  const locationInput = document.getElementById("locationInput");
  const datePostedInput = document.getElementById("datePostedInput");
  const resultsLimit = document.getElementById("resultsLimit");
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

  // Filter toolbar elements
  const jobsContainer = document.getElementById("jobsContainer");
  const filterKeyword = document.getElementById("filterKeyword");
  const clearKeywordBtn = document.getElementById("clearKeywordBtn");
  const filterWorkType = document.getElementById("filterWorkType");
  const filterFromDate = document.getElementById("filterFromDate");
  const filterToDate = document.getElementById("filterToDate");
  const clearDateBtn = document.getElementById("clearDateBtn");
  const filterSalaryOnly = document.getElementById("filterSalaryOnly");
  const filterSort = document.getElementById("filterSort");
  const clearAllFiltersBtn = document.getElementById("clearAllFiltersBtn");

  // Resume Matcher elements
  const resumeInput = document.getElementById("resumeInput");
  const atsWordCount = document.getElementById("atsWordCount");
  const atsCharCount = document.getElementById("atsCharCount");
  const matchBtn = document.getElementById("matchBtn");
  const matcherResults = document.getElementById("matcherResults");
  const loadSampleBioBtn = document.getElementById("loadSampleBioBtn");
  const resumeFileInput = document.getElementById("resumeFileInput");
  const clearResumeBtn = document.getElementById("clearResumeBtn");

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
  const drawerCopyLinkBtn = document.getElementById("drawerCopyLinkBtn");

  // Radar Canvas Elements
  const mainRadarCanvas = document.getElementById("mainRadarCanvas");
  const headerRadarCanvas = document.getElementById("headerRadarCanvas");
  const toastContainer = document.getElementById("toastContainer");

  // Local state cache
  let cachedJobs = [];
  let currentDrawerJob = null;

  // ==================== INITIALIZATION ====================
  initRadarAnimation();
  initSpotlightPhysics();
  initPresetChips();
  initDrawerControls();
  initFieldValidation();
  initFilterControls();
  initAtsControls();
  initKeyboardShortcuts();
  checkHealth();
  refreshDashboard();

  // ==================== TOAST NOTIFICATION SYSTEM ====================
  function showToast(message, type = "info", duration = 4000) {
    if (!toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `toast-pill toast-${type}`;
    toast.setAttribute("role", "alert");

    const textSpan = document.createElement("span");
    textSpan.textContent = message;
    toast.appendChild(textSpan);

    const closeBtn = document.createElement("button");
    closeBtn.className = "toast-close-btn";
    closeBtn.innerHTML = "&times;";
    closeBtn.title = "Dismiss";
    closeBtn.onclick = () => removeToast(toast);
    toast.appendChild(closeBtn);

    toastContainer.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => removeToast(toast), duration);
    }
  }

  function removeToast(toast) {
    if (!toast || !toast.parentNode) return;
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px) scale(0.95)";
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 250);
  }

  // ==================== 1. FIELD VALIDATION & REAL-TIME FEEDBACK ====================
  function validateQuery(val) {
    const trimmed = val.trim();
    if (!trimmed) {
      return { valid: false, message: "Search query cannot be empty." };
    }
    if (trimmed.length < 2) {
      return {
        valid: false,
        message: "Query must contain at least 2 characters.",
      };
    }
    if (trimmed.length > 100) {
      return { valid: false, message: "Query must not exceed 100 characters." };
    }
    const safeRegex = /^[a-zA-Z0-9\s\+\#\.\-_/]+$/;
    if (!safeRegex.test(trimmed)) {
      return {
        valid: false,
        message:
          "Special characters restricted. Alphanumerics, +, #, ., -, _, / allowed.",
      };
    }
    return { valid: true, message: "" };
  }

  function initFieldValidation() {
    if (!queryInput) return;

    function handleQueryInput() {
      const val = queryInput.value;
      if (queryCharCount) {
        queryCharCount.textContent = `${val.length} / 100`;
      }

      const check = validateQuery(val);
      if (check.valid) {
        queryInput.classList.remove("is-invalid");
        queryInput.classList.add("is-valid");
        if (queryValidationStatus) {
          queryValidationStatus.className = "validation-dot valid";
        }
        if (queryErrorMsg) {
          queryErrorMsg.style.display = "none";
          queryErrorMsg.textContent = "";
        }
      } else {
        queryInput.classList.remove("is-valid");
        queryInput.classList.add("is-invalid");
        if (queryValidationStatus) {
          queryValidationStatus.className = "validation-dot invalid";
        }
        if (queryErrorMsg) {
          queryErrorMsg.style.display = "block";
          queryErrorMsg.textContent = check.message;
        }
      }
    }

    queryInput.addEventListener("input", handleQueryInput);
    handleQueryInput(); // Run on initial render
  }

  // ==================== 2. SEARCH INGESTION CONTROLLER ====================
  searchForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const query = queryInput.value.trim();
    const location = locationInput.value;
    const num_results = parseInt(resultsLimit.value, 10);
    const date_posted = datePostedInput ? datePostedInput.value : null;

    const check = validateQuery(query);
    if (!check.valid) {
      queryInput.classList.add("is-invalid");
      if (queryErrorMsg) {
        queryErrorMsg.style.display = "block";
        queryErrorMsg.textContent = check.message;
      }
      queryInput.focus();
      showToast(check.message, "error");
      return;
    }

    searchBtn.disabled = true;
    searchBtnText.textContent = "Scanning SerpApi...";
    searchNotification.style.display = "none";

    // Show shimmering skeleton placeholders in the feed
    renderSkeletonJobs();

    const t0 = performance.now();
    try {
      const payload = { query, location, num_results };
      if (date_posted) payload.date_posted = date_posted;

      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error (${res.status})`);
      }

      const data = await res.json();
      const elapsed = Math.round(performance.now() - t0);
      statLatency.textContent = `${elapsed} ms`;

      searchNotification.style.display = "block";
      searchNotification.textContent = `[${data.source.toUpperCase()}] ${data.message} (${data.retrieved_count} extracted, ${data.stored_count} indexed into DuckDB).`;

      showToast(
        `SerpApi query complete: ${data.retrieved_count} jobs retrieved in ${elapsed}ms`,
        "success",
      );

      await refreshDashboard();
    } catch (err) {
      searchNotification.style.display = "block";
      searchNotification.textContent = `Search error: ${err.message}`;
      showToast(err.message, "error", 6000);
      await loadJobs(); // Re-render actual jobs on error
    } finally {
      searchBtn.disabled = false;
      searchBtnText.textContent = "Run Live Scan";
    }
  });

  // ==================== 3. FILTER & CALENDAR RANGE CONTROLS ====================
  function initFilterControls() {
    if (filterKeyword) {
      filterKeyword.addEventListener("input", () => {
        if (clearKeywordBtn) {
          clearKeywordBtn.style.display = filterKeyword.value
            ? "inline-block"
            : "none";
        }
        updateResetButtonVisibility();
        debounceLoadJobs();
      });
    }

    if (clearKeywordBtn) {
      clearKeywordBtn.addEventListener("click", () => {
        filterKeyword.value = "";
        clearKeywordBtn.style.display = "none";
        updateResetButtonVisibility();
        loadJobs();
      });
    }

    if (filterWorkType) {
      filterWorkType.addEventListener("change", () => {
        updateResetButtonVisibility();
        loadJobs();
      });
    }

    if (filterSort) {
      filterSort.addEventListener("change", () => {
        updateResetButtonVisibility();
        loadJobs();
      });
    }

    if (filterSalaryOnly) {
      filterSalaryOnly.addEventListener("change", () => {
        updateResetButtonVisibility();
        loadJobs();
      });
    }

    // Calendar Date Range Listeners
    if (filterFromDate && filterToDate) {
      const handleDateChange = () => {
        const from = filterFromDate.value;
        const to = filterToDate.value;

        if (clearDateBtn) {
          clearDateBtn.style.display = from || to ? "inline-block" : "none";
        }

        if (from && to && from > to) {
          showToast("From Date cannot be later than To Date.", "warning");
          filterToDate.value = from;
        }

        updateResetButtonVisibility();
        loadJobs();
      };

      filterFromDate.addEventListener("change", handleDateChange);
      filterToDate.addEventListener("change", handleDateChange);
    }

    if (clearDateBtn) {
      clearDateBtn.addEventListener("click", () => {
        if (filterFromDate) filterFromDate.value = "";
        if (filterToDate) filterToDate.value = "";
        clearDateBtn.style.display = "none";
        updateResetButtonVisibility();
        loadJobs();
      });
    }

    if (clearAllFiltersBtn) {
      clearAllFiltersBtn.addEventListener("click", () => {
        if (filterKeyword) filterKeyword.value = "";
        if (clearKeywordBtn) clearKeywordBtn.style.display = "none";
        if (filterWorkType) filterWorkType.value = "";
        if (filterFromDate) filterFromDate.value = "";
        if (filterToDate) filterToDate.value = "";
        if (clearDateBtn) clearDateBtn.style.display = "none";
        if (filterSalaryOnly) filterSalaryOnly.checked = false;
        if (filterSort) filterSort.value = "newest";

        clearAllFiltersBtn.style.display = "none";
        showToast("All filters reset to defaults.", "info");
        loadJobs();
      });
    }
  }

  function updateResetButtonVisibility() {
    if (!clearAllFiltersBtn) return;
    const hasKeyword = filterKeyword && filterKeyword.value.trim() !== "";
    const hasWorkType = filterWorkType && filterWorkType.value !== "";
    const hasFromDate = filterFromDate && filterFromDate.value !== "";
    const hasToDate = filterToDate && filterToDate.value !== "";
    const hasSalary = filterSalaryOnly && filterSalaryOnly.checked;
    const hasSort = filterSort && filterSort.value !== "newest";

    const isFiltered =
      hasKeyword ||
      hasWorkType ||
      hasFromDate ||
      hasToDate ||
      hasSalary ||
      hasSort;
    clearAllFiltersBtn.style.display = isFiltered ? "inline-block" : "none";
  }

  const debounceLoadJobs = debounce(loadJobs, 250);

  // ==================== 4. ATS RESUME MATCHER CONTROLS ====================
  function initAtsControls() {
    if (resumeInput) {
      resumeInput.addEventListener("input", updateResumeCounters);
      updateResumeCounters();
    }

    if (loadSampleBioBtn) {
      loadSampleBioBtn.addEventListener("click", () => {
        resumeInput.value =
          "Senior Software Engineer with 4+ years building high-throughput analytical services using Python, DuckDB, FastAPI, PostgreSQL, and Docker. Experienced in PyTorch ML inference, Next.js TypeScript frontends, and GeoPandas telemetry.";
        updateResumeCounters();
        showToast("Sample technical candidate bio loaded.", "info");
      });
    }

    if (resumeFileInput) {
      resumeFileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (file.size > 2 * 1024 * 1024) {
          showToast("File size exceeds 2MB limit.", "error");
          return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
          resumeInput.value = event.target.result;
          updateResumeCounters();
          showToast(`Imported ${file.name} successfully.`, "success");
        };
        reader.onerror = () => {
          showToast("Failed to read the uploaded resume file.", "error");
        };
        reader.readAsText(file);
      });
    }

    if (clearResumeBtn) {
      clearResumeBtn.addEventListener("click", () => {
        resumeInput.value = "";
        updateResumeCounters();
        matcherResults.innerHTML =
          '<div class="ats-empty-state font-mono">Paste skill inventory to compute match ratio.</div>';
        showToast("Resume inventory cleared.", "info");
      });
    }

    matchBtn.addEventListener("click", runAtsMatch);
  }

  function updateResumeCounters() {
    if (!resumeInput) return;
    const text = resumeInput.value;
    const charLen = text.length;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;

    if (atsCharCount)
      atsCharCount.textContent = `${charLen.toLocaleString()} / 50,000 chars`;
    if (atsWordCount)
      atsWordCount.textContent = `${words} ${words === 1 ? "word" : "words"}`;
  }

  async function runAtsMatch() {
    const text = resumeInput.value.trim();
    if (!text) {
      showToast(
        "Please enter or upload technical skills to evaluate.",
        "warning",
      );
      resumeInput.focus();
      return;
    }
    if (text.length < 5) {
      showToast("Resume text is too brief (minimum 5 characters).", "warning");
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

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error evaluating resume alignment.");
      }

      const data = await res.json();
      renderAtsResults(data);
      showToast(
        `ATS evaluation complete: ${data.match_score_percentage}% market alignment.`,
        "success",
      );
    } catch (err) {
      matcherResults.innerHTML = `<p class="ats-empty-state font-mono text-rose">Analysis error: ${escapeHtml(err.message)}</p>`;
      showToast(err.message, "error");
    } finally {
      matchBtn.disabled = false;
      matchBtn.textContent = "Calculate Skill Alignment";
    }
  }

  // ==================== 5. SKELETON LOADERS ====================
  function renderSkeletonJobs() {
    if (!jobsContainer) return;
    jobsContainer.innerHTML = Array(3)
      .fill(0)
      .map(
        () => `
      <div class="job-card-skeleton" aria-hidden="true">
        <div class="skeleton-line w-60"></div>
        <div class="skeleton-line w-40"></div>
        <div class="skeleton-line w-80"></div>
        <div class="skeleton-line w-30"></div>
      </div>
    `,
      )
      .join("");
  }

  // ==================== 6. JOB CORPUS FETCH & RENDERING ====================
  async function loadJobs() {
    const keyword = filterKeyword ? filterKeyword.value.trim() : "";
    const locationType = filterWorkType ? filterWorkType.value : "";
    const sort = filterSort ? filterSort.value : "newest";
    const fromDate = filterFromDate ? filterFromDate.value : "";
    const toDate = filterToDate ? filterToDate.value : "";
    const hasSalary = filterSalaryOnly ? filterSalaryOnly.checked : false;

    const params = new URLSearchParams();
    if (keyword) params.append("keyword", keyword);
    if (locationType) params.append("location_type", locationType);
    if (sort) params.append("sort_by", sort);
    if (fromDate) params.append("from_date", fromDate);
    if (toDate) params.append("to_date", toDate);
    if (hasSalary) params.append("has_salary", "true");

    try {
      const res = await fetch(`/api/jobs?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to load jobs.");
      const data = await res.json();
      cachedJobs = data.jobs || [];
      renderJobs(cachedJobs);
    } catch (e) {
      jobsContainer.innerHTML = `<p class="empty-state font-mono text-rose">Error querying DuckDB: ${escapeHtml(e.message)}</p>`;
    }
  }

  function renderJobs(jobs) {
    if (!jobs || jobs.length === 0) {
      jobsContainer.innerHTML =
        '<p class="empty-state font-mono">No records matching active search filters. Try adjusting your query or date range.</p>';
      return;
    }

    jobsContainer.innerHTML = jobs
      .map((job, idx) => {
        const isRemote =
          job.work_from_home ||
          (job.location && job.location.toLowerCase().includes("remote"));

        return `
        <article class="job-stream-card" data-index="${idx}" tabindex="0" role="button" aria-label="View details for ${escapeHtml(job.title)}">
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

    const cards = jobsContainer.querySelectorAll(".job-stream-card");
    cards.forEach((card) => {
      const handleOpen = () => {
        const index = parseInt(card.getAttribute("data-index"), 10);
        if (cachedJobs[index]) openDrawer(cachedJobs[index]);
      };
      card.addEventListener("click", handleOpen);
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleOpen();
        }
      });
    });
  }

  // ==================== 7. DRAWER INSPECTION & LINK SHARING ====================
  function initDrawerControls() {
    if (closeDrawerBtn) closeDrawerBtn.addEventListener("click", closeDrawer);
    if (drawerBackdrop) drawerBackdrop.addEventListener("click", closeDrawer);

    if (drawerCopyLinkBtn) {
      drawerCopyLinkBtn.addEventListener("click", () => {
        if (!currentDrawerJob) return;
        const link = currentDrawerJob.apply_link || window.location.href;
        navigator.clipboard.writeText(link).then(
          () =>
            showToast(
              "Official application link copied to clipboard!",
              "success",
            ),
          () => showToast("Unable to copy to clipboard.", "error"),
        );
      });
    }
  }

  function openDrawer(job) {
    currentDrawerJob = job;
    drawerJobTitle.textContent = job.title;
    drawerJobCompany.textContent = job.company_name;
    drawerLocation.textContent = `${job.location || "Location Not Stated"} • Schedule: ${job.schedule_type || "Standard"}`;

    drawerBadges.innerHTML = `
      <span class="badge ${job.work_from_home ? "badge-remote" : ""}">${job.work_from_home ? "REMOTE" : "ON-SITE"}</span>
      <span class="badge">${escapeHtml(job.via || "Direct")}</span>
      <span class="badge font-mono text-cyan">${escapeHtml(job.posted_at || "Indexed")}</span>
    `;

    if (job.salary) {
      drawerSalaryWrap.style.display = "block";
      drawerSalary.textContent = job.salary;
    } else {
      drawerSalaryWrap.style.display = "none";
    }

    drawerDescription.textContent =
      job.description || "No full description provided by hiring portal.";

    if (job.apply_link) {
      drawerApplyBtn.href = job.apply_link;
      drawerApplyBtn.style.display = "inline-flex";
    } else {
      drawerApplyBtn.style.display = "none";
    }

    jobDetailDrawer.classList.add("open");
    drawerBackdrop.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    jobDetailDrawer.classList.remove("open");
    drawerBackdrop.classList.remove("open");
    document.body.style.overflow = "";
    currentDrawerJob = null;
  }

  // ==================== 8. KEYBOARD SHORTCUTS ====================
  function initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Escape closes drawer
      if (e.key === "Escape") {
        if (jobDetailDrawer.classList.contains("open")) {
          closeDrawer();
        }
      }

      // Hotkey / focuses search input if not currently typing in an input
      if (
        e.key === "/" &&
        document.activeElement.tagName !== "INPUT" &&
        document.activeElement.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        queryInput.focus();
        queryInput.select();
      }

      // Ctrl + Enter in resume textarea triggers match
      if (
        e.ctrlKey &&
        e.key === "Enter" &&
        document.activeElement === resumeInput
      ) {
        e.preventDefault();
        runAtsMatch();
      }
    });
  }

  // ==================== 9. DASHBOARD ANALYTICS REFRESH ====================
  async function refreshDashboard() {
    await Promise.all([loadAnalytics(), loadJobs()]);
  }

  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      if (data.status === "healthy") {
        apiStatusText.textContent = data.serpapi_configured
          ? "SERPAPI: LIVE ONLINE"
          : "SERPAPI: DEMO CORPUS";
        if (apiStatusPill) {
          apiStatusPill.classList.toggle(
            "status-online",
            data.serpapi_configured,
          );
        }
      }
    } catch (e) {
      apiStatusText.textContent = "BACKEND: OFFLINE";
    }
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
            <span class="text-cyan font-mono">${item.count}</span>
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
        <span class="channel-badge-count font-mono">${p.count}</span>
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
        <span class="channel-badge-count font-mono">${c.count}</span>
      </div>
    `,
      )
      .join("");
  }

  function renderAtsResults(data) {
    const score = data.match_score_percentage || 0;
    const circumference = 2 * Math.PI * 28;
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

  // ==================== 10. PRESET CHIPS & SPOTLIGHT PHYSICS ====================
  function initPresetChips() {
    const chips = document.querySelectorAll(".preset-chip");
    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const q = chip.getAttribute("data-query");
        const l = chip.getAttribute("data-location");
        if (q && queryInput) {
          queryInput.value = q;
          queryInput.dispatchEvent(new Event("input"));
        }
        if (l && locationInput) {
          locationInput.value = l;
        }
        showToast(`Preset loaded: ${q}`, "info");
      });
    });
  }

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
      ctxMain.strokeStyle = "#00f0ff";
      ctxMain.lineWidth = 2;
      ctxMain.shadowColor = "#00f0ff";
      ctxMain.shadowBlur = 8;
      ctxMain.beginPath();
      ctxMain.moveTo(0, 0);
      ctxMain.lineTo(maxR, 0);
      ctxMain.stroke();
      ctxMain.restore();

      // Target Blips
      blips.forEach((b) => {
        const diff = (angle - b.theta + Math.PI * 2) % (Math.PI * 2);
        if (diff < 0.25) b.alpha = 1.0;
        else b.alpha = Math.max(0, b.alpha - 0.015);

        if (b.alpha > 0.05) {
          const bx = cx + Math.cos(b.theta) * b.r;
          const by = cy + Math.sin(b.theta) * b.r;

          ctxMain.fillStyle = `rgba(16, 185, 129, ${b.alpha})`;
          ctxMain.shadowColor = "#10b981";
          ctxMain.shadowBlur = 10;
          ctxMain.beginPath();
          ctxMain.arc(bx, by, 4, 0, Math.PI * 2);
          ctxMain.fill();
        }
      });

      // Mini Header Radar
      const mw = headerRadarCanvas.width;
      const mh = headerRadarCanvas.height;
      const mcx = mw / 2;
      const mcy = mh / 2;
      const mmaxR = mcx - 3;

      ctxMini.clearRect(0, 0, mw, mh);
      ctxMini.strokeStyle = "rgba(14, 165, 233, 0.3)";
      ctxMini.lineWidth = 1;
      ctxMini.beginPath();
      ctxMini.arc(mcx, mcy, mmaxR, 0, Math.PI * 2);
      ctxMini.stroke();

      ctxMini.save();
      ctxMini.translate(mcx, mcy);
      ctxMini.rotate(angle);
      ctxMini.strokeStyle = "#00f0ff";
      ctxMini.lineWidth = 1.5;
      ctxMini.beginPath();
      ctxMini.moveTo(0, 0);
      ctxMini.lineTo(mmaxR, 0);
      ctxMini.stroke();
      ctxMini.restore();

      angle = (angle + 0.035) % (Math.PI * 2);
      requestAnimationFrame(draw);
    }

    draw();
  }

  // ==================== UTILITY FUNCTIONS ====================
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
