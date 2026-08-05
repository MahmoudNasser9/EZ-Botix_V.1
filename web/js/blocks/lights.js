/**
 * blocks/lights.js - 💡 Lights category (onboard LED, external LED, and WS2812 RGB strips)
 *
 * Pattern for every hardware block file:
 *   1. Define the Blockly.Blocks[...] shape
 *   2. Define its python.pythonGenerator.forBlock[...] code generator
 *   3. Call EZBOTIX.registerCategory(...) once, listing every block type
 *      that belongs in this category
 */

// ============================================================
//  Existing: Simple onboard / external LED toggle
// ============================================================

Blockly.Blocks['led_toggle'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("💡")
            .appendField(new Blockly.FieldDropdown([
                ["Onboard LED", "onboard_led"],
                ["External LED", "external_led"]
            ]), "LED_SELECT")
            .appendField(new Blockly.FieldDropdown([
                ["ON", "1"],
                ["OFF", "0"]
            ]), "STATE");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(20);
    }
};

python.pythonGenerator.forBlock['led_toggle'] = function (block) {
    const led = block.getFieldValue('LED_SELECT');
    const state = block.getFieldValue('STATE');
    return `${led}.value(${state})\n`;
};

// ============================================================
//  RGB Strip: Set a SINGLE LED colour by index
// ============================================================

Blockly.Blocks['rgb_set_led'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🌈 RGB Strip")
            .appendField(new Blockly.FieldDropdown([
                ["Front (8 LEDs)", "rgb_front"],
                ["Back  (8 LEDs)", "rgb_back"]
            ]), "STRIP");
        this.appendDummyInput()
            .appendField("LED #")
            .appendField(new Blockly.FieldDropdown([
                ["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"],
                ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"]
            ]), "INDEX")
            .appendField("  R")
            .appendField(new Blockly.FieldNumber(255, 0, 255, 1), "R")
            .appendField("G")
            .appendField(new Blockly.FieldNumber(0,   0, 255, 1), "G")
            .appendField("B")
            .appendField(new Blockly.FieldNumber(0,   0, 255, 1), "B");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(20);
        this.setTooltip("Set the colour of one LED on a WS2812 strip. Index 0–7.");
    }
};

python.pythonGenerator.forBlock['rgb_set_led'] = function (block) {
    const strip = block.getFieldValue('STRIP');
    const index = block.getFieldValue('INDEX');
    const r = block.getFieldValue('R');
    const g = block.getFieldValue('G');
    const b = block.getFieldValue('B');
    return `${strip}.set_led(${index}, ${r}, ${g}, ${b})\n`;
};

// ============================================================
//  RGB Strip: Set ALL LEDs to the same colour
// ============================================================

Blockly.Blocks['rgb_set_all'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🌈 RGB Strip")
            .appendField(new Blockly.FieldDropdown([
                ["Front (8 LEDs)", "rgb_front"],
                ["Back  (8 LEDs)", "rgb_back"],
                ["Both strips",    "both"]
            ]), "STRIP");
        this.appendDummyInput()
            .appendField("All LEDs  R")
            .appendField(new Blockly.FieldNumber(255, 0, 255, 1), "R")
            .appendField("G")
            .appendField(new Blockly.FieldNumber(255, 0, 255, 1), "G")
            .appendField("B")
            .appendField(new Blockly.FieldNumber(255, 0, 255, 1), "B");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(20);
        this.setTooltip("Set every LED on the chosen strip(s) to the same colour.");
    }
};

python.pythonGenerator.forBlock['rgb_set_all'] = function (block) {
    const strip = block.getFieldValue('STRIP');
    const r = block.getFieldValue('R');
    const g = block.getFieldValue('G');
    const b = block.getFieldValue('B');
    if (strip === 'both') {
        return `rgb_front.set_all(${r}, ${g}, ${b})\nrgb_back.set_all(${r}, ${g}, ${b})\n`;
    }
    return `${strip}.set_all(${r}, ${g}, ${b})\n`;
};

