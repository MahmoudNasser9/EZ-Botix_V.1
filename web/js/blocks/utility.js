/**
 * blocks/utility.js - generic utility blocks + Task Scheduler blocks
 *
 * Contains:
 *   - delay_ms: simple blocking wait (placed in Loops category)
 *   - task_every_ms: register a periodic task with the scheduler
 *   - scheduler_run: start the scheduler loop (run forever)
 *   - scheduler_run_for: run the scheduler for a specific duration
 *   - scheduler_tick: advance all tasks by one tick (for custom loops)
 */

// ============================================================
//  Delay (placed in Loops category, not Tasks)
// ============================================================

Blockly.Blocks['delay_ms'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("Wait")
            .appendField(new Blockly.FieldNumber(500, 0), "MS")
            .appendField("ms");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(120);
    }
};

python.pythonGenerator.forBlock['delay_ms'] = function (block) {
    return `time.sleep_ms(${block.getFieldValue('MS')})\n`;
};

// ============================================================
//  Task Scheduler: Periodic/Cyclic Execution Blocks
// ============================================================

Blockly.Blocks['task_every_ms'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("⏱️ Every")
            .appendField(new Blockly.FieldNumber(500, 10), "INTERVAL")
            .appendField("ms do");
        this.appendStatementInput("DO")
            .setCheck(null);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(260);
        this.setTooltip(
            "Registers a periodic task to run every N milliseconds. " +
            "Hardware blocks inside this task run non-blocking automatically."
        );
    }
};

python.pythonGenerator.forBlock['task_every_ms'] = function (block) {
    const interval = block.getFieldValue('INTERVAL');
    const branch = python.pythonGenerator.statementToCode(block, 'DO') || '    pass\n';
    const funcName = python.pythonGenerator.provideFunction_(
        'cyclic_task_' + interval + 'ms',
        [`def ${python.pythonGenerator.FUNCTION_NAME_PLACEHOLDER_}():`,
         branch]
    );
    return `scheduler.add_task(${interval}, ${funcName})\n`;
};

// ============================================================
//  Start Scheduler Loop (run forever)
// ============================================================

Blockly.Blocks['scheduler_run'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("⏱️ Start Task Scheduler Loop");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(260);
        this.setTooltip(
            "Starts the scheduler — runs all registered tasks forever. " +
            "Place this AFTER all your task registrations."
        );
    }
};

python.pythonGenerator.forBlock['scheduler_run'] = function (block) {
    // V2: run(duration_ms=0) means "run forever" — won't exit when drivers go idle
    return `scheduler.run(duration_ms=0)\n`;
};

// ============================================================
//  Run Scheduler For Duration (NEW in V2)
// ============================================================

Blockly.Blocks['scheduler_run_for'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("⏱️ Run Tasks for")
            .appendField(new Blockly.FieldNumber(5000, 100), "DURATION")
            .appendField("ms");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(260);
        this.setTooltip(
            "Runs all registered tasks for a specific duration, then stops. " +
            "Useful for timed behaviors like 'blink LED for 5 seconds'."
        );
    }
};

python.pythonGenerator.forBlock['scheduler_run_for'] = function (block) {
    const duration = block.getFieldValue('DURATION');
    return `scheduler.run(duration_ms=${duration})\n`;
};

// ============================================================
//  Update Tasks — single tick (for custom loops)
// ============================================================

Blockly.Blocks['scheduler_tick'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("⏱️ Update Tasks (1 Tick)");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(260);
        this.setTooltip(
            "Checks and runs ready tasks once. Use inside your own loop " +
            "if you need custom control over the event loop."
        );
    }
};

python.pythonGenerator.forBlock['scheduler_tick'] = function (block) {
    return `scheduler.tick()\n`;
};
