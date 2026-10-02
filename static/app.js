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
  const exportCsvBtn = document.getElementById("exportCsvBtn");
  const exportJsonBtn = document.getElementById("exportJsonBtn");

  // SQL Console elements
  const sqlQueryInput = document.getElementById("sqlQueryInput");
  const runSqlBtn = document.getElementById("runSqlBtn");
  const clearSqlBtn = document.getElementById("clearSqlBtn");
  const sqlRowCount = document.getElementById("sqlRowCount");
  const sqlLatencyBadge = document.getElementById("sqlLatencyBadge");
  const sqlTableWrap = document.getElementById("sqlTableWrap");

  // Resume Matcher elements
  const resumeInput = document.getElementById("resumeInput");
  const resumeErrorMsg = document.getElementById("resumeErrorMsg");
  const atsWordCount = document.getElementById("atsWordCount");
  const atsCharCount = document.getElementById("atsCharCount");
  const matchBtn = document.getElementById("matchBtn");
  const matcherResults = document.getElementById("matcherResults");
  const loadSampleBioBtn = document.getElementById("loadSampleBioBtn");
  const resumeFileInput = document.getElementById("resumeFileInput");
  const clearResumeBtn = document.getElementById("clearResumeBtn");
  const calendarRangeWrap = document.querySelector(".calendar-range-wrap");

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
  let candidateAnalyzedSkills = [];

  // ==================== INITIALIZATION ====================
  initRadarAnimation();
  initSpotlightPhysics();
  initPresetChips();
  initDrawerControls();
  initFieldValidation();
  initFilterControls();
  initCustomDropdowns();
  initExportControls();
  initSqlConsole();
  initAtsControls();
  initKeyboardShortcuts();
  checkHealth();
  refreshDashboard();

  // ==================== TOAST NOTIFICATION SYSTEM ====================
  function showToast(message, type = "info", duration = 4000) {
    if (!toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `toast-pill toast-${type} gap-icon`;
    toast.setAttribute("role", "alert");

    const toastIcons = {
      success:
        '<svg class="ui-icon ui-icon-md text-emerald" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
      error:
        '<svg class="ui-icon ui-icon-md text-rose" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
      warning:
        '<svg class="ui-icon ui-icon-md text-amber" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
      info: '<svg class="ui-icon ui-icon-md text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>',
    };

    const iconSpan = document.createElement("span");
    iconSpan.innerHTML = toastIcons[type] || toastIcons.info;
    toast.appendChild(iconSpan);

    const textSpan = document.createElement("span");
    textSpan.textContent = message;
    toast.appendChild(textSpan);

    const closeBtn = document.createElement("button");
    closeBtn.className = "toast-close-btn";
    closeBtn.innerHTML =
      '<svg class="ui-icon ui-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
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

  function validateFilterKeyword(val) {
    if (!val) return { valid: true, message: "" };
    if (val.length > 100) {
      return {
        valid: false,
        message: "Filter keyword must not exceed 100 characters.",
      };
    }
    const unsafeChars = /[<>"';`]/;
    if (unsafeChars.test(val)) {
      return {
        valid: false,
        message: "Restricted characters detected (< > \" ' ; `).",
      };
    }
    return { valid: true, message: "" };
  }

  function validateDateRange(from, to) {
    if (!from && !to) return { valid: true, message: "" };
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (from && !dateRegex.test(from)) {
      return {
        valid: false,
        message: "From Date must follow YYYY-MM-DD format.",
      };
    }
    if (to && !dateRegex.test(to)) {
      return {
        valid: false,
        message: "To Date must follow YYYY-MM-DD format.",
      };
    }
    if (from && to && from > to) {
      return {
        valid: false,
        message: "From Date cannot be later than To Date.",
      };
    }
    return { valid: true, message: "" };
  }

  function validateResume(text) {
    const trimmed = text.trim();
    if (!trimmed) {
      return {
        valid: false,
        message: "Resume skill inventory cannot be empty.",
      };
    }
    if (trimmed.length < 10) {
      return {
        valid: false,
        message: "Resume text is too brief (minimum 10 characters required).",
      };
    }
    const words = trimmed.split(/\s+/).length;
    if (words < 2) {
      return {
        valid: false,
        message:
          "Please enter at least 2 distinct technical skills or phrases.",
      };
    }
    if (trimmed.length > 50000) {
      return {
        valid: false,
        message: "Resume text exceeds 50,000 character maximum limit.",
      };
    }
    return { valid: true, message: "" };
  }

  function initFieldValidation() {
    // 1. Search Query Validation
    if (queryInput) {
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
      handleQueryInput();
    }

    // 2. Filter Keyword Validation
    if (filterKeyword) {
      filterKeyword.addEventListener("input", () => {
        const check = validateFilterKeyword(filterKeyword.value);
        if (!check.valid) {
          filterKeyword.classList.add("is-invalid");
          showToast(check.message, "warning", 3000);
        } else {
          filterKeyword.classList.remove("is-invalid");
        }
      });
    }

    // 3. Resume Real-Time Validation
    if (resumeInput) {
      resumeInput.addEventListener("input", () => {
        const val = resumeInput.value.trim();
        if (!val) {
          resumeInput.classList.remove("is-valid", "is-invalid");
          if (resumeErrorMsg) resumeErrorMsg.style.display = "none";
          return;
        }
        const check = validateResume(val);
        if (check.valid) {
          resumeInput.classList.remove("is-invalid");
          resumeInput.classList.add("is-valid");
          if (resumeErrorMsg) {
            resumeErrorMsg.style.display = "none";
            resumeErrorMsg.textContent = "";
          }
        } else {
          resumeInput.classList.remove("is-valid");
          resumeInput.classList.add("is-invalid");
          if (resumeErrorMsg) {
            resumeErrorMsg.style.display = "block";
            resumeErrorMsg.textContent = check.message;
          }
        }
      });
    }
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

        const dateCheck = validateDateRange(from, to);
        if (!dateCheck.valid) {
          if (calendarRangeWrap) calendarRangeWrap.classList.add("is-invalid");
          showToast(dateCheck.message, "warning");
          filterToDate.value = from;
        } else {
          if (calendarRangeWrap)
            calendarRangeWrap.classList.remove("is-invalid");
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
        if (calendarRangeWrap) calendarRangeWrap.classList.remove("is-invalid");
        clearDateBtn.style.display = "none";
        updateResetButtonVisibility();
        loadJobs();
      });
    }

    if (clearAllFiltersBtn) {
      clearAllFiltersBtn.addEventListener("click", () => {
        if (filterKeyword) filterKeyword.value = "";
        if (clearKeywordBtn) clearKeywordBtn.style.display = "none";
        if (filterWorkType) {
          filterWorkType.value = "";
          if (typeof filterWorkType._syncCustomDropdown === "function") {
            filterWorkType._syncCustomDropdown();
          }
        }
        if (filterFromDate) filterFromDate.value = "";
        if (filterToDate) filterToDate.value = "";
        if (calendarRangeWrap) calendarRangeWrap.classList.remove("is-invalid");
        if (clearDateBtn) clearDateBtn.style.display = "none";
        if (filterSalaryOnly) filterSalaryOnly.checked = false;
        if (filterSort) {
          filterSort.value = "newest";
          if (typeof filterSort._syncCustomDropdown === "function") {
            filterSort._syncCustomDropdown();
          }
        }

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

  // ==================== 4. EXPORT DATA CONTROLS ====================
  function initExportControls() {
    const exportDropdownWrap = document.getElementById("exportDropdownWrap");
    const exportDropdownTrigger = document.getElementById(
      "exportDropdownTrigger",
    );

    if (exportDropdownTrigger && exportDropdownWrap) {
      exportDropdownTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        const isOpen = exportDropdownWrap.classList.contains("is-open");
        closeAllDropdowns(exportDropdownWrap);
        if (!isOpen) {
          exportDropdownWrap.classList.add("is-open");
          exportDropdownTrigger.setAttribute("aria-expanded", "true");
        } else {
          exportDropdownWrap.classList.remove("is-open");
          exportDropdownTrigger.setAttribute("aria-expanded", "false");
        }
      });
    }

    if (exportCsvBtn) {
      exportCsvBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (exportDropdownWrap) {
          exportDropdownWrap.classList.remove("is-open");
          if (exportDropdownTrigger) {
            exportDropdownTrigger.setAttribute("aria-expanded", "false");
          }
        }
        triggerExport("csv");
      });
    }
    if (exportJsonBtn) {
      exportJsonBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (exportDropdownWrap) {
          exportDropdownWrap.classList.remove("is-open");
          if (exportDropdownTrigger) {
            exportDropdownTrigger.setAttribute("aria-expanded", "false");
          }
        }
        triggerExport("json");
      });
    }
  }

  // ==================== CUSTOM RADAR DROPDOWNS ====================
  function initCustomDropdowns() {
    const selects = document.querySelectorAll(
      "select.custom-select, select.filter-select",
    );

    selects.forEach((select) => {
      if (select.dataset.radarCustomized) return;
      select.dataset.radarCustomized = "true";

      // Visually hide native select but retain in DOM for form processing & values
      select.classList.add("radar-select-native-hidden");

      // Wrap in radar-select-wrapper
      const wrapper = document.createElement("div");
      wrapper.className = "radar-select-wrapper";
      if (select.classList.contains("filter-select")) {
        wrapper.classList.add("filter-select-wrapper");
      }
      select.parentNode.insertBefore(wrapper, select);
      wrapper.appendChild(select);

      // Trigger button
      const trigger = document.createElement("button");
      trigger.type = "button";
      trigger.className = "radar-select-trigger font-mono";
      trigger.setAttribute("aria-haspopup", "listbox");
      trigger.setAttribute("aria-expanded", "false");

      const valueWrap = document.createElement("span");
      valueWrap.className = "radar-select-value";

      const chevronSvg = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "svg",
      );
      chevronSvg.setAttribute("class", "radar-select-chevron");
      chevronSvg.setAttribute("viewBox", "0 0 24 24");
      chevronSvg.setAttribute("fill", "none");
      chevronSvg.setAttribute("stroke", "currentColor");
      chevronSvg.setAttribute("stroke-width", "2");
      chevronSvg.setAttribute("stroke-linecap", "round");
      chevronSvg.setAttribute("stroke-linejoin", "round");
      chevronSvg.setAttribute("aria-hidden", "true");
      chevronSvg.innerHTML = '<polyline points="6 9 12 15 18 9"></polyline>';

      trigger.appendChild(valueWrap);
      trigger.appendChild(chevronSvg);
      wrapper.appendChild(trigger);

      // Floating Menu Panel
      const panel = document.createElement("div");
      panel.className = "radar-select-panel";
      panel.setAttribute("role", "listbox");
      panel.setAttribute("tabindex", "-1");

      function buildOptions() {
        panel.innerHTML = "";
        Array.from(select.options).forEach((opt) => {
          const item = document.createElement("div");
          item.className = "radar-select-option";
          item.setAttribute("role", "option");
          item.dataset.value = opt.value;
          item.dataset.text = opt.text;
          const isSelected = opt.value === select.value;
          item.setAttribute("aria-selected", isSelected ? "true" : "false");
          if (isSelected) {
            item.classList.add("is-selected");
          }

          const iconHtml = getOptionIconHtml(select.id, opt.value, opt.text);

          item.innerHTML = `
            <span class="radar-select-option-content">
              ${iconHtml}
              <span>${opt.text}</span>
            </span>
            <svg class="radar-select-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          `;

          item.addEventListener("click", (e) => {
            e.stopPropagation();
            selectOption(opt.value);
          });

          panel.appendChild(item);
        });
      }

      function updateTriggerDisplay() {
        const selectedOpt = select.options[select.selectedIndex];
        if (selectedOpt) {
          const icon = getOptionIconHtml(
            select.id,
            selectedOpt.value,
            selectedOpt.text,
          );
          valueWrap.innerHTML = `${icon}<span>${selectedOpt.text}</span>`;
        }
      }

      function selectOption(val) {
        select.value = val;
        select._syncCustomDropdown();
        closeDropdown();
        select.dispatchEvent(new Event("change", { bubbles: true }));
        select.dispatchEvent(new Event("input", { bubbles: true }));
        trigger.focus();
      }

      function toggleDropdown() {
        if (wrapper.classList.contains("is-open")) {
          closeDropdown();
        } else {
          openDropdown();
        }
      }

      function openDropdown() {
        closeAllDropdowns(wrapper);

        // Viewport collision detection
        const rect = wrapper.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        if (spaceBelow < 220 && rect.top > 220) {
          wrapper.classList.add("drop-up");
        } else {
          wrapper.classList.remove("drop-up");
        }

        wrapper.classList.add("is-open");
        trigger.setAttribute("aria-expanded", "true");

        const parentCard = wrapper.closest(".spotlight-card");
        if (parentCard) parentCard.classList.add("has-open-dropdown");

        // Focus current or first option
        const selectedItem =
          panel.querySelector(".radar-select-option.is-selected") ||
          panel.querySelector(".radar-select-option");
        if (selectedItem) {
          panel
            .querySelectorAll(".radar-select-option")
            .forEach((o) => o.classList.remove("is-focused"));
          selectedItem.classList.add("is-focused");
          selectedItem.scrollIntoView({ block: "nearest" });
        }
      }

      function closeDropdown() {
        wrapper.classList.remove("is-open");
        trigger.setAttribute("aria-expanded", "false");
        panel
          .querySelectorAll(".radar-select-option")
          .forEach((o) => o.classList.remove("is-focused"));

        const parentCard = wrapper.closest(".spotlight-card");
        if (parentCard) parentCard.classList.remove("has-open-dropdown");
      }

      select._syncCustomDropdown = () => {
        updateTriggerDisplay();
        panel.querySelectorAll(".radar-select-option").forEach((opt) => {
          const isSel = opt.dataset.value === select.value;
          opt.classList.toggle("is-selected", isSel);
          opt.setAttribute("aria-selected", isSel ? "true" : "false");
        });
      };

      select.addEventListener("change", select._syncCustomDropdown);

      trigger.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleDropdown();
      });

      trigger.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (!wrapper.classList.contains("is-open")) {
            openDropdown();
          }
        } else if (e.key === "Escape") {
          closeDropdown();
        }
      });

      wrapper.addEventListener("keydown", (e) => {
        if (!wrapper.classList.contains("is-open")) return;
        const items = Array.from(
          panel.querySelectorAll(".radar-select-option"),
        );
        let focusedIdx = items.findIndex((i) =>
          i.classList.contains("is-focused"),
        );

        if (e.key === "ArrowDown") {
          e.preventDefault();
          const nextIdx = focusedIdx < items.length - 1 ? focusedIdx + 1 : 0;
          items.forEach((i) => i.classList.remove("is-focused"));
          items[nextIdx].classList.add("is-focused");
          items[nextIdx].scrollIntoView({ block: "nearest" });
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          const prevIdx = focusedIdx > 0 ? focusedIdx - 1 : items.length - 1;
          items.forEach((i) => i.classList.remove("is-focused"));
          items[prevIdx].classList.add("is-focused");
          items[prevIdx].scrollIntoView({ block: "nearest" });
        } else if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (focusedIdx >= 0 && items[focusedIdx]) {
            selectOption(items[focusedIdx].dataset.value);
          }
        } else if (e.key === "Escape") {
          e.preventDefault();
          closeDropdown();
          trigger.focus();
        } else if (e.key === "Tab") {
          closeDropdown();
        }
      });

      buildOptions();
      updateTriggerDisplay();
      wrapper.appendChild(panel);
    });
  }

  function getOptionIconHtml(selectId, value, text) {
    if (selectId === "locationInput") {
      if (value === "Remote" || (value && value.includes("United States"))) {
        return '<svg class="radar-select-option-icon text-emerald" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>';
      }
      return '<svg class="radar-select-option-icon text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>';
    }
    if (selectId === "datePostedInput") {
      return '<svg class="radar-select-option-icon text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>';
    }
    if (selectId === "resultsLimit") {
      return '<svg class="radar-select-option-icon text-amber" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>';
    }
    if (selectId === "filterWorkType") {
      if (value === "Remote") {
        return '<svg class="radar-select-option-icon text-emerald" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>';
      }
      if (value === "Hybrid") {
        return '<svg class="radar-select-option-icon text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><line x1="1.05" y1="12" x2="7" y2="12"></line><line x1="17.01" y1="12" x2="22.96" y2="12"></line></svg>';
      }
      if (value === "On-site") {
        return '<svg class="radar-select-option-icon text-amber" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><line x1="9" y1="22" x2="9" y2="22.01"></line><line x1="15" y1="22" x2="15" y2="22.01"></line></svg>';
      }
      return '<svg class="radar-select-option-icon text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>';
    }
    if (selectId === "filterSort") {
      return '<svg class="radar-select-option-icon text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>';
    }
    return "";
  }

  function closeAllDropdowns(except = null) {
    document
      .querySelectorAll(
        ".radar-select-wrapper.is-open, .export-dropdown-wrap.is-open",
      )
      .forEach((el) => {
        if (el !== except) {
          el.classList.remove("is-open");
          const trigger = el.querySelector(
            ".radar-select-trigger, #exportDropdownTrigger",
          );
          if (trigger) trigger.setAttribute("aria-expanded", "false");
          const parentCard = el.closest(".spotlight-card");
          if (parentCard) parentCard.classList.remove("has-open-dropdown");
        }
      });
  }

  // Global document click listener for outside clicks
  document.addEventListener("click", (e) => {
    if (
      !e.target.closest(".radar-select-wrapper") &&
      !e.target.closest(".export-dropdown-wrap")
    ) {
      closeAllDropdowns();
    }
  });

  function triggerExport(format) {
    const keyword = filterKeyword ? filterKeyword.value.trim() : "";
    const locationType = filterWorkType ? filterWorkType.value : "";
    const fromDate = filterFromDate ? filterFromDate.value : "";
    const toDate = filterToDate ? filterToDate.value : "";
    const hasSalary = filterSalaryOnly ? filterSalaryOnly.checked : false;

    const params = new URLSearchParams();
    params.append("format", format);
    if (keyword) params.append("keyword", keyword);
    if (locationType) params.append("location_type", locationType);
    if (fromDate) params.append("from_date", fromDate);
    if (toDate) params.append("to_date", toDate);
    if (hasSalary) params.append("has_salary", "true");

    const exportUrl = `/api/export?${params.toString()}`;
    const link = document.createElement("a");
    link.href = exportUrl;
    link.setAttribute("download", `serpapi_jobs_radar.${format}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast(
      `Streaming ${format.toUpperCase()} dataset from DuckDB database...`,
      "success",
    );
  }

  // ==================== 5. LIVE DUCKDB SQL QUERY CONSOLE ====================
  function initSqlConsole() {
    if (runSqlBtn) {
      runSqlBtn.addEventListener("click", executeDuckDbSql);
    }

    if (clearSqlBtn) {
      clearSqlBtn.addEventListener("click", () => {
        if (sqlQueryInput) {
          sqlQueryInput.value = "";
          sqlQueryInput.focus();
        }
        if (sqlRowCount) sqlRowCount.textContent = "Query input cleared";
        if (sqlTableWrap) {
          sqlTableWrap.innerHTML =
            '<p class="empty-state font-mono">Enter a SELECT query or click an analytical preset above.</p>';
        }
      });
    }

    const presetBtns = document.querySelectorAll(".sql-preset-btn");
    presetBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const sql = btn.getAttribute("data-sql");
        if (sql && sqlQueryInput) {
          sqlQueryInput.value = sql;
          executeDuckDbSql();
        }
      });
    });

    if (sqlQueryInput) {
      sqlQueryInput.addEventListener("keydown", (e) => {
        if (e.ctrlKey && e.key === "Enter") {
          e.preventDefault();
          executeDuckDbSql();
        }
      });
    }
  }

  async function executeDuckDbSql() {
    if (!sqlQueryInput) return;
    const query = sqlQueryInput.value.trim();
    if (!query) {
      showToast("Please enter an analytical SQL query.", "warning");
      sqlQueryInput.focus();
      return;
    }

    if (!query.toUpperCase().startsWith("SELECT")) {
      showToast(
        "Only read-only SELECT queries are permitted in the analytical console.",
        "error",
      );
      return;
    }

    if (runSqlBtn) {
      runSqlBtn.disabled = true;
      runSqlBtn.innerHTML =
        '<svg class="ui-icon ui-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg> Executing...';
    }

    if (sqlRowCount)
      sqlRowCount.textContent = "Executing in-memory OLAP query...";

    try {
      const res = await fetch("/api/sql", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Query execution failed.");
      }

      if (sqlLatencyBadge) {
        sqlLatencyBadge.innerHTML = `<svg class="ui-icon ui-icon-xs text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg> DuckDB: ${data.latency_ms}ms`;
      }
      if (statLatency) {
        statLatency.textContent = `${data.latency_ms} ms`;
      }

      if (sqlRowCount) {
        sqlRowCount.textContent = `${data.row_count} ${data.row_count === 1 ? "row" : "rows"} (${data.latency_ms} ms)`;
      }

      renderSqlResults(data);
      showToast(
        `DuckDB returned ${data.row_count} rows in ${data.latency_ms} ms.`,
        "success",
      );
    } catch (err) {
      if (sqlTableWrap) {
        sqlTableWrap.innerHTML = `<p class="empty-state font-mono text-rose" style="padding: 16px;">Execution Error: ${escapeHtml(err.message)}</p>`;
      }
      if (sqlRowCount) sqlRowCount.textContent = "Execution halted";
      showToast(err.message, "error");
    } finally {
      if (runSqlBtn) {
        runSqlBtn.disabled = false;
        runSqlBtn.innerHTML =
          '<svg class="ui-icon ui-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Execute Query';
      }
    }
  }

  function renderSqlResults(data) {
    if (!sqlTableWrap) return;

    if (!data.rows || data.rows.length === 0) {
      sqlTableWrap.innerHTML =
        '<p class="empty-state font-mono">0 rows returned matching query filter.</p>';
      return;
    }

    const colsHtml = (data.columns || [])
      .map((col) => `<th>${escapeHtml(col)}</th>`)
      .join("");

    const rowsHtml = (data.rows || [])
      .map((row) => {
        const cells = row
          .map((cell) => `<td>${escapeHtml(cell)}</td>`)
          .join("");
        return `<tr>${cells}</tr>`;
      })
      .join("");

    sqlTableWrap.innerHTML = `
      <table class="sql-table">
        <thead><tr>${colsHtml}</tr></thead>
        <tbody>${rowsHtml}</tbody>
      </table>
    `;
  }

  // ==================== 6. ATS RESUME MATCHER CONTROLS ====================
  function initAtsControls() {
    if (resumeInput) {
      resumeInput.addEventListener("input", updateResumeCounters);
      updateResumeCounters();
    }

    if (loadSampleBioBtn) {
      loadSampleBioBtn.addEventListener("click", () => {
        resumeInput.value =
          "Senior Software Engineer with 4+ years building high-throughput analytical services using Python, DuckDB, FastAPI, PostgreSQL, and Docker. Experienced in PyTorch ML inference, Next.js TypeScript frontends, and GeoPandas telemetry.";
        if (resumeErrorMsg) resumeErrorMsg.style.display = "none";
        resumeInput.classList.remove("is-invalid");
        resumeInput.classList.add("is-valid");
        updateResumeCounters();
        showToast("Sample technical candidate bio loaded.", "info");
      });
    }

    if (resumeFileInput) {
      resumeFileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const allowedExts = [".txt", ".md", ".json", ".csv"];
        const fileName = file.name.toLowerCase();
        const isAllowed = allowedExts.some((ext) => fileName.endsWith(ext));
        if (!isAllowed) {
          showToast(
            "Invalid file type. Only .txt, .md, .json, and .csv files are supported.",
            "error",
          );
          resumeFileInput.value = "";
          return;
        }

        if (file.size > 2 * 1024 * 1024) {
          showToast("File size exceeds 2MB limit.", "error");
          resumeFileInput.value = "";
          return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
          resumeInput.value = event.target.result;
          if (resumeErrorMsg) resumeErrorMsg.style.display = "none";
          resumeInput.classList.remove("is-invalid");
          resumeInput.classList.add("is-valid");
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
        resumeInput.classList.remove("is-valid", "is-invalid");
        if (resumeErrorMsg) resumeErrorMsg.style.display = "none";
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
    const check = validateResume(text);

    if (!check.valid) {
      resumeInput.classList.remove("is-valid");
      resumeInput.classList.add("is-invalid");
      if (resumeErrorMsg) {
        resumeErrorMsg.style.display = "block";
        resumeErrorMsg.textContent = check.message;
      }
      showToast(check.message, "warning");
      resumeInput.focus();
      return;
    }

    resumeInput.classList.remove("is-invalid");
    resumeInput.classList.add("is-valid");
    if (resumeErrorMsg) resumeErrorMsg.style.display = "none";

    matchBtn.disabled = true;
    matchBtn.innerHTML =
      '<svg class="ui-icon ui-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg> Analyzing Market Alignment...';

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
      matchBtn.innerHTML =
        '<svg class="ui-icon ui-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg> Calculate Skill Alignment';
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

        const remoteBadge = isRemote
          ? '<span class="badge badge-remote gap-icon"><svg class="ui-icon ui-icon-xs text-emerald" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.55a11 11 0 0 1 14.08 0"></path><path d="M1.42 9a16 16 0 0 1 21.16 0"></path><path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path><line x1="12" y1="20" x2="12.01" y2="20"></line></svg>REMOTE</span>'
          : '<span class="badge gap-icon"><svg class="ui-icon ui-icon-xs text-sub" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><line x1="9" y1="22" x2="9" y2="22.01"></line><line x1="15" y1="22" x2="15" y2="22.01"></line><line x1="9" y1="6" x2="9.01" y2="6"></line><line x1="15" y1="6" x2="15.01" y2="6"></line><line x1="9" y1="10" x2="9.01" y2="10"></line><line x1="15" y1="10" x2="15.01" y2="10"></line><line x1="9" y1="14" x2="9.01" y2="14"></line><line x1="15" y1="15" x2="15.01" y2="14"></line></svg>ON-SITE</span>';

        const viaBadge = `<span class="badge gap-icon"><svg class="ui-icon ui-icon-xs text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>${escapeHtml(job.via || "Direct Portal")}</span>`;

        const salaryBadge = job.salary
          ? `<span class="badge badge-salary gap-icon"><svg class="ui-icon ui-icon-xs text-amber" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>${escapeHtml(job.salary)}</span>`
          : "";

        let fitBadge = "";
        if (candidateAnalyzedSkills && candidateAnalyzedSkills.length > 0) {
          const reqSkills = Array.isArray(job.skills_required)
            ? job.skills_required
            : [];
          if (reqSkills.length > 0) {
            const lowerCandidateSkills = candidateAnalyzedSkills.map((s) =>
              s.toLowerCase(),
            );
            const matchedCount = reqSkills.filter((s) =>
              lowerCandidateSkills.includes(s.toLowerCase()),
            ).length;
            const fitPct = Math.round((matchedCount / reqSkills.length) * 100);
            if (fitPct > 0) {
              fitBadge = `<span class="badge badge-fit gap-icon"><svg class="ui-icon ui-icon-xs text-emerald" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"></polyline></svg>${fitPct}% FIT</span>`;
            }
          }
        }

        return `
        <article class="job-stream-card" data-index="${idx}" tabindex="0" role="button" aria-label="View details for ${escapeHtml(job.title)}">
          <div class="job-card-header">
            <div>
              <h4 class="job-card-title">${escapeHtml(job.title)}</h4>
              <div class="job-card-company">${escapeHtml(job.company_name)}</div>
            </div>
            <div class="badge-row">
              ${remoteBadge}
              ${viaBadge}
              ${salaryBadge}
              ${fitBadge}
            </div>
          </div>
          <p class="job-card-snippet">${escapeHtml(truncate(job.description, 200))}</p>
          <div class="job-card-footer">
            <span class="job-card-location gap-icon">
              <svg class="ui-icon ui-icon-xs text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
              ${escapeHtml(job.location || "Location Not Stated")} &bull;
              <svg class="ui-icon ui-icon-xs text-sub" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
              ${escapeHtml(job.posted_at || "Indexed")}
            </span>
            <span class="inspect-trigger gap-icon">
              Inspect Details
              <svg class="ui-icon ui-icon-xs text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
            </span>
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
  function copyTextToClipboard(text, successMsg = "Copied to clipboard!") {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard
        .writeText(text)
        .then(() => showToast(successMsg, "success"))
        .catch(() => fallbackCopyText(text, successMsg));
    } else {
      fallbackCopyText(text, successMsg);
    }
  }

  function fallbackCopyText(text, successMsg) {
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      textArea.style.top = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const successful = document.execCommand("copy");
      document.body.removeChild(textArea);
      if (successful) {
        showToast(successMsg, "success");
      } else {
        showToast("Unable to copy to clipboard.", "warning");
      }
    } catch (err) {
      showToast("Unable to copy to clipboard.", "warning");
    }
  }

  function initDrawerControls() {
    if (closeDrawerBtn) closeDrawerBtn.addEventListener("click", closeDrawer);
    if (drawerBackdrop) drawerBackdrop.addEventListener("click", closeDrawer);

    if (drawerCopyLinkBtn) {
      drawerCopyLinkBtn.addEventListener("click", () => {
        if (!currentDrawerJob) return;
        const link = currentDrawerJob.apply_link || window.location.href;
        copyTextToClipboard(
          link,
          "Official application link copied to clipboard!",
        );
      });
    }
  }

  function openDrawer(job) {
    currentDrawerJob = job;
    drawerJobTitle.textContent = job.title;
    drawerJobCompany.textContent = job.company_name;
    drawerLocation.textContent = `${job.location || "Location Not Stated"} • Schedule: ${job.schedule_type || "Standard"}`;

    const remoteDrawerBadge = job.work_from_home
      ? '<span class="badge badge-remote gap-icon"><svg class="ui-icon ui-icon-xs text-emerald" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.55a11 11 0 0 1 14.08 0"></path><path d="M1.42 9a16 16 0 0 1 21.16 0"></path><path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path><line x1="12" y1="20" x2="12.01" y2="20"></line></svg>REMOTE</span>'
      : '<span class="badge gap-icon"><svg class="ui-icon ui-icon-xs text-sub" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><line x1="9" y1="22" x2="9" y2="22.01"></line><line x1="15" y1="22" x2="15" y2="22.01"></line><line x1="9" y1="6" x2="9.01" y2="6"></line><line x1="15" y1="6" x2="15.01" y2="6"></line><line x1="9" y1="10" x2="9.01" y2="10"></line><line x1="15" y1="10" x2="15.01" y2="10"></line><line x1="9" y1="14" x2="9.01" y2="14"></line><line x1="15" y1="15" x2="15.01" y2="14"></line></svg>ON-SITE</span>';

    drawerBadges.innerHTML = `
      ${remoteDrawerBadge}
      <span class="badge gap-icon"><svg class="ui-icon ui-icon-xs text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>${escapeHtml(job.via || "Direct")}</span>
      <span class="badge font-mono text-cyan gap-icon"><svg class="ui-icon ui-icon-xs text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>${escapeHtml(job.posted_at || "Indexed")}</span>
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
    jobDetailDrawer.classList.add("is-open");
    drawerBackdrop.classList.add("open");
    drawerBackdrop.classList.add("is-open");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    jobDetailDrawer.classList.remove("open");
    jobDetailDrawer.classList.remove("is-open");
    drawerBackdrop.classList.remove("open");
    drawerBackdrop.classList.remove("is-open");
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

    candidateAnalyzedSkills = data.matched_skills || [];

    const matchedPills =
      data.matched_skills.length > 0
        ? data.matched_skills
            .map(
              (s) =>
                `<span class="tax-pill pill-matched clickable-pill font-mono" data-skill="${escapeHtml(s)}" role="button" tabindex="0" title="Filter job corpus for ${escapeHtml(s)}">${escapeHtml(s)}</span>`,
            )
            .join("")
        : '<span class="text-sub font-mono">None detected</span>';

    const missingPills =
      data.missing_skills.length > 0
        ? data.missing_skills
            .map(
              (s) =>
                `<span class="tax-pill pill-missing clickable-pill font-mono" data-skill="${escapeHtml(s)}" role="button" tabindex="0" title="Filter job corpus for ${escapeHtml(s)}">${escapeHtml(s)}</span>`,
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
        <div class="ats-taxonomy-title font-mono gap-icon">
          <svg class="ui-icon ui-icon-xs text-emerald" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          MATCHED PREREQUISITES (${data.matched_skills.length})
        </div>
        <div class="pill-cloud">${matchedPills}</div>
      </div>

      <div class="ats-taxonomy-group">
        <div class="ats-taxonomy-title font-mono gap-icon">
          <svg class="ui-icon ui-icon-xs text-rose" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          HIGH-DEMAND GAPS (${data.missing_skills.length})
        </div>
        <div class="pill-cloud">${missingPills}</div>
      </div>
    `;

    // Attach click listeners to skill pills for deep-link filtering
    const pills = matcherResults.querySelectorAll(".clickable-pill");
    pills.forEach((p) => {
      const handlePillClick = () => {
        const skill = p.getAttribute("data-skill");
        if (skill && filterKeyword) {
          filterKeyword.value = skill;
          filterKeyword.dispatchEvent(new Event("input"));
          updateResetButtonVisibility();
          loadJobs();
          document
            .querySelector(".jobs-section")
            ?.scrollIntoView({ behavior: "smooth" });
          showToast(`Filtered job stream for skill: ${skill}`, "info");
        }
      };
      p.addEventListener("click", handlePillClick);
      p.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handlePillClick();
        }
      });
    });

    // Re-render job stream to display fit percentage badges
    if (cachedJobs && cachedJobs.length > 0) {
      renderJobs(cachedJobs);
    }
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
          if (typeof locationInput._syncCustomDropdown === "function") {
            locationInput._syncCustomDropdown();
          }
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
      ctxMain.strokeStyle = "rgba(167, 139, 250, 0.12)";
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
      grad.addColorStop(0, "rgba(167, 139, 250, 0.35)");
      grad.addColorStop(1, "rgba(124, 58, 237, 0)");

      ctxMain.fillStyle = grad;
      ctxMain.beginPath();
      ctxMain.moveTo(0, 0);
      ctxMain.arc(0, 0, maxR, -0.4, 0);
      ctxMain.closePath();
      ctxMain.fill();

      // Sweep Leading Line
      ctxMain.strokeStyle = "#a78bfa";
      ctxMain.lineWidth = 2;
      ctxMain.shadowColor = "#7c3aed";
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
      ctxMini.strokeStyle = "rgba(167, 139, 250, 0.3)";
      ctxMini.lineWidth = 1;
      ctxMini.beginPath();
      ctxMini.arc(mcx, mcy, mmaxR, 0, Math.PI * 2);
      ctxMini.stroke();

      ctxMini.save();
      ctxMini.translate(mcx, mcy);
      ctxMini.rotate(angle);
      ctxMini.strokeStyle = "#a78bfa";
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
