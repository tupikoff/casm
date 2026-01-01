/**
 * Cambridge Assembly Emulator - Frontend Application
 */

// DOM Elements
const codeEditor = document.getElementById('code-editor');
const inputBuffer = document.getElementById('input-buffer');
const startAddress = document.getElementById('start-address');
const maxSteps = document.getElementById('max-steps');
const memorySize = document.getElementById('memory-size');
const traceWatch = document.getElementById('trace-watch');
const traceEnabled = document.getElementById('trace-enabled');
const traceIx = document.getElementById('trace-ix');
const traceFlag = document.getElementById('trace-flag');
const traceIo = document.getElementById('trace-io');
const runBtn = document.getElementById('run-btn');
const samplesSelect = document.getElementById('samples-select');
const statusIndicator = document.getElementById('status-indicator');
const resultsSection = document.getElementById('results-section');
const stepsBadge = document.getElementById('steps-badge');
const errorDisplay = document.getElementById('error-display');
const outputText = document.getElementById('output-text');
const finalState = document.getElementById('final-state');
const traceHeader = document.getElementById('trace-header');
const traceBody = document.getElementById('trace-body');
const traceContainer = document.getElementById('trace-container');

/**
 * Parse initial memory string into dict
 * Format: "80:10, 81:8, 82:80"
 */
function parseInitialMemory(str) {
    const result = {};
    if (!str.trim()) return result;

    const pairs = str.split(',');
    for (const pair of pairs) {
        const [addr, val] = pair.split(':').map(s => s.trim());
        if (addr && val) {
            result[addr] = parseInt(val, 10);
        }
    }
    return result;
}

/**
 * Parse trace watch string into array
 * Format: "80, 81, 82, 83"
 */
function parseTraceWatch(str) {
    if (!str.trim()) return [];
    return str.split(',')
        .map(s => parseInt(s.trim(), 10))
        .filter(n => !isNaN(n));
}

/**
 * Build API request from form inputs
 */
function buildRequest() {
    return {
        program: codeEditor.value,
        input: inputBuffer.value,
        options: {
            start_address: parseInt(startAddress.value, 10) || 200,
            max_steps: parseInt(maxSteps.value, 10) || 10000,
            memory_size: parseInt(memorySize.value, 10) || 256,
            trace: traceEnabled.checked,
            trace_watch: parseTraceWatch(traceWatch.value),
            trace_include_ix: traceIx.checked,
            trace_include_flag: traceFlag.checked,
            trace_include_io: traceIo.checked,
        }
    };
}

/**
 * Render final state
 */
function renderFinalState(state) {
    const items = [
        { label: 'ACC', value: state.acc },
        { label: 'IX', value: state.ix },
        { label: 'PC', value: state.pc },
        { label: 'FLAG', value: state.flag === null ? 'null' : state.flag.toString() },
    ];

    finalState.innerHTML = items.map(item => `
        <div class="state-item">
            <span class="label">${item.label}</span>
            <span class="value">${item.value}</span>
        </div>
    `).join('');
}

/**
 * Render error display
 */
function renderError(error) {
    if (!error) {
        errorDisplay.classList.add('hidden');
        return;
    }

    errorDisplay.classList.remove('hidden');
    errorDisplay.innerHTML = `
        <div class="error-type">${error.type}</div>
        <div class="error-message">${error.message}</div>
        <div class="error-location">Step ${error.step} at address ${error.addr}${error.source_line_no ? ` (line ${error.source_line_no})` : ''}</div>
        ${error.source_text ? `<div class="error-source">${escapeHtml(error.source_text)}</div>` : ''}
    `;
}

/**
 * Escape HTML characters
 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Render trace table
 */
