/**
 * blocks/inputs.js - ⌨️ Inputs category (4x4 matrix keypad)
 */

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

EZBOTIX.registerCategory({
    name: "⌨️ Inputs",
    colour: 65,
    blocks: ["keypad_wait"]
});
