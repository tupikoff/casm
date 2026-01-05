/**
 * Cambridge Assembly Emulator - Frontend Application
 */

// DOM Elements
const codeEditor = document.getElementById('code-editor');
const inputBuffer = document.getElementById('input-buffer');
const startAddress = document.getElementById('start-address');
const maxSteps = document.getElementById('max-steps');
const memorySize = document.getElementById('memory-size');
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
const DEFAULT_WORD_BITS = 8;

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

    // Headers
    const headers = ['Step', 'Addr'];
    const hasLabels = trace.some(r => r.label);
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
            cells.push(`<td class="col-label">${isStep0 ? '' : (row.label || '')}</td>`);
        }

        cells.push(
            `<td class="col-instr">${isStep0 ? '' : row.instr_text}</td>`,
            buildValueCell(row.acc, 'col-acc'),
        );

        // Memory values
        for (const addr of traceWatchList) {
            const val = row.mem[addr.toString()];
            cells.push(buildValueCell(val !== undefined ? val : '-', 'col-mem'));
        }

        // Optional columns
        if (options.trace_include_ix) {
            cells.push(buildValueCell(row.ix !== undefined ? row.ix : '-', 'col-ix'));
        }
        if (options.trace_include_flag) {
            cells.push(`<td class="col-flag">${row.flag !== null && row.flag !== undefined ? row.flag : '-'}</td>`);
        }
        if (options.trace_include_io) {
            cells.push(buildValueCell(row.in_code !== null ? row.in_code : '-', 'col-io'));
            cells.push(buildValueCell(row.out_code !== null ? row.out_code : '-', 'col-io'));
        }

        return `<tr ${rowClass}>${cells.join(' ')}</tr>`;
    }).join('');
}

function buildValueCell(value, className) {
    const display = value === undefined ? '-' : value;
    const binaryTooltip = getBinaryTooltip(value);
    const tooltipAttr = binaryTooltip ? ` data-bintooltip="${escapeHtml(binaryTooltip)}"` : '';
    return `<td class="${className}"${tooltipAttr}>${display}</td>`;
}

function getBinaryTooltip(value) {
    if (value === null || value === undefined) {
        return null;
    }
    if (typeof value === 'string') {
        if (value.startsWith('B')) {
            return value;
        }
        const numeric = Number(value);
        if (!Number.isNaN(numeric)) {
            return formatBinaryValue(numeric);
        }
        return null;
    }
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        return null;
    }
    return formatBinaryValue(value);
}

