/**
 * blocks/ultrasonic.js - 📡 Sensors category
 */

const ultrasonicBlocks = [];

Blockly.Blocks['ultrasonic_get_distance'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("📡 Get Ultrasonic distance (cm)");
        this.setOutput(true, "Number");
        this.setColour(65);
        this.setTooltip("Get the distance measured by the ultrasonic sensor in cm");
    }
};

python.pythonGenerator.forBlock['ultrasonic_get_distance'] = function (block) {
    return [`ultrasonic.distance_cm()`, python.Order.FUNCTION_CALL];
};

ultrasonicBlocks.push("ultrasonic_get_distance");

EZBOTIX.registerCategory({
    name: "📡 Sensors",
    colour: 65,
    blocks: ultrasonicBlocks
});
