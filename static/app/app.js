/**
 * static/app/app.js
 * Skill Unlock Interface — Vanilla JS (DOM APIs only)
 */

(function () {
  "use strict";

  // Elements
  const resumeInput = document.getElementById("resume-input");
  const charCounter = document.getElementById("char-counter");
  const sampleBadge = document.getElementById("sample-badge");
  const btnSampleResume = document.getElementById("btn-sample-resume");
  const btnFindUnlocks = document.getElementById("btn-find-unlocks");
  const thresholdSlider = document.getElementById("threshold-slider");
  const thresholdVal = document.getElementById("threshold-val");
  const matchHelp = document.getElementById("match-help");

  const pillJobs = document.getElementById("pill-jobs");
  const pillDate = document.getElementById("pill-date");

  const stateIdle = document.getElementById("state-idle");
  const stateLoading = document.getElementById("state-loading");
  const stateError = document.getElementById("state-error");
  const stateResults = document.getElementById("state-results");
  const errorMessage = document.getElementById("error-message");

  const statMatchedNow = document.getElementById("stat-matched-now");
  const statAfterSkills = document.getElementById("stat-after-skills");
  const statSkillsFound = document.getElementById("stat-skills-found");

  const pathContainer = document.getElementById("path-container");
  const unlocksContainer = document.getElementById("unlocks-container");
  const unlocksCountBadge = document.getElementById("unlocks-count-badge");
  const jobsContainer = document.getElementById("jobs-container");

  const footerSampleNote = document.getElementById("footer-sample-note");
  const footerTelemetry = document.getElementById("footer-telemetry");

  const roleInputs = document.querySelectorAll('input[name="role-filter"]');
  const locationInputs = document.querySelectorAll(
    'input[name="location-filter"]',
  );

  // State
  let activeRequestId = 0;
  let currentlyExpandedAccordion = null;

  const MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  function formatDateString(rawDateStr) {
    if (!rawDateStr) return "--";
    try {
      const datePart = String(rawDateStr).split(" ")[0]; // YYYY-MM-DD
      const parts = datePart.split("-");
      if (parts.length === 3) {
        const year = parts[0];
        const monthIndex = parseInt(parts[1], 10) - 1;
        const day = parseInt(parts[2], 10);
        if (
          !isNaN(monthIndex) &&
          monthIndex >= 0 &&
          monthIndex < 12 &&
          !isNaN(day)
        ) {
          return day + " " + MONTHS[monthIndex] + " " + year;
        }
      }
    } catch (e) {
      // Fallback
    }
    return String(rawDateStr).slice(0, 10);
  }

  function updateCharCount() {
    const len = resumeInput.value.length;
    charCounter.textContent = len.toLocaleString() + " / 50,000";
    if (len > 50000) {
      charCounter.style.color = "var(--red)";
    } else {
      charCounter.style.color = "";
    }
  }

  function getSelectedRole() {
    for (let i = 0; i < roleInputs.length; i++) {
      if (roleInputs[i].checked) {
        return roleInputs[i].value || null;
      }
    }
    return null;
  }

  function getSelectedLocation() {
    for (let i = 0; i < locationInputs.length; i++) {
      if (locationInputs[i].checked) {
        return locationInputs[i].value || null;
      }
    }
    return null;
  }

  function getThreshold() {
    return parseInt(thresholdSlider.value, 10) || 60;
  }

  function showState(stateName) {
    stateIdle.classList.toggle("hidden", stateName !== "idle");
    stateLoading.classList.toggle("hidden", stateName !== "loading");
    stateError.classList.toggle("hidden", stateName !== "error");
    stateResults.classList.toggle("hidden", stateName !== "results");
  }

  function animateHeroNumber(element, targetVal, durationMs) {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion || durationMs <= 0) {
      element.textContent = targetVal.toLocaleString();
      return;
    }

    const startVal = 0;
    const startTime = performance.now();

    function step(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / durationMs, 1.0);
      // Ease-out cubic: 1 - (1 - progress)^3
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const currentVal = Math.round(
        startVal + (targetVal - startVal) * easeProgress,
      );
      element.textContent = currentVal.toLocaleString();

      if (progress < 1.0) {
        requestAnimationFrame(step);
      } else {
        element.textContent = targetVal.toLocaleString();
      }
    }

    requestAnimationFrame(step);
  }

  function clearElementChildren(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  // Render Fastest Path
  function renderPath(pathList) {
    clearElementChildren(pathContainer);

    if (!pathList || pathList.length === 0) {
      const emptyCard = document.createElement("div");
      emptyCard.className = "card path-empty-card";
      emptyCard.textContent =
        "No single skill moves you closer at this match bar.";
      pathContainer.appendChild(emptyCard);
      return;
    }

    pathList.forEach(function (step) {
      const card = document.createElement("div");
      card.className = "card path-step-card";

      const badge = document.createElement("span");
      badge.className = "path-step-badge mono";
      badge.textContent = "Step " + step.step;

      const skillEl = document.createElement("span");
      skillEl.className = "path-step-skill";
      skillEl.textContent = step.skill;

      const unlocksEl = document.createElement("span");
      unlocksEl.className = "path-step-unlocks mono";
      unlocksEl.textContent = "+" + step.unlocks + " jobs";

      const cumEl = document.createElement("span");
      cumEl.className = "path-step-cum mono";
      cumEl.textContent = step.cumulative_gain + " total unlocked";

      card.appendChild(badge);
      card.appendChild(skillEl);
      card.appendChild(unlocksEl);
      card.appendChild(cumEl);
      pathContainer.appendChild(card);
    });
  }

  // Render All Unlocks
  function renderUnlocks(unlocksList) {
    clearElementChildren(unlocksContainer);
    currentlyExpandedAccordion = null;

    if (!unlocksList || unlocksList.length === 0) {
      const emptyRow = document.createElement("div");
      emptyRow.className = "card path-empty-card";
      emptyRow.textContent =
        "No skill unlocks found for this resume and threshold.";
      unlocksContainer.appendChild(emptyRow);
      return;
    }

    let maxUnlocks = 1;
    unlocksList.forEach(function (u) {
      if (u.unlocks > maxUnlocks) maxUnlocks = u.unlocks;
    });

    unlocksList.forEach(function (u) {
      const card = document.createElement("div");
      card.className = "unlock-row-card";

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "unlock-btn";
      btn.setAttribute("aria-expanded", "false");

      const topRow = document.createElement("div");
      topRow.className = "unlock-row-top";

      const skillName = document.createElement("span");
      skillName.className = "unlock-skill-name";
      skillName.textContent = u.skill;

      const metrics = document.createElement("div");
      metrics.className = "unlock-metrics mono";

      const mUnlocks = document.createElement("span");
      mUnlocks.className = "metric-unlocks";
      mUnlocks.textContent = "+" + u.unlocks + " jobs";

      const mDemand = document.createElement("span");
      mDemand.className = "metric-demand";
      mDemand.textContent = "in " + u.demand + " jobs";

      metrics.appendChild(mUnlocks);
      metrics.appendChild(mDemand);
      topRow.appendChild(skillName);
      topRow.appendChild(metrics);

      const track = document.createElement("div");
      track.className = "unlock-bar-track";

      const fill = document.createElement("div");
      fill.className = "unlock-bar-fill";
      const pctWidth = Math.max(
        3,
        Math.min(100, Math.round((u.unlocks / maxUnlocks) * 100)),
      );
      fill.style.width = pctWidth + "%";
      track.appendChild(fill);

      btn.appendChild(topRow);
      btn.appendChild(track);
      card.appendChild(btn);

      // Accordion panel for example jobs
      const panel = document.createElement("div");
      panel.className = "example-jobs-panel hidden";

      if (u.example_jobs && u.example_jobs.length > 0) {
        u.example_jobs.forEach(function (ex) {
          const item = document.createElement("div");
          item.className = "example-job-item";

          const titleSpan = document.createElement("span");
          titleSpan.className = "example-job-title";
          titleSpan.textContent =
            ex.title + (ex.company_name ? " · " + ex.company_name : "");

          const matchSpan = document.createElement("span");
          matchSpan.className = "example-job-match mono";
          matchSpan.textContent =
            ex.match_before + "% → " + ex.match_after + "%";

          item.appendChild(titleSpan);
          item.appendChild(matchSpan);
          panel.appendChild(item);
        });
      } else {
        const noEx = document.createElement("div");
        noEx.className = "example-job-item";
        const noExSpan = document.createElement("span");
        noExSpan.className = "example-job-title";
        noExSpan.textContent = "No specific example job previews available.";
        noEx.appendChild(noExSpan);
        panel.appendChild(noEx);
      }

      card.appendChild(panel);

      btn.addEventListener("click", function () {
        const isExpanded = btn.getAttribute("aria-expanded") === "true";
        if (
          currentlyExpandedAccordion &&
          currentlyExpandedAccordion !== panel
        ) {
          currentlyExpandedAccordion.classList.add("hidden");
          const parentBtn =
            currentlyExpandedAccordion.parentElement.querySelector("button");
          if (parentBtn) parentBtn.setAttribute("aria-expanded", "false");
        }

        if (isExpanded) {
          btn.setAttribute("aria-expanded", "false");
          panel.classList.add("hidden");
          currentlyExpandedAccordion = null;
        } else {
          btn.setAttribute("aria-expanded", "true");
          panel.classList.remove("hidden");
          currentlyExpandedAccordion = panel;
        }
      });

      unlocksContainer.appendChild(card);
    });
  }

  // Render Best-Fit Jobs
  function renderJobs(jobsList) {
    clearElementChildren(jobsContainer);

    if (!jobsList || jobsList.length === 0) {
      const emptyCard = document.createElement("div");
      emptyCard.className = "card path-empty-card";
      emptyCard.textContent = "No matching jobs found for current filters.";
      jobsContainer.appendChild(emptyCard);
      return;
    }

    // Top 8 jobs
    const topJobs = jobsList.slice(0, 8);

    topJobs.forEach(function (job, idx) {
      const card = document.createElement("div");
      card.className = "card job-card";
      card.style.animationDelay = idx * 40 + "ms";

      // Header row
      const header = document.createElement("div");
      header.className = "job-header";

      const metaLeft = document.createElement("div");
      metaLeft.className = "job-meta-left";

      const titleEl = document.createElement("span");
      titleEl.className = "job-title";
      titleEl.textContent = job.title;

      const compEl = document.createElement("span");
      compEl.className = "job-company";
      compEl.textContent =
        job.company_name + (job.location ? " · " + job.location : "");

      metaLeft.appendChild(titleEl);
      metaLeft.appendChild(compEl);

      const badges = document.createElement("div");
      badges.className = "job-badges";

      // Status chip
      const statusChip = document.createElement("span");
      if (job.status === "matched") {
        statusChip.className = "chip chip-status-matched";
        statusChip.textContent = "Matched";
      } else if (job.status === "one_skill_away") {
        statusChip.className = "chip chip-status-one_skill_away";
        statusChip.textContent = "1 skill away";
      } else {
        statusChip.className = "chip chip-status-further";
        statusChip.textContent = "Further";
      }
      badges.appendChild(statusChip);

      // Location chip
      if (job.location_type) {
        const locChip = document.createElement("span");
        locChip.className = "chip chip-location";
        locChip.textContent = job.location_type;
        badges.appendChild(locChip);
      }

      // Portal chip
      const portalChip = document.createElement("span");
      portalChip.className = "chip chip-portals mono";
      const pCount = job.portal_count || 1;
      portalChip.textContent = pCount >= 8 ? "8+ portals" : pCount + " portals";
      badges.appendChild(portalChip);

      header.appendChild(metaLeft);
      header.appendChild(badges);
      card.appendChild(header);

      // Match bar row
      const matchRow = document.createElement("div");
      matchRow.className = "job-match-row";

      const track = document.createElement("div");
      track.className = "job-match-bar-track";

      const fill = document.createElement("div");
      fill.className = "job-match-bar-fill";
      const pct = Math.max(0, Math.min(100, job.match_pct || 0));
      fill.style.width = pct + "%";
      track.appendChild(fill);

      const pctText = document.createElement("span");
      pctText.className = "job-match-pct mono";
      pctText.textContent = pct + "%";

      matchRow.appendChild(track);
      matchRow.appendChild(pctText);
      card.appendChild(matchRow);

      // Missing skills chips
      if (job.missing && job.missing.length > 0) {
        const missingWrap = document.createElement("div");
        missingWrap.className = "job-missing-skills";

        const label = document.createElement("span");
        label.className = "missing-label";
        label.textContent = "Missing:";
        missingWrap.appendChild(label);

        job.missing.forEach(function (mSkill) {
          const chip = document.createElement("span");
          chip.className = "chip chip-missing";
          chip.textContent = mSkill;
          missingWrap.appendChild(chip);
        });

        card.appendChild(missingWrap);
      }

      jobsContainer.appendChild(card);
    });
  }

  // Execute Analysis
  async function runAnalysis() {
    const text = resumeInput.value.trim();
    if (!text) {
      showState("error");
      errorMessage.textContent =
        "Please paste a resume or use the sample resume to find unlocks.";
      return;
    }

    const reqId = ++activeRequestId;
    showState("loading");
    btnFindUnlocks.disabled = true;
    btnFindUnlocks.textContent = "Finding...";

    const threshold = getThreshold();
    const role = getSelectedRole();
    const locationType = getSelectedLocation();

    const payloadUnlock = {
      resume_text: text,
      threshold: threshold,
      top_n: 10,
    };
    if (role) payloadUnlock.role = role;
    if (locationType) payloadUnlock.location_type = locationType;

    const payloadFit = {
      resume_text: text,
      threshold: threshold,
      limit: 12,
    };
    if (role) payloadFit.role = role;
    if (locationType) payloadFit.location_type = locationType;

    const controller = new AbortController();
    const timeoutId = setTimeout(function () {
      controller.abort();
    }, 15000);

    try {
      const [resUnlock, resFit] = await Promise.all([
        fetch("/api/unlock", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payloadUnlock),
          signal: controller.signal,
        }),
        fetch("/api/fit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payloadFit),
          signal: controller.signal,
        }),
      ]);

      clearTimeout(timeoutId);

      // Stale response guard
      if (reqId !== activeRequestId) return;

      // Handle HTTP errors
      if (!resUnlock.ok || !resFit.ok) {
        const failedRes = !resUnlock.ok ? resUnlock : resFit;
        if (failedRes.status === 429) {
          showState("error");
          errorMessage.textContent =
            "Too many requests. Wait a minute and try again.";
          return;
        }

        let detailMsg = "An error occurred during calculation.";
        try {
          const errJson = await failedRes.json();
          if (errJson && errJson.detail) {
            if (typeof errJson.detail === "string") {
              detailMsg = errJson.detail;
            } else if (
              Array.isArray(errJson.detail) &&
              errJson.detail.length > 0 &&
              errJson.detail[0].msg
            ) {
              detailMsg = errJson.detail[0].msg;
            }
          }
        } catch (e) {
          // Keep generic detailMsg
        }

        showState("error");
        errorMessage.textContent = detailMsg;
        return;
      }

      const dataUnlock = await resUnlock.json();
      const dataFit = await resFit.json();

      if (reqId !== activeRequestId) return;

      // Populate Stat Strip
      const baseline = dataUnlock.baseline || {
        eligible_jobs: 0,
        matched_jobs: 0,
      };
      statMatchedNow.textContent =
        baseline.matched_jobs + " / " + baseline.eligible_jobs;

      // Hero Stat: Matched + cumulative gain from last step of path
      const pathList = dataUnlock.path || [];
      const lastGain =
        pathList.length > 0
          ? pathList[pathList.length - 1].cumulative_gain || 0
          : 0;
      const targetAfter = baseline.matched_jobs + lastGain;
      animateHeroNumber(statAfterSkills, targetAfter, 600);

      const resumeSkills = dataUnlock.resume_skills || [];
      statSkillsFound.textContent = resumeSkills.length.toString();

      // Populate Fastest Path
      renderPath(pathList);

      // Populate All Unlocks
      const unlocksList = dataUnlock.unlocks || [];
      unlocksCountBadge.textContent = unlocksList.length + " skills";
      renderUnlocks(unlocksList);

      // Populate Best-Fit Jobs
      renderJobs(dataFit.jobs || []);

      // Footer Disclosure & Telemetry
      const corpus = dataUnlock.corpus || {};
      const dateFormatted = formatDateString(corpus.as_of_max);
      pillDate.textContent = "As of " + dateFormatted;
      const notePrefix =
        corpus.sample_note || "Jobs captured from Google Jobs searches.";
      footerSampleNote.textContent =
        notePrefix + " Data as of " + dateFormatted + ".";

      const uMs = dataUnlock.query_ms != null ? dataUnlock.query_ms : "--";
      const fMs = dataFit.query_ms != null ? dataFit.query_ms : "--";
      footerTelemetry.textContent =
        "Unlock query " +
        uMs +
        " ms · Fit query " +
        fMs +
        " ms (DuckDB, server-side)";

      showState("results");
    } catch (err) {
      if (reqId !== activeRequestId) return;
      showState("error");
      if (err.name === "AbortError") {
        errorMessage.textContent =
          "Request timed out after 15 seconds. Please try again.";
      } else {
        errorMessage.textContent = "Could not reach the server.";
      }
    } finally {
      if (reqId === activeRequestId) {
        btnFindUnlocks.disabled = false;
        btnFindUnlocks.textContent = "Find my unlocks";
      }
    }
  }

  // Populate Sample Resume
  async function loadSampleResume(autoRun) {
    try {
      const res = await fetch("/api/sample-resume");
      if (!res.ok) throw new Error("Failed to load sample resume");
      const data = await res.json();
      if (data && data.text) {
        resumeInput.value = data.text;
        updateCharCount();
        sampleBadge.classList.remove("hidden");
        if (autoRun) {
          runAnalysis();
        }
      }
    } catch (err) {
      showState("idle");
    }
  }

  // Load Header Meta (Health & Roles)
  async function loadHeaderMeta() {
    try {
      const [resHealth, resRoles] = await Promise.all([
        fetch("/api/health"),
        fetch("/api/roles"),
      ]);

      if (resHealth.ok) {
        const hData = await resHealth.json();
        if (hData && hData.indexed_jobs_count != null) {
          pillJobs.textContent = hData.indexed_jobs_count + " jobs indexed";
        }
      }

      if (resRoles.ok) {
        const rData = await resRoles.json();
        if (rData && rData.roles) {
          rData.roles.forEach(function (r) {
            const labelEl = document.getElementById("role-label-" + r.role);
            if (labelEl) {
              labelEl.textContent = r.label + " (" + r.jobs + ")";
            }
          });
        }
      }
    } catch (e) {
      // Non-critical background header load
    }
  }

  // Event Listeners
  resumeInput.addEventListener("input", function () {
    updateCharCount();
    sampleBadge.classList.add("hidden");
  });

  thresholdSlider.addEventListener("input", function () {
    const val = getThreshold();
    thresholdVal.textContent = val + "%";
    matchHelp.textContent =
      "A job counts as a match when you already cover " +
      val +
      "% of its listed skills.";
  });

  btnSampleResume.addEventListener("click", function () {
    loadSampleResume(true);
  });

  btnFindUnlocks.addEventListener("click", function () {
    runAnalysis();
  });

  roleInputs.forEach(function (radio) {
    radio.addEventListener("change", function () {
      if (resumeInput.value.trim().length > 0) {
        runAnalysis();
      }
    });
  });

  locationInputs.forEach(function (radio) {
    radio.addEventListener("change", function () {
      if (resumeInput.value.trim().length > 0) {
        runAnalysis();
      }
    });
  });

  // Initialization
  updateCharCount();
  loadHeaderMeta();
  loadSampleResume(true); // First load: fetch sample resume and run automatically
})();
