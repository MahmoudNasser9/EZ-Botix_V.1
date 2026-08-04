/**
 * toolbox.js
 *
 * Builds the Blockly toolbox from:
 *   1. Hardware categories registered by js/blocks/*.js
 *   2. A fixed set of standard programming categories (Logic/Loops/Math/Text/Variables)
 *
 * To add a new hardware feature: create js/blocks/yourfeature.js, define its
 * block(s) + generator(s), call EZBOTIX.registerCategory(...), add one
 * <script> tag in index.html. Nothing in this file needs to change.
 */

function buildToolboxXml() {
    const hardwareXml = EZBOTIX.hardwareCategories.map(cat => {
        const blocks = cat.blocks.map(type => {
            if (typeof type === 'string' && type.startsWith('<block')) {
                return type;
            }
            return `<block type="${type}"></block>`;
        }).join('');
        return `<category name="${cat.name}" colour="${cat.colour}">${blocks}</category>`;
    }).join('');

    const standardXml = `
        <category name="⚙️ Logic" colour="210">
            <block type="controls_if"></block>
            <block type="logic_compare"></block>
            <block type="logic_operation"></block>
            <block type="logic_negate"></block>
            <block type="logic_boolean"></block>
            <block type="logic_null"></block>
            <block type="logic_ternary"></block>
        </category>
        <category name="🔄 Loops" colour="120">
            <block type="delay_ms"></block>
            <block type="controls_repeat_ext">
                <value name="TIMES"><block type="math_number"><field name="NUM">5</field></block></value>
            </block>
            <block type="controls_whileUntil"></block>
            <block type="controls_for">
                <value name="FROM"><block type="math_number"><field name="NUM">1</field></block></value>
                <value name="TO"><block type="math_number"><field name="NUM">10</field></block></value>
                <value name="BY"><block type="math_number"><field name="NUM">1</field></block></value>
            </block>
            <block type="controls_forEach"></block>
            <block type="controls_flow_statements"></block>
        </category>
        <category name="🔢 Math" colour="230">
            <block type="math_number"></block>
            <block type="math_arithmetic"></block>
            <block type="math_single"></block>
            <block type="math_trig"></block>
            <block type="math_constant"></block>
            <block type="math_number_property"></block>
            <block type="math_round"></block>
            <block type="math_modulo"></block>
            <block type="math_constrain"></block>
            <block type="math_random_int"></block>
        </category>
        <category name="📝 Text" colour="160">
            <block type="text"></block>
            <block type="text_join"></block>
            <block type="text_append"></block>
            <block type="text_length"></block>
            <block type="text_isEmpty"></block>
        </category>
        <category name="📊 Variables" custom="VARIABLE" colour="330"></category>
    `;

    const xmlString = `<xml>${hardwareXml}<sep></sep>${standardXml}</xml>`;
    return new DOMParser().parseFromString(xmlString, 'text/xml').documentElement;
}
