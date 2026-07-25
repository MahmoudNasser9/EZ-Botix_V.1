/**
 * blocks/motion.js - 🛞 Motion category (car movement)
 */

Blockly.Blocks['car_move'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🛞 Move Car")
            .appendField(new Blockly.FieldDropdown([
                ["Forward", "FORWARD"],
                ["Backward", "BACKWARD"],
                ["Turn Left", "LEFT"],
                ["Turn Right", "RIGHT"],
                ["Stop", "STOP"]
            ]), "DIRECTION");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
    }
};

python.pythonGenerator.forBlock['car_move'] = function (block) {
    return `car.move("${block.getFieldValue('DIRECTION')}")\n`;
};

EZBOTIX.registerCategory({
    name: "🛞 Motion",
    colour: 160,
    blocks: ["car_move"]
});
