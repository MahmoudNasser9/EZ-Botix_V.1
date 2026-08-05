/**
 * blocks/buzzer.js - 🔊 Sound category (Passive Buzzer)
 *
 * Pattern for every hardware block file:
 *   1. Define the Blockly.Blocks[...] shape
 *   2. Define its python.pythonGenerator.forBlock[...] code generator
 *   3. Call EZBOTIX.registerCategory(...) once, listing every block type
 *      that belongs in this category
 */

Blockly.Blocks['buzzer_play_tone'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🔊 Play Tone")
            .appendField("Frequency (Hz)")
            .appendField(new Blockly.FieldNumber(2048, 0, 20000), "FREQ");
        this.appendDummyInput()
            .appendField("Duration (ms)")
            .appendField(new Blockly.FieldNumber(500, 0, 60000), "DURATION");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(300);
        this.setTooltip("Plays a tone on the passive buzzer.");
    }
};

python.pythonGenerator.forBlock['buzzer_play_tone'] = function (block) {
    var freq = block.getFieldValue('FREQ');
    var duration = block.getFieldValue('DURATION');
    return `buzzer.play_tone(${freq}, ${duration})\n`;
};

Blockly.Blocks['buzzer_stop'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🔊 Stop Buzzer");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(300);
        this.setTooltip("Immediately stops the buzzer from playing.");
    }
};

python.pythonGenerator.forBlock['buzzer_stop'] = function (block) {
    return `buzzer.stop()\n`;
};

Blockly.Blocks['buzzer_play_melody'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("🎵 Play Melody")
            .appendField(new Blockly.FieldDropdown([
                ["Super Mario", "Mario"],
                ["Star Wars", "StarWars"],
                ["Police Siren", "Siren"],
                ["Happy Birthday", "Happy"],
                ["Car Horn", "CarHorn"],
                ["Truck Horn", "TruckHorn"],
                ["Power Up", "PowerUp"],
                ["Power Down", "PowerDown"],
                ["Error Bzzzt", "Error"],
                ["Success Ding", "Success"],
                ["Mission Impossible", "MissionImpossible"]
            ]), "MELODY");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(300);
        this.setTooltip("Plays a pre-programmed melody on the buzzer.");
    }
};

python.pythonGenerator.forBlock['buzzer_play_melody'] = function (block) {
    var melody = block.getFieldValue('MELODY');
    return `buzzer.play_melody("${melody}")\n`;
};

EZBOTIX.registerCategory({
    name: "🔊 Sound",
    colour: 300,
    blocks: ["buzzer_play_tone", "buzzer_play_melody", "buzzer_stop"]
});
