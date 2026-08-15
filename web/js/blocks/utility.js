/**
 * blocks/utility.js - generic utility block(s)
 *
 * delay_ms isn't hardware-specific, so unlike lights/motion/inputs it does
 * NOT call EZBOTIX.registerCategory() - it's placed directly inside the
 * standard "🔄 Loops" category by toolbox.js, alongside the built-in loop
 * blocks.
 */

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
        this.setColour(120);
        this.setTooltip("Registers a cyclic task to run every N milliseconds.");
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

Blockly.Blocks['scheduler_run'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("⏱️ Start Task Scheduler Loop");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(120);
        this.setTooltip("Starts continuous execution for all registered cyclic tasks.");
    }
};

python.pythonGenerator.forBlock['scheduler_run'] = function (block) {
    return `scheduler.run()\n`;
};

Blockly.Blocks['scheduler_tick'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("⏱️ Update Tasks (1 Tick)");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(120);
        this.setTooltip("Checks and runs ready cyclic tasks once inside a custom loop.");
    }
};

python.pythonGenerator.forBlock['scheduler_tick'] = function (block) {
    return `scheduler.tick()\n`;
};

