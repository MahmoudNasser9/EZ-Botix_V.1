/**
 * oled.js
 * 
 * Defines blocks and generators for the OLED display module.
 */

// 1. Define the Blocks
Blockly.Blocks['oled_show_text'] = {
    init: function () {
        this.appendValueInput("TEXT")
            .setCheck(null)
            .appendField("📺 show text on OLED");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(195);
        this.setTooltip("Displays text on the OLED screen.");
        this.setHelpUrl("");
    }
};

Blockly.Blocks['oled_show_emoji'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("📺 show emoji on OLED")
            .appendField(new Blockly.FieldDropdown([
                ["❤️ Heart", "heart"],
                ["🥺 Cute Eyes", "cute_eyes"],
                ["😠 Angry Eyes", "angry_eyes"]
            ]), "EMOJI");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(195);
        this.setTooltip("Displays a predefined emoji on the OLED screen.");
        this.setHelpUrl("");
    }
};

// 2. Define the Python Code Generators
Blockly.Python['oled_show_text'] = function (block) {
    var text = Blockly.Python.valueToCode(block, 'TEXT', Blockly.Python.ORDER_ATOMIC) || '""';
    return 'oled.show_text(' + text + ')\n';
};

Blockly.Python['oled_show_emoji'] = function (block) {
    var dropdown_emoji = block.getFieldValue('EMOJI');
    return 'oled.show_emoji("' + dropdown_emoji + '")\n';
};

// 3. Register the Hardware Category
if (window.EZBOTIX && EZBOTIX.registerCategory) {
    EZBOTIX.registerCategory({
        name: "📺 OLED",
        colour: 195,
        blocks: [
            "oled_show_text",
            "oled_show_emoji"
        ]
    });
}
