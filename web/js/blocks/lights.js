/**
 * blocks/lights.js - 💡 Lights category (onboard LED)
 *
 * Pattern for every hardware block file:
 *   1. Define the Blockly.Blocks[...] shape
 *   2. Define its python.pythonGenerator.forBlock[...] code generator
 *   3. Call EZBOTIX.registerCategory(...) once, listing every block type
 *      that belongs in this category
 */

Blockly.Blocks['led_toggle'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("💡 Onboard LED")
            .appendField(new Blockly.FieldDropdown([["ON", "1"], ["OFF", "0"]]), "STATE");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(20);
    }
};

python.pythonGenerator.forBlock['led_toggle'] = function (block) {
    return `onboard_led.value(${block.getFieldValue('STATE')})\n`;
};

EZBOTIX.registerCategory({
    name: "💡 Lights",
    colour: 20,
    blocks: ["led_toggle"]
});
