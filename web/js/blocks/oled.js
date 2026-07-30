/**
 * oled.js
 *
 * Defines Blockly blocks and MicroPython generators for:
 *   1. show text (manual size)
 *   2. show text smart-fit (auto-size)
 *   3. show emoji (static)
 *   4. animate eyes (20+ smooth animations)
 */

// ============================================================= 1. MANUAL TEXT
Blockly.Blocks['oled_show_text'] = {
    init: function () {
        this.appendValueInput("TEXT")
            .setCheck(null)
            .appendField("📺 OLED show text");
        this.appendDummyInput()
            .appendField("  size")
            .appendField(new Blockly.FieldDropdown([
                ["Small (1)",  "1"],
                ["Medium (2)", "2"],
                ["Large (3)",  "3"],
                ["Huge (4)",   "4"]
            ]), "SIZE");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(195);
        this.setTooltip("Display text at a chosen size. Longer text wraps automatically.");
        this.setHelpUrl("");
    }
};

python.pythonGenerator.forBlock['oled_show_text'] = function (block) {
    var text = python.pythonGenerator.valueToCode(block, 'TEXT', python.Order.ATOMIC) || '""';
    var size = block.getFieldValue('SIZE');
    return `oled.show_text(${text}, size=${size})\n`;
};

// ============================================================= 2. SMART-FIT TEXT
Blockly.Blocks['oled_show_text_fit'] = {
    init: function () {
        this.appendValueInput("TEXT")
            .setCheck(null)
            .appendField("📺 OLED smart-fit text");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(195);
        this.setTooltip(
            "Automatically picks the largest text size that fits on screen. " +
            "Short text = huge letters. Long text = small letters."
        );
        this.setHelpUrl("");
    }
};

python.pythonGenerator.forBlock['oled_show_text_fit'] = function (block) {
    var text = python.pythonGenerator.valueToCode(block, 'TEXT', python.Order.ATOMIC) || '""';
    return `oled.show_text_fit(${text})\n`;
};

// ============================================================= 3. STATIC EMOJI
Blockly.Blocks['oled_show_emoji'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("📺 OLED show emoji")
            .appendField(new Blockly.FieldDropdown([
                ["❤️ Heart",                    "heart"],
                ["🥺 Cute Eyes",                "cute_eyes"],
                ["😠 Angry Eyes",               "angry_eyes"],
                ["👀 Big Eyes (Intellar)",       "big_eyes"],
                ["👁️ Hollow Eyes (SpiderMaf)",  "hollow_eyes"],
                ["😑 Wide Eyes (Abdulsalam)",    "wide_eyes"],
                ["👽 Tall Eyes (Vinny)",         "tall_eyes"],
                ["⬛ Small Eyes (Picaio)",       "small_eyes"]
            ]), "EMOJI");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(195);
        this.setTooltip("Displays a predefined emoji or eye shape on the OLED screen.");
        this.setHelpUrl("");
    }
};

python.pythonGenerator.forBlock['oled_show_emoji'] = function (block) {
    var emoji = block.getFieldValue('EMOJI');
    return `oled.show_emoji("${emoji}")\n`;
};

// ============================================================= 4. ANIMATE EYES
Blockly.Blocks['oled_animate_eyes'] = {
    init: function () {
        this.appendDummyInput()
            .appendField("📺 OLED animate")
            .appendField(new Blockly.FieldDropdown([
                // --- Blink & Wink ---
                ["👁️ Blink",              "blink"],
                ["👁️👁️ Double Blink",    "double_blink"],
                ["😉 Wink Left",          "wink_left"],
                ["😉 Wink Right",         "wink_right"],
                // --- Look Around ---
                ["👈 Look Left",          "look_left"],
                ["👉 Look Right",         "look_right"],
                ["👆 Look Up",            "look_up"],
                ["👇 Look Down",          "look_down"],
                ["↖️ Look Top-Left",      "look_topleft"],
                ["↗️ Look Top-Right",     "look_topright"],
                ["↙️ Look Bottom-Left",   "look_botleft"],
                ["↘️ Look Bottom-Right",  "look_botright"],
                // --- Mood / Expression ---
                ["😊 Happy",             "happy"],
                ["😠 Angry",             "angry"],
                ["😢 Sad",               "sad"],
                ["😲 Surprised",         "surprised"],
                ["😕 Confused",          "confused"],
                // --- Special FX ---
                ["🌀 Spin",              "spin"],
                ["😵 Dizzy",             "dizzy"],
                ["😴 Sleepy",            "sleepy"],
                ["🤩 Excited",           "excited"],
                ["⚡ Flicker",            "flicker"],
                ["💀 Glitch",             "glitch"],
                ["💓 Heartbeat",         "heartbeat"]
            ]), "ANIM");
        this.appendDummyInput()
            .appendField("  style")
            .appendField(new Blockly.FieldDropdown([
                ["Big Eyes (Intellar)",     "big_eyes"],
                ["Hollow Eyes (SpiderMaf)", "hollow_eyes"],
                ["Wide Eyes (Abdulsalam)",  "wide_eyes"],
                ["Tall Eyes (Vinny)",       "tall_eyes"],
                ["Cute Eyes",              "cute_eyes"],
                ["Small Eyes (Picaio)",     "small_eyes"]
            ]), "STYLE");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(195);
        this.setTooltip(
            "Plays a smooth animation on the OLED. " +
            "The animation runs once then leaves the eyes open."
        );
        this.setHelpUrl("");
    }
};

python.pythonGenerator.forBlock['oled_animate_eyes'] = function (block) {
    var anim  = block.getFieldValue('ANIM');
    var style = block.getFieldValue('STYLE');
    return `oled.animate_eyes(style="${style}", animation="${anim}")\n`;
};

// ============================================================= CATEGORY
EZBOTIX.registerCategory({
    name: "📺 OLED",
    colour: 195,
    blocks: [
        "oled_show_text",
        "oled_show_text_fit",
        "oled_show_emoji",
        "oled_animate_eyes"
    ]
});
