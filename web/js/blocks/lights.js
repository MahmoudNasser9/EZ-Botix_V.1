/**
 * blocks/lights.js - 💡 Lights category (onboard and external LEDs)
 */

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

EZBOTIX.registerCategory({
    name: "💡 Lights",
    colour: 20,
    blocks: ["led_toggle"]
});