function renderTrace(trace, traceWatchList, options) {
    if (!trace || trace.length === 0) {
        traceContainer.style.display = 'none';
        return;
    }

    traceContainer.style.display = 'block';

    // Build header
    const hasLabels = trace.some(row => row.label);
    const headers = ['Step', 'Addr'];
    if (hasLabels) headers.push('Label');
    headers.push('Command', 'ACC');

    // Add watched memory addresses
    for (const addr of traceWatchList) {
        headers.push(addr.toString());
    }

    // Add optional columns
    if (options.trace_include_ix) headers.push('IX');
    if (options.trace_include_flag) headers.push('FLAG');
    if (options.trace_include_io) {
        headers.push('IN');
        headers.push('OUT');
    }

    traceHeader.innerHTML = '<tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr>';

    // Build body
    traceBody.innerHTML = trace.map(row => {
        const isStep0 = row.step === 0;
        const rowClass = isStep0 ? 'class="row-step-0"' : '';
        const cells = [
            `<td class="col-step">${row.step}</td>`,
            `<td class="col-addr">${isStep0 ? '' : row.addr}</td>`,
        ];

        if (hasLabels) {
            cells.push(`<td class="col-label">${isStep0 ? '' : escapeHtml(row.label || '')}</td>`);
        }

        cells.push(
            `<td class="col-instr">${isStep0 ? '' : escapeHtml(row.instr_text)}</td>`,
            `<td class="col-acc">${row.acc}</td>`,
        );

        // Memory values
        for (const addr of traceWatchList) {
            const val = row.mem[addr.toString()];
            cells.push(`<td class="col-mem">${val !== undefined ? val : '-'}</td>`);
        }

        // Optional columns
        if (options.trace_include_ix) {
            cells.push(`<td class="col-ix">${row.ix !== undefined ? row.ix : '-'}</td>`);
        }
        if (options.trace_include_flag) {
            cells.push(`<td class="col-flag">${row.flag !== null && row.flag !== undefined ? row.flag : '-'}</td>`);
        }
        if (options.trace_include_io) {
            cells.push(`<td class="col-io">${row.in_code !== null ? row.in_code : '-'}</td>`);
            cells.push(`<td class="col-io">${row.out_code !== null ? row.out_code : '-'}</td>`);
        }

        return `<tr ${rowClass}>${cells.join('')}</tr>`;
    }).join('');
}

/**
 * Run the program
 */
async function runProgram() {
    runBtn.disabled = true;
    statusIndicator.textContent = 'Running...';
    statusIndicator.className = 'status-indicator loading';

    const request = buildRequest();

    try {
        const response = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        // Show results
        resultsSection.classList.remove('hidden');

        // Badge
        stepsBadge.textContent = `${result.steps_executed} steps`;
        stepsBadge.className = 'badge ' + (result.status === 'ok' ? 'success' : 'error');

        // Error
        renderError(result.error);

        // Output
        outputText.textContent = result.output_text || '(no output)';

        // Final state
        renderFinalState(result.final_state);

        // Trace
        renderTrace(result.trace, result.trace_watch, request.options);

        statusIndicator.textContent = result.status === 'ok' ? 'Complete' : 'Error';
        statusIndicator.className = 'status-indicator ' + (result.status === 'ok' ? '' : 'error');

    } catch (err) {
        statusIndicator.textContent = err.message;
        statusIndicator.className = 'status-indicator error';

        errorDisplay.classList.remove('hidden');
        errorDisplay.innerHTML = `
            <div class="error-type">NetworkError</div>
            <div class="error-message">${escapeHtml(err.message)}</div>
        `;
        resultsSection.classList.remove('hidden');
    } finally {
        runBtn.disabled = false;
    }
}

const SAMPLES = {
    countdown: {
        code: `; Sample program: Count down from 5\nLDM #5\nSTO 80\nLOOP: LDD 80\nCMP #0\nJPE DONE\nDEC ACC\nSTO 80\nJMP LOOP\nDONE: END`,
        watch: '80',
        start: 200
    },
    integrated_mem: {
        code: `80 10\n81 8\n200 LDD 80\nADD 81\nSTO 82\nEND`,
        watch: '80, 81, 82',
        start: 200
    },
    user_sample: {
        code: `80 10\n8\n80\n81\n200 LDD 81\nINC ACC\nSTO 83\nLDI 82\nCMP 83\nJPE 209\nLDD 83\nADD #10\nJMP 210\nDEC ACC\nSTO 81\nEND`,
        watch: '80, 81, 82, 83',
        start: 200
    }
};

// Event listeners
runBtn.addEventListener('click', runProgram);

samplesSelect.addEventListener('change', () => {
    const sample = SAMPLES[samplesSelect.value];
    if (sample) {
        codeEditor.value = sample.code;
        traceWatch.value = sample.watch || '';
        startAddress.value = sample.start || 200;

        // Trigger input event to update any listeners
        codeEditor.dispatchEvent(new Event('input', { bubbles: true }));
        traceWatch.dispatchEvent(new Event('input', { bubbles: true }));
        startAddress.dispatchEvent(new Event('input', { bubbles: true }));
    }
});

// Keyboard shortcut: Ctrl+Enter or Cmd+Enter to run
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runProgram();
    }
});

// Initialize with sample program
if (!codeEditor.value.trim()) {
    codeEditor.value = `; Sample program: Count down from 5
LDM #5
STO 80
LOOP: LDD 80
CMP #0
JPE DONE
DEC ACC
STO 80
JMP LOOP
DONE: END`;
    traceWatch.value = '80';
}