function formatBinaryValue(value, bits = DEFAULT_WORD_BITS) {
    if (typeof value !== 'number' || !Number.isFinite(value)) return null;
    const width = Math.max(bits, 1);
    const mask = (1n << BigInt(width)) - 1n;
    let unsigned = BigInt(Math.trunc(value));
    unsigned &= mask;
    const binary = unsigned.toString(2).padStart(width, '0');
    return `B${binary}`;
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

        // Result text
        outputText.textContent = result.output_text || '(No output)';
        if (result.output_text) {
            document.getElementById('output-panel').open = true;
        }

        // Final state
        // renderFinalState(result.final_state); // Removed as per instruction

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
    echo: {
        code: `; Echo one character\n\n200 IN\n201 OUT\n202 END`,
        start: 200,
        input: 'A'
    },
    next_ascii: {
        code: `; Read char and output next ASCII\n\n200 IN\n201 ADD #1\n202 OUT\n203 END`,
        start: 200,
        input: 'A'
    },
    inc_mem: {
        code: `; Increment MEM[81] by 1\n81 8\n\n200 LDD 81\n201 INC ACC\n202 STO 81\n203 END`,
        start: 200
    },
    if_else: {
        code: `; If X equals 10 then RESULT=0 else RESULT=1\n81 X: 10\n82 RESULT: 0\n\n200 START: LDD X\n201 CMP #10\n202 JPE THEN\n203 LDM #1\n204 STO RESULT\n205 JMP DONE\n206 THEN: LDM #0\n207 STO RESULT\n208 DONE: END`,
        start: 200
    },
    n_stars_nolabel: {
        code: `; Output '*' N times (no labels)\n81 5\n\n200 LDD 81\n201 CMP #0\n202 JPE 210\n203 LDM #42\n204 OUT\n205 LDD 81\n206 DEC ACC\n207 STO 81\n208 JMP 200\n210 END`,
        start: 200
    },
    n_stars_labels: {
        code: `; Output '*' N times (labels for memory and jumps)\n81 N: 5\n\n200 LOOP: LDD N\n201 CMP #0\n202 JPE STOP\n203 LDM #42\n204 OUT\n205 LDD N\n206 DEC ACC\n207 STO N\n208 JMP LOOP\n209 STOP: END`,
        start: 200
    },
    string_output: {
        code: `; Output zero-terminated string using IX and LDX\n80 STR: 72\n81 69\n82 76\n83 76\n84 79\n85 32\n86 87\n87 79\n88 82\n89 76\n90 68\n91 0\n\n200 INIT: LDR #0\n201 LOOP: LDX STR\n202 CMP #0\n203 JPE DONE\n204 OUT\n205 INC IX\n206 JMP LOOP\n207 DONE: END`,
        start: 200
    },
    sum_compare: {
        code: `; Sum A and B, compare with TARGET, output 'Y' or 'N'\n80 A: 7\n81 B: 3\n82 TARGET: 10\n\n200 START: LDD A\n201 ADD B\n202 CMP TARGET\n203 JPE YES\n204 LDM #78\n205 OUT\n206 JMP DONE\n207 YES: LDM #89\n208 OUT\n209 DONE: END`,
        start: 200
    },
    bit_mask_check: {
        code: `; Bit mask check: output 'Y' if (VALUE AND MASK) equals MASK, else output 'N'\n; Memory (address LABEL: value)\n80 VALUE: B00101101\n81 MASK:  #B00000101\n\n; Program (address [label:] instruction)\n200 START: LDD VALUE\n201 AND MASK\n202 CMP MASK\n203 JPE YES\n204 LDM #78\n205 OUT\n206 JMP DONE\n207 YES: LDM #89\n208 OUT\n209 DONE: END`,
        start: 200
    },
    shift_toggle: {
        code: `; Shift and toggle: ACC = (VALUE LSL 1) XOR TOGGLE, store in RESULT, output result byte\n; Memory (address LABEL: value)\n80 VALUE:  #B00001111\n81 TOGGLE: #B00110011\n82 RESULT: 0\n\n; Program (address [label:] instruction)\n200 START: LDD VALUE\n201 LSL #1\n202 XOR TOGGLE\n203 STO RESULT\n204 OUT\n205 END`,
        start: 200
    },
    extract_high_nibble: {
        code: `; Extract high nibble: ACC = (VALUE AND #B11110000) LSR 4, store in HIGH\n; Memory (address LABEL: value)\n80 VALUE: B10101100\n81 HIGH:  0\n\n; Program (address [label:] instruction)\n200 START: LDD VALUE\n201 AND #B11110000\n202 LSR #4\n203 STO HIGH\n204 END`,
        start: 200
    }
};

// Event listeners
runBtn.addEventListener('click', runProgram);

samplesSelect.addEventListener('change', () => {
    const sample = SAMPLES[samplesSelect.value];
    if (sample) {
        codeEditor.value = sample.code;
        inputBuffer.value = sample.input || '';

        // Adjust start address if sample specify it
        const startAddrInput = document.querySelector('input[placeholder="200"]');
        if (startAddrInput) {
            startAddrInput.value = sample.start || 200;
        }

        // Clear previous results when loading new sample
        resultsSection.classList.add('hidden');
        errorDisplay.classList.add('hidden');
        traceContainer.style.display = 'none';

        // Trigger input event to update any listeners
        codeEditor.dispatchEvent(new Event('input', { bubbles: true }));
        inputBuffer.dispatchEvent(new Event('input', { bubbles: true }));
        if (startAddrInput) {
            startAddrInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
});

// Keyboard shortcut: Ctrl+Enter or Cmd+Enter to run
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runProgram();
    }
});

// Initialize with default sample if empty
if (!codeEditor.value.trim()) {
    samplesSelect.value = 'echo';
    samplesSelect.dispatchEvent(new Event('change'));
}