// ============================================================
//  RGB Strip: Turn OFF (clear)
// ============================================================

Blockly.Blocks['rgb_clear'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🌈 RGB Strip")
            .appendField(new Blockly.FieldDropdown([
                ["Front (8 LEDs)", "rgb_front"],
                ["Back  (8 LEDs)", "rgb_back"],
                ["Both strips",    "both"]
            ]), "STRIP")
            .appendField("Turn OFF all LEDs");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(20);
        this.setTooltip("Turn off every LED on the chosen strip(s).");
    }
};

python.pythonGenerator.forBlock['rgb_clear'] = function (block) {
    const strip = block.getFieldValue('STRIP');
    if (strip === 'both') {
        return `rgb_front.clear()\nrgb_back.clear()\n`;
    }
    return `${strip}.clear()\n`;
};

// ============================================================
//  RGB Strip: Turn ON all LEDs (white or colour)
// ============================================================

Blockly.Blocks['rgb_turn_on'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🌈 RGB Strip")
            .appendField(new Blockly.FieldDropdown([
                ["Front (8 LEDs)", "rgb_front"],
                ["Back  (8 LEDs)", "rgb_back"],
                ["Both strips",    "both"]
            ]), "STRIP")
            .appendField("Turn ON  R")
            .appendField(new Blockly.FieldNumber(255, 0, 255, 1), "R")
            .appendField("G")
            .appendField(new Blockly.FieldNumber(255, 0, 255, 1), "G")
            .appendField("B")
            .appendField(new Blockly.FieldNumber(255, 0, 255, 1), "B");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(20);
        this.setTooltip("Turn on all LEDs to a solid colour (default: white).");
    }
};

python.pythonGenerator.forBlock['rgb_turn_on'] = function (block) {
    const strip = block.getFieldValue('STRIP');
    const r = block.getFieldValue('R');
    const g = block.getFieldValue('G');
    const b = block.getFieldValue('B');
    if (strip === 'both') {
        return `rgb_front.turn_on(${r}, ${g}, ${b})\nrgb_back.turn_on(${r}, ${g}, ${b})\n`;
    }
    return `${strip}.turn_on(${r}, ${g}, ${b})\n`;
};

// ============================================================
//  RGB Strip: Play a built-in effect
// ============================================================

Blockly.Blocks['rgb_effect'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("✨ RGB Effect")
            .appendField(new Blockly.FieldDropdown([
                ["Front strip", "rgb_front"],
                ["Back strip",  "rgb_back"],
                ["Both strips", "both"]
            ]), "STRIP");
        this.appendDummyInput()
            .appendField("Effect")
            .appendField(new Blockly.FieldDropdown([
                ["🌈 Rainbow",      "rainbow"],
                ["🔴 Chase Red",    "chase_red"],
                ["🟢 Chase Green",  "chase_green"],
                ["🔵 Chase Blue",   "chase_blue"],
                ["⚪ Blink White",  "blink_white"],
                ["❤️  Pulse Red",   "pulse_red"],
                ["🚔 Police",       "police"],
                ["🔥 Fire",         "fire"]
            ]), "EFFECT");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(20);
        this.setTooltip("Play a built-in lighting effect on the RGB strip.");
    }
};

python.pythonGenerator.forBlock['rgb_effect'] = function (block) {
    const strip = block.getFieldValue('STRIP');
    const effect = block.getFieldValue('EFFECT');
    if (strip === 'both') {
        return `rgb_front.show_effect("${effect}")\nrgb_back.show_effect("${effect}")\n`;
    }
    return `${strip}.show_effect("${effect}")\n`;
};

// ============================================================
//  Category registration
// ============================================================

EZBOTIX.registerCategory({
    name: "💡 Lights",
    colour: 20,
    blocks: [
        "led_toggle",
        "rgb_set_led",
        "rgb_set_all",
        "rgb_turn_on",
        "rgb_clear",
        "rgb_effect"
    ]
});
