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
