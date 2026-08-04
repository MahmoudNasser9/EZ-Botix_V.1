/**
 * blocks/motion.js - 🚗 Motion category (car movement)
 */

Blockly.Blocks['car_move'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🏎️💨 Move Car")
            .appendField(new Blockly.FieldDropdown([
                ["Forward ⬆️", "FORWARD"],
                ["Backward ⬇️", "BACKWARD"],
                ["Turn Left ⬅️", "LEFT"],
                ["Turn Right ➡️", "RIGHT"],
                ["Stop 🛑", "STOP"]
            ]), "DIRECTION");

        this.appendValueInput("SPEED")
            .setCheck("Number")
            .appendField("at speed (%)");

        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip("Allowed values are -100 to 100.\nPositive numbers drive forward.\nNegative (-) numbers drive backward.");
    }
};

python.pythonGenerator.forBlock['car_move'] = function (block) {
    const direction = block.getFieldValue('DIRECTION');

    if (direction === 'STOP') {
        return `car.stop()\n`;
    }

    // Get speed, default to 50 if the block is not attached.
    const speed = python.pythonGenerator.valueToCode(block, 'SPEED', python.pythonGenerator.ORDER_NONE) || '50';

    if (direction === 'FORWARD') {
        return `car.forward(${speed})\n`;
    } else if (direction === 'BACKWARD') {
        return `car.backward(${speed})\n`;
    } else if (direction === 'LEFT') {
        return `car.turn_left(${speed})\n`;
    } else if (direction === 'RIGHT') {
        return `car.turn_right(${speed})\n`;
    }
    return `car.stop()\n`;
};

Blockly.Blocks['car_drive_wheels'] = {
    init: function () {
        this.appendValueInput("LEFT_SPEED")
            .setCheck("Number")
            .appendField("🚗 Drive Left Motor (%)");
        this.appendValueInput("RIGHT_SPEED")
            .setCheck("Number")
            .appendField("Right Motor (%)");

        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip("Allowed values are -100 to 100.\nPositive numbers drive forward.\nNegative (-) numbers drive backward.");
    }
};

python.pythonGenerator.forBlock['car_drive_wheels'] = function (block) {
    const leftSpeed = python.pythonGenerator.valueToCode(block, 'LEFT_SPEED', python.pythonGenerator.ORDER_NONE) || '0';
    const rightSpeed = python.pythonGenerator.valueToCode(block, 'RIGHT_SPEED', python.pythonGenerator.ORDER_NONE) || '0';

    return `car.drive(${leftSpeed}, ${rightSpeed})\n`;
};

EZBOTIX.registerCategory({
    name: "🚗 Motion",
    colour: 160,
    blocks: [
        `<block type="car_move">
            <value name="SPEED"><shadow type="math_number"><field name="NUM">50</field></shadow></value>
        </block>`,
        `<block type="car_drive_wheels">
            <value name="LEFT_SPEED"><shadow type="math_number"><field name="NUM">50</field></shadow></value>
            <value name="RIGHT_SPEED"><shadow type="math_number"><field name="NUM">50</field></shadow></value>
        </block>`
    ]
});
