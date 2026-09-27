/**
 * blocks/buzzer.js - 🔊 Sound category (Passive Buzzer)
 *
 * V2 Architecture: Context-Aware Code Generation
 *   - At the top level: blocks generate BLOCKING calls (sequential)
 *   - Inside a ⏱️ Task: blocks generate NON-BLOCKING calls (concurrent)
 *
 * The user never sees blocking/non-blocking — it just works based on
 * where they place the block.
 */

// ============================================================
//  Helper: detect if a block is inside a task_every_ms block
// ============================================================

/**
 * Walks up the block tree to check if this block is nested inside
 * a `task_every_ms` block. If it is, the block should generate
 * non-blocking code so the task callback returns immediately.
 *
 * @param {Blockly.Block} block - The block to check.
 * @returns {boolean} True if the block is inside a task.
 */
function isInsideTask(block) {
    let parent = block.getSurroundParent();
    while (parent) {
        if (parent.type === 'task_every_ms') return true;
        parent = parent.getSurroundParent();
    }
    return false;
}

// ============================================================
//  Play Tone
// ============================================================

Blockly.Blocks['buzzer_play_tone'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🔊 Play Tone")
            .appendField("Frequency (Hz)")
            .appendField(new Blockly.FieldNumber(2048, 0, 20000), "FREQ");
        this.appendDummyInput()
            .appendField("Duration (ms)")
            .appendField(new Blockly.FieldNumber(500, 0, 60000), "DURATION");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(300);
        this.setTooltip("Plays a tone on the passive buzzer.");
    }
};

python.pythonGenerator.forBlock['buzzer_play_tone'] = function (block) {
    var freq = block.getFieldValue('FREQ');
    var duration = block.getFieldValue('DURATION');

    // Context-aware: non-blocking inside a Task, blocking at top level
    if (isInsideTask(block)) {
        return `buzzer.play_tone(${freq}, ${duration}, blocking=False)\n`;
    }
    return `buzzer.play_tone(${freq}, ${duration})\n`;
};

// ============================================================
//  Stop Buzzer
// ============================================================

Blockly.Blocks['buzzer_stop'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🔊 Stop Buzzer");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(300);
        this.setTooltip("Immediately stops the buzzer from playing.");
    }
};

python.pythonGenerator.forBlock['buzzer_stop'] = function (block) {
    return `buzzer.stop()\n`;
};

// ============================================================
//  Play Melody
// ============================================================

Blockly.Blocks['buzzer_play_melody'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🎵 Play Melody")
            .appendField(new Blockly.FieldDropdown([
                ["Super Mario", "Mario"],
                ["Star Wars", "StarWars"],
                ["Police Siren", "Siren"],
                ["Happy Birthday", "Happy"],
                ["Car Horn", "CarHorn"],
                ["Truck Horn", "TruckHorn"],
                ["Power Up", "PowerUp"],
                ["Power Down", "PowerDown"],
                ["Error Bzzzt", "Error"],
                ["Success Ding", "Success"],
                ["Mission Impossible", "MissionImpossible"]
            ]), "MELODY");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(300);
        this.setTooltip("Plays a pre-programmed melody on the buzzer.");
    }
};

python.pythonGenerator.forBlock['buzzer_play_melody'] = function (block) {
    var melody = block.getFieldValue('MELODY');

    // Context-aware: non-blocking inside a Task, blocking at top level
    if (isInsideTask(block)) {
        return `buzzer.play_melody("${melody}", blocking=False)\n`;
    }
    return `buzzer.play_melody("${melody}")\n`;
};

// ============================================================
//  Category registration
// ============================================================

EZBOTIX.registerCategory({
    name: "🔊 Sound",
    colour: 300,
    blocks: ["buzzer_play_tone", "buzzer_play_melody", "buzzer_stop"]
});
