/**
 * blocks/inputs.js - ⌨️ Inputs category (4x4 matrix keypad)
 */

const KEY_PAD_IS_ENABLE = false;

const inputBlocks = [];

if (KEY_PAD_IS_ENABLE) {
    const KEYPAD_KEYS = [
        "1", "2", "3", "A",
        "4", "5", "6", "B",
        "7", "8", "9", "C",
        "*", "0", "#", "D"
    ];

    Blockly.Blocks['keypad_wait'] = {
        init: function () {
            this.appendDummyInput()
                .appendField("⌨️ Wait until Key")
                .appendField(new Blockly.FieldDropdown(KEYPAD_KEYS.map(k => [k, k])), "KEY")
                .appendField("is pressed");
            this.setPreviousStatement(true, null);
            this.setNextStatement(true, null);
            this.setColour(65);
        }
    };

    python.pythonGenerator.forBlock['keypad_wait'] = function (block) {
        return `keypad.wait_for_key("${block.getFieldValue('KEY')}")\n`;
    };

    inputBlocks.push("keypad_wait");
}

// Single push button at D19
Blockly.Blocks['button_is_pressed'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🔘 Button is pressed?");
        this.setOutput(true, "Boolean");
        this.setColour(65);
    }
};

python.pythonGenerator.forBlock['button_is_pressed'] = function (block) {
    return [`button.is_pressed()`, python.Order.FUNCTION_CALL];
};

inputBlocks.push("button_is_pressed");

// IR Sensor
Blockly.Blocks['ir_obstacle_detected'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("👀 Obstacle is detected?");
        this.setOutput(true, "Boolean");
        this.setColour(65);
    }
};

python.pythonGenerator.forBlock['ir_obstacle_detected'] = function (block) {
    return [`ir_sensor.is_obstacle_detected()`, python.Order.FUNCTION_CALL];
};

Blockly.Blocks['ir_digital_value'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("👀 IR digital value");
        this.setOutput(true, "Number");
        this.setColour(65);
    }
};

python.pythonGenerator.forBlock['ir_digital_value'] = function (block) {
    return [`ir_sensor.get_digital_value()`, python.Order.FUNCTION_CALL];
};

inputBlocks.push("ir_obstacle_detected", "ir_digital_value");

EZBOTIX.registerCategory({
    name: "⌨️ Inputs",
    colour: 65,
    blocks: inputBlocks
});
