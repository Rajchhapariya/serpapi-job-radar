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

  const statAfterSkills = document.getElementById("stat-after-skills");
  const heroStatTotal = document.getElementById("hero-stat-total");
  const heroSupportLine = document.getElementById("hero-support-line");

  const pathTrackBar = document.getElementById("path-track-bar");
  const pathTrackLabels = document.getElementById("path-track-labels");
  const pathTrackEmpty = document.getElementById("path-track-empty");

  const pathContainer = document.getElementById("path-container");
  const unlocksContainer = document.getElementById("unlocks-container");
  const unlocksCountBadge = document.getElementById("unlocks-count-badge");
  const jobsContainer = document.getElementById("jobs-container");

  const footerSampleNote = document.getElementById("footer-sample-note");
  const footerTelemetry = document.getElementById("footer-telemetry");

  const liveQueryInput = document.getElementById("live-query-input");
  const liveLocationInput = document.getElementById("live-location-input");
  const btnFetchLive = document.getElementById("btn-fetch-live");
  const liveStatusRow = document.getElementById("live-status-row");

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

  // Render Horizontal Path Track beneath Hero
  function renderTrack(baseline, pathList) {
    clearElementChildren(pathTrackBar);
    clearElementChildren(pathTrackLabels);

    const eligible = baseline.eligible_jobs || 1;
    const matched = baseline.matched_jobs || 0;

    // Segment 1: matched now (var(--ink))
    const segNow = document.createElement("div");
    segNow.className = "track-segment track-segment-now";
    const pctNow = Math.min(100, (matched / eligible) * 100);
    segNow.style.width = pctNow + "%";
    pathTrackBar.appendChild(segNow);

    // Label 1: NOW {matched}
    const lblNow = document.createElement("span");
    lblNow.className = "track-label";
    lblNow.textContent = "NOW " + matched;
    pathTrackLabels.appendChild(lblNow);

    if (!pathList || pathList.length === 0) {
      if (pathTrackEmpty) pathTrackEmpty.classList.remove("hidden");
      return;
    }
    if (pathTrackEmpty) pathTrackEmpty.classList.add("hidden");

    // Segments 2 to 4: path steps 1 to 3
    const opacities = [0.55, 0.75, 1.0];
    const stepsToShow = pathList.slice(0, 3);

    stepsToShow.forEach(function (st, idx) {
      const seg = document.createElement("div");
      seg.className = "track-segment track-segment-step";
      seg.style.opacity = opacities[idx];
      const segPct = Math.min(100, (st.unlocks / eligible) * 100);
      seg.style.width = segPct + "%";
      pathTrackBar.appendChild(seg);

      const lbl = document.createElement("span");
      lbl.className = "track-label";
      const cumCount = matched + st.cumulative_gain;
      lbl.textContent = "+ " + st.skill.toUpperCase() + " " + cumCount;
      pathTrackLabels.appendChild(lbl);
    });
  }

  // Render Fastest Path Ledger Rows
  function renderPath(pathList) {
    clearElementChildren(pathContainer);

    if (!pathList || pathList.length === 0) {
      const emptyRow = document.createElement("div");
      emptyRow.className = "ledger-row ledger-row-empty mono";
      emptyRow.textContent =
        "No single skill moves you closer at this match bar.";
      pathContainer.appendChild(emptyRow);
      return;
    }

    pathList.forEach(function (step) {
      const row = document.createElement("div");
      row.className = "ledger-row path-ledger-row";

      const stepNum = document.createElement("span");
      stepNum.className = "path-step-num mono";
      stepNum.textContent = String(step.step);

      const skillEl = document.createElement("span");
      skillEl.className = "path-step-skill";
      skillEl.textContent = step.skill;

      const unlocksEl = document.createElement("span");
      unlocksEl.className = "path-step-unlocks mono";
      unlocksEl.textContent = "+" + step.unlocks + " jobs";

      const cumEl = document.createElement("span");
      cumEl.className = "path-step-cum mono";
      cumEl.textContent = step.cumulative_gain + " total";

      row.appendChild(stepNum);
      row.appendChild(skillEl);
      row.appendChild(unlocksEl);
      row.appendChild(cumEl);
      pathContainer.appendChild(row);
    });
  }

  // Render All Unlocks Ledger Rows
  function renderUnlocks(unlocksList) {
    clearElementChildren(unlocksContainer);
    currentlyExpandedAccordion = null;

    if (!unlocksList || unlocksList.length === 0) {
      const emptyRow = document.createElement("div");
      emptyRow.className = "ledger-row ledger-row-empty mono";
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
      const row = document.createElement("div");
      row.className = "ledger-row unlock-ledger-row";

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "unlock-btn";
      btn.setAttribute("aria-expanded", "false");

      const mainDiv = document.createElement("div");
      mainDiv.className = "unlock-btn-main";

      const skillName = document.createElement("span");
      skillName.className = "unlock-skill-name";
      skillName.textContent = u.skill;

      const metrics = document.createElement("div");
      metrics.className = "unlock-metrics mono";

      const mUnlocks = document.createElement("span");
      mUnlocks.className = "unlock-metric-gain";
      mUnlocks.textContent = "+" + u.unlocks + " jobs";

      const mDemand = document.createElement("span");
      mDemand.className = "unlock-metric-demand";
      mDemand.textContent = "in " + u.demand + " jobs";

      metrics.appendChild(mUnlocks);
      metrics.appendChild(mDemand);
      mainDiv.appendChild(skillName);
      mainDiv.appendChild(metrics);

      const track = document.createElement("div");
      track.className = "unlock-bar-track";

      const fill = document.createElement("div");
      fill.className = "unlock-bar-fill";
      const ratio = Math.max(0.02, Math.min(1.0, u.unlocks / maxUnlocks));
      fill.style.transform = "scaleX(" + ratio + ")";
      track.appendChild(fill);

      btn.appendChild(mainDiv);
      btn.appendChild(track);
      row.appendChild(btn);

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
            ex.match_before + "% to " + ex.match_after + "%";

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

      row.appendChild(panel);

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

      unlocksContainer.appendChild(row);
    });
  }

  // Render Best-Fit Jobs Ledger Rows
  function renderJobs(jobsList) {
    clearElementChildren(jobsContainer);

    if (!jobsList || jobsList.length === 0) {
      const emptyRow = document.createElement("div");
      emptyRow.className = "ledger-row ledger-row-empty mono";
      emptyRow.textContent = "No matching jobs found for current filters.";
      jobsContainer.appendChild(emptyRow);
      return;
    }

    const topJobs = jobsList.slice(0, 8);

    topJobs.forEach(function (job, idx) {
      const row = document.createElement("div");
      row.className = "ledger-row job-ledger-row stagger-row";
      row.style.animationDelay = Math.min(idx, 7) * 30 + "ms";

      // Top row: Title on left, Status + Portals on right
      const topRow = document.createElement("div");
      topRow.className = "job-row-top";

      const titleEl = document.createElement("span");
      titleEl.className = "job-title";
      titleEl.textContent = job.title;

      const badges = document.createElement("div");
      badges.className = "job-badges";

      // Status label: matched = green on green-soft, one_skill_away = amber on amber-soft, further = ink-3 on inset (4px radius)
      const statusChip = document.createElement("span");
      if (job.status === "matched") {
        statusChip.className = "status-badge status-matched";
        statusChip.textContent = "Matched";
      } else if (job.status === "one_skill_away") {
        statusChip.className = "status-badge status-one_skill_away";
        statusChip.textContent = "1 skill away";
      } else {
        statusChip.className = "status-badge status-further";
        statusChip.textContent = "Further";
      }
      badges.appendChild(statusChip);

      // Portals as "{n} portals" or "8+ portals"
      const portalChip = document.createElement("span");
      portalChip.className = "job-portal-badge mono";
      const pCount = job.portal_count || 1;
      portalChip.textContent = pCount >= 8 ? "8+ portals" : pCount + " portals";
      badges.appendChild(portalChip);

      topRow.appendChild(titleEl);
      topRow.appendChild(badges);
      row.appendChild(topRow);

      // Meta sub row: Company and Location_type in var(--ink-3)
      const metaRow = document.createElement("div");
      metaRow.className = "job-meta-row";
      let metaText = job.company_name || "";
      if (job.location_type) {
        metaText += (metaText ? " · " : "") + job.location_type;
      }
      metaRow.textContent = metaText;
      row.appendChild(metaRow);

      // Match bar row: thin match bar with "{match_pct}%" in mono
      const matchRow = document.createElement("div");
      matchRow.className = "job-match-row";

      const track = document.createElement("div");
      track.className = "job-match-track";

      const fill = document.createElement("div");
      fill.className = "job-match-fill";
      const pct = Math.max(0, Math.min(100, job.match_pct || 0));
      fill.style.width = pct + "%";
      track.appendChild(fill);

      const pctText = document.createElement("span");
      pctText.className = "job-match-pct mono";
      pctText.textContent = pct + "%";

      matchRow.appendChild(track);
      matchRow.appendChild(pctText);
      row.appendChild(matchRow);

      // Missing skills: chips (red on red-soft, no border, 4px radius)
      if (job.missing && job.missing.length > 0) {
        const missingWrap = document.createElement("div");
        missingWrap.className = "job-missing-wrap";

        const mLabel = document.createElement("span");
        mLabel.className = "job-missing-label mono";
        mLabel.textContent = "MISSING:";
        missingWrap.appendChild(mLabel);

        job.missing.forEach(function (mSkill) {
          const chip = document.createElement("span");
          chip.className = "chip-missing";
          chip.textContent = mSkill;
          missingWrap.appendChild(chip);
        });

        row.appendChild(missingWrap);
      }

      jobsContainer.appendChild(row);
    });
  }

  // API Call Coordinator
  async function handleRunAnalysis() {
    const resumeText = resumeInput.value.trim();
    if (!resumeText) {
      showState("idle");
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
      resume_text: resumeText,
      threshold: threshold,
      top_n: 10,
    };
    if (role) payloadUnlock.role = role;
    if (locationType) payloadUnlock.location_type = locationType;

    const payloadFit = {
      resume_text: resumeText,
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

      // Populate Hero Block
      const baseline = dataUnlock.baseline || {
        eligible_jobs: 0,
        matched_jobs: 0,
      };

      const pathList = dataUnlock.path || [];
      const lastGain =
        pathList.length > 0
          ? pathList[pathList.length - 1].cumulative_gain || 0
          : 0;
      const targetAfter = baseline.matched_jobs + lastGain;

      animateHeroNumber(statAfterSkills, targetAfter, 600);
      heroStatTotal.textContent = " of " + baseline.eligible_jobs + " jobs";

      const resumeSkills = dataUnlock.resume_skills || [];
      heroSupportLine.textContent =
        "Up from " +
        baseline.matched_jobs +
        " today. " +
        resumeSkills.length +
        " skills recognized in your resume.";

      // Populate Path Track beneath hero
      renderTrack(baseline, pathList);

      // Populate Fastest Path ledger rows
      renderPath(pathList);

      // Populate All Unlocks ledger rows
      const unlocksList = dataUnlock.unlocks || [];
      unlocksCountBadge.textContent = unlocksList.length + " skills";
      renderUnlocks(unlocksList);

      // Populate Best-Fit Jobs ledger rows
      renderJobs(dataFit.jobs || []);

      // Footer Disclosure & Telemetry
      const corpus = dataUnlock.corpus || {};
      const dateFormatted = formatDateString(corpus.as_of_max);
      pillDate.textContent = "Data as of " + dateFormatted;
      if (corpus.jobs != null) {
        pillJobs.textContent = corpus.jobs + " jobs indexed";
      }

      const share =
        corpus.snapshot_share != null ? Number(corpus.snapshot_share) : 1;
      let snapshotSentence = "";
      if (share >= 0.999 || share === 1) {
        snapshotSentence =
          "All listings come from saved Google Jobs snapshots.";
      } else {
        const pct = Math.round(share * 100);
        snapshotSentence =
          pct + "% of listings come from saved Google Jobs snapshots.";
      }
      footerSampleNote.textContent =
        snapshotSentence + " Data as of " + dateFormatted + ".";

      const uMs = dataUnlock.query_ms != null ? dataUnlock.query_ms : "--";
      const fMs = dataFit.query_ms != null ? dataFit.query_ms : "--";
      footerTelemetry.textContent =
        "Unlock query " +
        uMs +
        " ms · Fit query " +
        fMs +
        " ms (DuckDB, server-side)";

      showState("results");
      return dataUnlock;
    } catch (err) {
      if (reqId !== activeRequestId) return;
      showState("error");
      if (err.name === "AbortError") {
        errorMessage.textContent = "Request timed out after 15 seconds.";
      } else {
        errorMessage.textContent = "Could not reach the server.";
      }
      return null;
    } finally {
      if (reqId === activeRequestId) {
        btnFindUnlocks.disabled = false;
        btnFindUnlocks.textContent = "Find my unlocks";
      }
    }
  }

  // Live Data Ingestion Handler
  function renderLiveError(msg) {
    clearElementChildren(liveStatusRow);
    liveStatusRow.classList.remove("hidden");

    const badge = document.createElement("span");
    badge.className = "live-status-badge live-status-badge-error mono";
    badge.textContent = "ERROR";
    liveStatusRow.appendChild(badge);

    const sep = document.createTextNode(" · ");
    liveStatusRow.appendChild(sep);

    const spanErr = document.createElement("span");
    spanErr.className = "live-status-error-text mono";
    spanErr.textContent = msg;
    liveStatusRow.appendChild(spanErr);
  }

  function renderLiveSuccess(data, newCorpusCount) {
    clearElementChildren(liveStatusRow);
    liveStatusRow.classList.remove("hidden");

    // Source label LIVE or CACHE
    const badge = document.createElement("span");
    const isCache = String(data.source).toLowerCase() === "cache";
    badge.className =
      "live-status-badge mono " +
      (isCache ? "live-status-badge-cache" : "live-status-badge-live");
    badge.textContent = isCache ? "CACHE" : "LIVE";
    liveStatusRow.appendChild(badge);

    // SerpApi {serpapi_ms} ms
    const sMs = data.serpapi_ms != null ? data.serpapi_ms : 0;
    const spanSerp = document.createElement("span");
    spanSerp.textContent = " · SerpApi " + sMs + " ms";
    liveStatusRow.appendChild(spanSerp);

    // Ingest {ingest_ms} ms
    const iMs = data.ingest_ms != null ? data.ingest_ms : 0;
    const spanIngest = document.createElement("span");
    spanIngest.textContent = " · Ingest " + iMs + " ms";
    liveStatusRow.appendChild(spanIngest);

    // SerpApi cache: yes / no / unknown (null means unknown)
    let cacheStatus = "unknown";
    if (data.serpapi_cached === true) cacheStatus = "yes";
    else if (data.serpapi_cached === false) cacheStatus = "no";
    const spanCache = document.createElement("span");
    spanCache.textContent = " · SerpApi cache: " + cacheStatus;
    liveStatusRow.appendChild(spanCache);

    // {retrieved_count} retrieved, {stored_count} new
    const rCount = data.retrieved_count != null ? data.retrieved_count : 0;
    const sCount = data.stored_count != null ? data.stored_count : 0;
    const spanCounts = document.createElement("span");
    spanCounts.textContent = " · " + rCount + " retrieved, " + sCount + " new";
    liveStatusRow.appendChild(spanCounts);

    // Notice text if present
    if (data.notice) {
      const spanNotice = document.createElement("span");
      spanNotice.textContent = " · " + data.notice;
      liveStatusRow.appendChild(spanNotice);
    }

    // Corpus now {n} jobs
    if (newCorpusCount != null) {
      const spanCorpus = document.createElement("span");
      spanCorpus.id = "live-corpus-now";
      spanCorpus.textContent = " · Corpus now " + newCorpusCount + " jobs";
      liveStatusRow.appendChild(spanCorpus);
    }
  }

  async function handleFetchLive() {
    const query = (liveQueryInput.value || "").trim();
    const location = (liveLocationInput.value || "").trim();

    if (!query || !location) {
      renderLiveError("Please enter both a job title and location.");
      return;
    }

    btnFetchLive.disabled = true;
    btnFetchLive.textContent = "Fetching...";

    const controller = new AbortController();
    const timeoutId = setTimeout(function () {
      controller.abort();
    }, 30000);

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          location: location,
          num_results: 10,
          max_pages: 1,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        if (res.status === 429) {
          renderLiveError("Too many requests. Wait a minute and try again.");
          return;
        }

        let detailMsg = "Upstream search failed.";
        try {
          const errData = await res.json();
          if (errData && errData.detail) {
            const detailStr = String(errData.detail);
            if (
              detailStr.toLowerCase().includes("not configured") ||
              detailStr.includes("SERPAPI_API_KEY")
            ) {
              detailMsg = "Live fetching is not configured on this server.";
            } else {
              detailMsg = detailStr;
            }
          }
        } catch (e) {
          // Keep generic detailMsg
        }
        renderLiveError(detailMsg);
        return;
      }

      const searchData = await res.json();

      // Automatically re-run the analysis
      const unlockData = await handleRunAnalysis();
      const newJobsCount =
        unlockData && unlockData.corpus && unlockData.corpus.jobs != null
          ? unlockData.corpus.jobs
          : null;

      // Update header jobs count
      if (newJobsCount != null) {
        pillJobs.textContent = newJobsCount + " jobs indexed";
      }

      renderLiveSuccess(searchData, newJobsCount);
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError") {
        renderLiveError("Request timed out after 30 seconds.");
      } else {
        renderLiveError("Could not reach the server.");
      }
    } finally {
      btnFetchLive.disabled = false;
      btnFetchLive.textContent = "Fetch from Google Jobs";
    }
  }

  // Load sample resume from API
  async function loadSampleResume(triggerRun) {
    try {
      const res = await fetch("/api/sample-resume");
      if (!res.ok) throw new Error("Sample resume fetch failed");
      const data = await res.json();
      if (data && data.text) {
        resumeInput.value = data.text;
        sampleBadge.classList.remove("hidden");
        updateCharCount();
        if (triggerRun) {
          handleRunAnalysis();
        }
      }
    } catch (e) {
      showState("idle");
    }
  }

  // Event Listeners
  resumeInput.addEventListener("input", function () {
    sampleBadge.classList.add("hidden");
    updateCharCount();
  });

  btnSampleResume.addEventListener("click", function () {
    loadSampleResume(true);
  });

  btnFindUnlocks.addEventListener("click", function () {
    handleRunAnalysis();
  });

  thresholdSlider.addEventListener("input", function () {
    const val = thresholdSlider.value;
    thresholdVal.textContent = val + "%";
    matchHelp.textContent =
      "A job counts as a match when you already cover " +
      val +
      "% of its listed skills.";
  });

  thresholdSlider.addEventListener("change", function () {
    if (resumeInput.value.trim()) {
      handleRunAnalysis();
    }
  });

  roleInputs.forEach(function (r) {
    r.addEventListener("change", function () {
      if (resumeInput.value.trim()) {
        handleRunAnalysis();
      }
    });
  });

  locationInputs.forEach(function (l) {
    l.addEventListener("change", function () {
      if (resumeInput.value.trim()) {
        handleRunAnalysis();
      }
    });
  });

  if (btnFetchLive) {
    btnFetchLive.addEventListener("click", handleFetchLive);
  }

  // Initial Boot Sequence
  async function init() {
    updateCharCount();

    // Fetch health metadata for jobs count
    fetch("/api/health")
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (data && data.indexed_jobs_count != null) {
          pillJobs.textContent = data.indexed_jobs_count + " jobs indexed";
        }
      })
      .catch(function () {});

    // Fetch roles metadata for counts
    fetch("/api/roles")
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (data && data.roles) {
          data.roles.forEach(function (r) {
            const labelEl = document.getElementById("role-label-" + r.role);
            if (labelEl) {
              labelEl.textContent = r.name;
            }
          });
        }
      })
      .catch(function () {});

    // First load: auto-load sample resume and run
    loadSampleResume(true);
  }

  init();
})();
