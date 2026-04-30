/**
 * CodeExec AI — Frontend Application Logic
 * Dataset upload, AI prompt code generation, code editing, execution.
 */
(function () {
    "use strict";

    // --- DOM References ---
    // NOTE: codeEditor textarea is no longer in the DOM.
    // All code reads/writes go through editorAPI (Monaco abstraction).
    const lineNumbers = document.getElementById("lineNumbers"); // hidden, kept for safety
    const runBtn = document.getElementById("runBtn");
    const clearBtn = document.getElementById("clearBtn");
    const copyCodeBtn = document.getElementById("copyCodeBtn");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    const examplesList = document.getElementById("examplesList");
    const historyList = document.getElementById("historyList");
    const outputWelcome = document.getElementById("outputWelcome");
    const outputResults = document.getElementById("outputResults");
    const execOverlay = document.getElementById("execOverlay");
    const genOverlay = document.getElementById("genOverlay");
    const toastContainer = document.getElementById("toastContainer");
    const charCount = document.getElementById("charCount");
    const lineCount = document.getElementById("lineCount");
    const statusText = document.querySelector(".status-text");
    const statusDot = document.querySelector(".status-dot");
    const statRuns = document.getElementById("statRuns");
    const statSuccess = document.getElementById("statSuccess");
    const statAvgMs = document.getElementById("statAvgMs");

    // Monaco editor instance and abstraction API
    let monacoInstance = null;
    const editorAPI = {
        getValue: () => monacoInstance ? monacoInstance.getValue() : "",
        setValue: (code) => { if (monacoInstance) { monacoInstance.setValue(code); updateEditorInfo(); } },
        focus:    () => { if (monacoInstance) monacoInstance.focus(); }
    };

    // Mode tabs
    const modeEditor = document.getElementById("modeEditor");
    const modePrompt = document.getElementById("modePrompt");
    const editorPanel = document.getElementById("editorPanel");
    const promptPanel = document.getElementById("promptPanel");

    // Dataset
    const uploadZone = document.getElementById("uploadZone");
    const fileInput = document.getElementById("fileInput");
    const datasetList = document.getElementById("datasetList");

    // Prompt
    const promptInput = document.getElementById("promptInput");
    const generateBtn = document.getElementById("generateBtn");
    const generatedPreview = document.getElementById("generatedPreview");
    const generatedCode = document.getElementById("generatedCode");
    const generatedExplanation = document.getElementById("generatedExplanation");
    const generatedSuggestions = document.getElementById("generatedSuggestions");
    const explanationMode = document.getElementById("explanationMode");
    const debugToggle = document.getElementById("debugToggle");
    const copyGenBtn = document.getElementById("copyGenBtn");
    const editGenBtn = document.getElementById("editGenBtn");
    const runGenBtn = document.getElementById("runGenBtn");

    // --- State ---
    let history = [];
    let totalRuns = 0;
    let totalSuccess = 0;
    let totalTimeMs = 0;
    let lastGeneratedCode = "";
    let currentSessionId = null;

    // --- Resilient Fetch Utility ---
    // Handles retries, timeouts, and server-down gracefully
    async function resilientFetch(url, options, config) {
        config = config || {};
        var maxRetries = config.retries || 3;
        var timeoutMs = config.timeout || 120000; // 2 min default
        var retryDelay = config.retryDelay || 2000;
        var onRetry = config.onRetry || function() {};

        for (var attempt = 1; attempt <= maxRetries; attempt++) {
            var controller = new AbortController();
            var timeoutId = setTimeout(function() { controller.abort(); }, timeoutMs);

            try {
                var fetchOpts = Object.assign({}, options, { signal: controller.signal });
                var response = await fetch(url, fetchOpts);
                clearTimeout(timeoutId);
                return response;
            } catch (err) {
                clearTimeout(timeoutId);
                var isLast = attempt === maxRetries;
                var isAbort = err.name === 'AbortError';
                var isNetwork = err.message && err.message.indexOf('Failed to fetch') !== -1;

                if (isAbort && isLast) {
                    throw new Error('The request timed out. The AI model may be overloaded — please try again in a moment.');
                } else if (isNetwork && isLast) {
                    throw new Error('Cannot reach the server. Make sure it is running on http://localhost:8000');
                } else if (isLast) {
                    throw err;
                }

                // Retry with backoff
                var waitMs = retryDelay * attempt;
                onRetry(attempt, maxRetries, waitMs);
                await new Promise(function(r) { setTimeout(r, waitMs); });
            }
        }
    }

    // --- Init ---
    function init() {
        loadExamples();
        loadDatasets();
        bindEvents();
        initMonaco();
    }

    // --- Monaco Editor Initialization ---
    function initMonaco() {
        require.config({
            paths: { vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs" }
        });

        require(["vs/editor/editor.main"], function () {
            // Define a custom warm amber dark theme matching the app's palette
            monaco.editor.defineTheme("codeexec-dark", {
                base: "vs-dark",
                inherit: true,
                rules: [
                    { token: "comment",        foreground: "5a5a6a", fontStyle: "italic" },
                    { token: "keyword",        foreground: "f59e0b", fontStyle: "bold" },
                    { token: "string",         foreground: "22c55e" },
                    { token: "number",         foreground: "06b6d4" },
                    { token: "type",           foreground: "ef4444" },
                    { token: "delimiter",      foreground: "a1a1aa" },
                    { token: "identifier",     foreground: "f4f4f5" },
                    { token: "function",       foreground: "fbbf24" },
                ],
                colors: {
                    "editor.background":           "#18181b",
                    "editor.foreground":           "#f4f4f5",
                    "editorLineNumber.foreground": "#52525b",
                    "editorLineNumber.activeForeground": "#f59e0b",
                    "editor.lineHighlightBackground":    "#1e1e2260",
                    "editorCursor.foreground":     "#f59e0b",
                    "editor.selectionBackground":  "#f59e0b40",
                    "editorIndentGuide.background":"#27272b",
                    "editorIndentGuide.activeBackground": "#f59e0b50",
                    "editorWidget.background":     "#1e1e22",
                    "editorWidget.border":         "#3f3f46",
                    "editorSuggestWidget.background": "#1e1e22",
                    "editorSuggestWidget.border":  "#3f3f46",
                    "editorSuggestWidget.selectedBackground": "#f59e0b25",
                    "scrollbarSlider.background":  "#3f3f4680",
                    "scrollbarSlider.hoverBackground": "#52525b",
                }
            });

            monacoInstance = monaco.editor.create(document.getElementById("monacoEditor"), {
                value: "# Write your Python code here...\n# Try: print('Hello, World!')\n# Or click an example from the sidebar →\n",
                language: "python",
                theme: "codeexec-dark",
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: 13,
                lineHeight: 22,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                wordWrap: "on",
                automaticLayout: true,
                tabSize: 4,
                insertSpaces: true,
                renderLineHighlight: "gutter",
                cursorBlinking: "smooth",
                cursorSmoothCaretAnimation: "on",
                smoothScrolling: true,
                padding: { top: 14, bottom: 14 },
                suggest: { showKeywords: true, showSnippets: true },
                quickSuggestions: { other: true, comments: false, strings: false },
                bracketPairColorization: { enabled: true },
                guides: { bracketPairs: true, indentation: true },
                formatOnType: true,
                formatOnPaste: true,
                accessibilitySupport: "off",
            });

            // Ctrl+Enter to run
            monacoInstance.addAction({
                id: "run-code",
                label: "Run Code",
                keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
                run: function () { executeCode(); }
            });

            // Live char/line count updates
            monacoInstance.onDidChangeModelContent(function () {
                updateEditorInfo();
            });

            // Initial count
            updateEditorInfo();
            monacoInstance.focus();
        });
    }

    // --- Events ---
    function bindEvents() {
        runBtn.addEventListener("click", executeCode);
        clearBtn.addEventListener("click", clearOutput);
        copyCodeBtn.addEventListener("click", copyCode);
        sidebarToggle.addEventListener("click", toggleSidebar);

        // Mode tabs
        modeEditor.addEventListener("click", () => switchMode("editor"));
        modePrompt.addEventListener("click", () => switchMode("prompt"));

        // Dataset upload
        uploadZone.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", handleFileSelect);
        uploadZone.addEventListener("dragover", (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
        uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
        uploadZone.addEventListener("drop", handleFileDrop);

        // AI Prompt
        generateBtn.addEventListener("click", generateFromPrompt);
        if (copyGenBtn) copyGenBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(lastGeneratedCode);
            showToast("Code copied!", "success");
        });
        if (editGenBtn) editGenBtn.addEventListener("click", () => {
            editorAPI.setValue(lastGeneratedCode);
            switchMode("editor");
            // Small delay so Monaco is visible before focusing
            setTimeout(() => editorAPI.focus(), 80);
            showToast("Code loaded into editor — tweak it and hit Run!", "info");
        });
        if (runGenBtn) runGenBtn.addEventListener("click", () => {
            editorAPI.setValue(lastGeneratedCode);
            executeCode();
        });
    }

    // --- Mode Switching ---
    function switchMode(mode) {
        if (mode === "editor") {
            modeEditor.classList.add("active");
            modePrompt.classList.remove("active");
            editorPanel.style.display = "flex";
            promptPanel.style.display = "none";
            // Let Monaco re-layout after becoming visible
            if (monacoInstance) setTimeout(() => monacoInstance.layout(), 50);
        } else {
            modePrompt.classList.add("active");
            modeEditor.classList.remove("active");
            promptPanel.style.display = "flex";
            editorPanel.style.display = "none";
        }
    }

    // --- Editor info (char/line count in footer) ---
    function updateEditorInfo() {
        if (!monacoInstance) return;
        const text = monacoInstance.getValue();
        charCount.textContent = text.length + " chars";
        lineCount.textContent = monacoInstance.getModel().getLineCount() + " lines";
    }

    // --- Dataset Upload (Supabase-backed) ---
    function handleFileSelect(e) {
        if (e.target.files.length > 0) uploadFile(e.target.files[0]);
    }

    function handleFileDrop(e) {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) uploadFile(e.dataTransfer.files[0]);
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);
        try {
            showToast("Uploading " + file.name + " to Supabase...", "info");
            const res = await fetch("/api/upload", { method: "POST", body: formData });
            const data = await res.json();
            if (data.status === "success") {
                showToast("Dataset uploaded: " + file.name + " (" + (data.rows || 0) + " rows)", "success");
                loadDatasets();
            } else {
                showToast("Upload failed: " + (data.error || "Unknown error"), "error");
            }
        } catch (err) {
            showToast("Upload error: " + err.message, "error");
        }
        fileInput.value = "";
    }

    async function loadDatasets() {
        try {
            const res = await fetch("/api/datasets");
            const datasets = await res.json();
            datasetList.innerHTML = "";

            for (const ds of datasets) {
                const item = document.createElement("div");
                item.className = "dataset-item";
                const sizeStr = ds.size + " rows";
                item.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
                    <span class="name">${escapeHTML(ds.name)}</span>
                    <span class="size">${sizeStr}</span>
                    <button class="del-btn" title="Delete">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                `;
                item.querySelector(".del-btn").addEventListener("click", (e) => {
                    e.stopPropagation();
                    deleteDataset(ds.name);
                });
                datasetList.appendChild(item);
            }
        } catch (err) {
            console.error("Failed to load datasets:", err);
        }
    }

    async function deleteDataset(name) {
        try {
            await fetch("/api/datasets/" + encodeURIComponent(name), { method: "DELETE" });
            showToast("Deleted: " + name, "info");
            loadDatasets();
        } catch (err) {
            showToast("Delete failed", "error");
        }
    }


    async function generateFromPrompt() {
        const prompt = promptInput.value.trim();
        if (!prompt) { showToast("Enter a prompt first!", "info"); return; }

        const mode = explanationMode ? explanationMode.value : "technical";
        const debug = debugToggle ? debugToggle.checked : false;

        genOverlay.classList.add("active");
        statusText.textContent = "Generating...";
        statusDot.style.background = "var(--accent-yellow)";

        try {
            const res = await resilientFetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt,
                    session_id: currentSessionId,
                    explanation_mode: mode,
                    debug: debug
                }),
            }, {
                timeout: 120000,
                retries: 3,
                onRetry: function(attempt, max) {
                    statusText.textContent = "AI is thinking... retry " + attempt + "/" + max;
                    showToast("AI is taking a moment — retrying automatically...", "info");
                }
            });

            const data = await res.json();

            if (data.error) {
                showToast(data.error, "error");
                genOverlay.classList.remove("active");
                statusText.textContent = "Ready";
                statusDot.style.background = "var(--accent-green)";
                return;
            }

            lastGeneratedCode = data.code || "";
            const explanation = data.explanation || "No explanation provided.";
            const suggestions = data.suggestions || "";
            if (data.session_id) currentSessionId = data.session_id;

            // Show preview
            generatedPreview.style.display = "block";
            generatedCode.querySelector("code").textContent = lastGeneratedCode;
            generatedCode.querySelectorAll("pre code").forEach((el) => hljs.highlightElement(el));
            generatedExplanation.innerHTML = "<strong>Explanation:</strong> " + escapeHTML(explanation);

            if (suggestions && generatedSuggestions) {
                generatedSuggestions.style.display = "block";
                generatedSuggestions.innerHTML = "<strong>💡 Optimization Suggestions:</strong><br/>" + escapeHTML(suggestions);
            } else if (generatedSuggestions) {
                generatedSuggestions.style.display = "none";
            }

            showToast("Code generated! Review and run.", "success");
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            genOverlay.classList.remove("active");
            statusText.textContent = "Ready";
            statusDot.style.background = "var(--accent-green)";
        }
    }

    // --- Code Execution ---
    async function executeCode() {
        const code = editorAPI.getValue().trim();
        if (!code) { showToast("Write some code first!", "info"); return; }

        const debug = debugToggle ? debugToggle.checked : false;

        setExecuting(true);
        try {
            const response = await resilientFetch("/api/execute", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code, timeout: 30, debug: debug }),
            }, {
                timeout: 60000,
                retries: 2,
                onRetry: function(attempt, max) {
                    statusText.textContent = "Retrying execution... (" + attempt + "/" + max + ")";
                    showToast("Connection hiccup — retrying...", "info");
                }
            });
            const result = await response.json();
            displayResult(result, code);
            addToHistory(result, code);
            updateStats(result);
        } catch (err) {
            displayResult({ success: false, output: "", error: err.message, plots: [], output_files: [], execution_time_ms: 0 }, editorAPI.getValue());
        } finally {
            setExecuting(false);
        }
    }

    function setExecuting(active) {
        execOverlay.classList.toggle("active", active);
        runBtn.disabled = active;
        statusText.textContent = active ? "Executing..." : "Ready";
        statusDot.style.background = active ? "var(--accent-yellow)" : "var(--accent-green)";
    }

    // --- Display Result ---
    function displayResult(result, code) {
        outputWelcome.style.display = "none";
        outputResults.style.display = "block";

        const block = document.createElement("div");
        block.className = "result-block";
        const statusClass = result.success ? "success" : "error";
        const statusIcon = result.success ? "✅" : "❌";
        const statusLabel = result.success ? "Success" : "Failed";

        let bodyHTML = "";
        if (result.error) bodyHTML += '<div class="result-error">' + escapeHTML(result.error) + '</div>';
        if (result.output) bodyHTML += '<div class="result-output">' + escapeHTML(result.output) + '</div>';
        if (!result.output && !result.error) bodyHTML += '<div class="result-output" style="color:var(--text-muted);font-style:italic">(No output)</div>';

        if (result.plots && result.plots.length > 0) {
            bodyHTML += '<div class="result-plots">';
            for (const b64 of result.plots) bodyHTML += '<img class="result-plot-img" src="data:image/png;base64,' + b64 + '" alt="Chart" />';
            bodyHTML += '</div>';
        }

        // Output files generated by the code (CSV, XLSX, JSON, etc.)
        if (result.output_files && result.output_files.length > 0) {
            bodyHTML += '<div class="result-output-files" style="margin:10px 0;padding:10px 14px;background:rgba(46,213,115,0.08);border:1px solid rgba(46,213,115,0.25);border-radius:8px;">';
            bodyHTML += '<strong style="color:#2ed573;display:block;margin-bottom:8px;">📁 Generated Files (' + result.output_files.length + '):</strong>';
            for (var fi = 0; fi < result.output_files.length; fi++) {
                var of_ = result.output_files[fi];
                var sizeStr = of_.size < 1024 ? of_.size + ' B' : (of_.size / 1024).toFixed(1) + ' KB';
                bodyHTML += '<button class="output-file-btn" data-idx="' + fi + '" ' +
                    'style="display:inline-flex;align-items:center;gap:6px;margin:4px 6px 4px 0;padding:6px 14px;' +
                    'background:rgba(46,213,115,0.15);border:1px solid rgba(46,213,115,0.35);border-radius:6px;' +
                    'color:#2ed573;cursor:pointer;font-size:12px;font-weight:600;transition:all 0.2s;">' +
                    '⬇ ' + escapeHTML(of_.name) + ' (' + sizeStr + ')</button>';
            }
            bodyHTML += '</div>';
        }

        // Debug info
        if (result.debug_info) {
            bodyHTML += '<div class="result-explanation"><strong>🛠️ Debug Info:</strong><br/>' + escapeHTML(result.debug_info) + '</div>';
        }

        // Auto-retry info
        if (result.retried) {
            bodyHTML += '<div class="result-explanation"><strong>🔁 Auto-Recovery:</strong> Code failed initially and was automatically corrected and re-executed.</div>';
        }

        const codePreview = code.length > 600 ? code.substring(0, 600) + "\n# ... (truncated)" : code;

        block.innerHTML =
            '<div class="result-header">' +
                '<div class="result-status ' + statusClass + '">' + statusIcon + ' ' + statusLabel + '</div>' +
                '<div class="result-time" style="display:flex; align-items:center; gap: 10px;">' +
                    '<button class="small-btn export-txt-btn" style="padding:3px 8px;font-size:11px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:4px;color:white;cursor:pointer;">Export TXT</button>' +
                    '<button class="small-btn export-csv-btn" style="padding:3px 8px;font-size:11px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:4px;color:white;cursor:pointer;">Export CSV</button>' +
                    '<button class="small-btn export-json-btn" style="padding:3px 8px;font-size:11px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:4px;color:white;cursor:pointer;">Export JSON</button>' +
                    '⏱ ' + result.execution_time_ms + 'ms' +
                '</div>' +
            '</div>' +
            '<div class="result-body">' +
                bodyHTML +
                '<div class="result-code-block">' +
                    '<div class="result-code-header">' +
                        '<span>Executed Code</span>' +
                        '<button onclick="navigator.clipboard.writeText(this.closest(\'.result-block\').querySelector(\'code\').textContent)">Copy</button>' +
                    '</div>' +
                    '<div class="result-code-body">' +
                        '<pre><code class="language-python">' + escapeHTML(codePreview) + '</code></pre>' +
                    '</div>' +
                '</div>' +
            '</div>';

        outputResults.prepend(block);

        // Export TXT
        block.querySelector('.export-txt-btn').addEventListener('click', function() {
            var report = "CodeExec AI Execution Report\n" +
                "=============================\n" +
                "Status: " + statusLabel + "\n" +
                "Time: " + result.execution_time_ms + "ms\n\n" +
                "Code Executed:\n--------------\n" + code + "\n\n" +
                "Output:\n-------\n" + (result.output || "(No output)") + "\n\n" +
                "Error:\n------\n" + (result.error || "(No error)");
            downloadFile(report, "codeexec_report_" + Date.now() + ".txt", "text/plain");
        });

        // Export CSV
        block.querySelector('.export-csv-btn').addEventListener('click', function() {
            var csv = "field,value\n" +
                '"status","' + statusLabel + '"\n' +
                '"execution_time_ms","' + result.execution_time_ms + '"\n' +
                '"output","' + csvEscape(result.output || "") + '"\n' +
                '"error","' + csvEscape(result.error || "") + '"\n' +
                '"code","' + csvEscape(code) + '"';
            downloadFile(csv, "codeexec_report_" + Date.now() + ".csv", "text/csv");
        });

        // Export JSON
        block.querySelector('.export-json-btn').addEventListener('click', function() {
            var obj = {
                status: statusLabel,
                execution_time_ms: result.execution_time_ms,
                code: code,
                output: result.output || "",
                error: result.error || "",
                plots_count: (result.plots || []).length,
                timestamp: new Date().toISOString()
            };
            downloadFile(JSON.stringify(obj, null, 2), "codeexec_report_" + Date.now() + ".json", "application/json");
        });

        // Output file download buttons
        if (result.output_files && result.output_files.length > 0) {
            block.querySelectorAll('.output-file-btn').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var idx = parseInt(this.getAttribute('data-idx'));
                    var fileInfo = result.output_files[idx];
                    downloadBase64File(fileInfo.data_b64, fileInfo.name, fileInfo.mime);
                    showToast("Downloaded: " + fileInfo.name, "success");
                });
            });
        }

        block.querySelectorAll("pre code").forEach(function(el) { hljs.highlightElement(el); });
        showToast(result.success ? "Executed in " + result.execution_time_ms + "ms" : "Execution failed", result.success ? "success" : "error");
    }

    function downloadFile(content, filename, mime) {
        var blob = new Blob([content], { type: mime });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    function downloadBase64File(b64Data, filename, mime) {
        var byteChars = atob(b64Data);
        var byteNumbers = new Array(byteChars.length);
        for (var i = 0; i < byteChars.length; i++) {
            byteNumbers[i] = byteChars.charCodeAt(i);
        }
        var byteArray = new Uint8Array(byteNumbers);
        var blob = new Blob([byteArray], { type: mime });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    function csvEscape(str) {
        return str.replace(/"/g, '""').replace(/\n/g, '\\n');
    }

    // --- History ---
    function addToHistory(result, code) {
        const entry = { code, success: result.success, label: code.split("\n")[0].substring(0, 40) || "(empty)", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
        history.unshift(entry);
        if (history.length > 20) history.pop();
        renderHistory();
    }

    function renderHistory() {
        if (!history.length) return;
        historyList.innerHTML = "";
        for (const entry of history) {
            const item = document.createElement("div");
            item.className = "history-item";
            item.innerHTML = '<span class="dot ' + (entry.success ? "success" : "error") + '"></span><span class="label">' + escapeHTML(entry.label) + '</span><span class="time">' + entry.time + '</span>';
            item.addEventListener("click", () => {
                editorAPI.setValue(entry.code);
                switchMode("editor");
                setTimeout(() => editorAPI.focus(), 80);
                showToast("Code restored", "info");
            });
            historyList.appendChild(item);
        }
    }

    function updateStats(result) {
        totalRuns++;
        if (result.success) totalSuccess++;
        totalTimeMs += result.execution_time_ms;
        statRuns.textContent = totalRuns;
        statSuccess.textContent = totalSuccess;
        statAvgMs.textContent = Math.round(totalTimeMs / totalRuns) + "ms";
    }

    // --- Examples ---
    async function loadExamples() {
        try {
            const res = await fetch("/api/examples");
            const examples = await res.json();
            examplesList.innerHTML = "";
            for (const ex of examples) {
                const card = document.createElement("div");
                card.className = "example-card";
                const emoji = ex.title.match(/^[\p{Emoji}]/u)?.[0] || "📄";
                const titleText = ex.title.replace(/^[\p{Emoji}\s]+/u, "");
                card.innerHTML = '<span class="emoji">' + emoji + '</span><div class="info"><h4>' + escapeHTML(titleText) + '</h4><p>' + escapeHTML(ex.description) + '</p></div>';
                card.addEventListener("click", () => loadExample(ex.id));
                examplesList.appendChild(card);
            }
        } catch (err) { console.error("Failed to load examples:", err); }
    }

    async function loadExample(id) {
        try {
            const res = await fetch("/api/examples/" + id);
            const data = await res.json();
            editorAPI.setValue(data.code);
            switchMode("editor");
            setTimeout(() => editorAPI.focus(), 80);
            showToast("Example loaded — hit Run!", "info");
        } catch (err) { showToast("Failed to load example", "error"); }
    }

    // --- UI Utilities ---
    function clearOutput() {
        outputResults.innerHTML = "";
        outputResults.style.display = "none";
        outputWelcome.style.display = "flex";
        showToast("Output cleared", "info");
    }

    function copyCode() {
        navigator.clipboard.writeText(editorAPI.getValue()).then(() => showToast("Code copied!", "success"));
    }

    function toggleSidebar() {
        sidebar.classList.toggle("collapsed");
        sidebar.classList.toggle("open");
    }

    function showToast(message, type) {
        type = type || "info";
        const toast = document.createElement("div");
        toast.className = "toast " + type;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(function() { toast.style.opacity = "0"; toast.style.transform = "translateY(12px)"; toast.style.transition = "all 0.3s ease"; setTimeout(function() { toast.remove(); }, 300); }, 2800);
    }

    function escapeHTML(str) {
        const div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    document.addEventListener("DOMContentLoaded", init);
})();
