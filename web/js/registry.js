/**
 * registry.js
 *
 * Registry of hardware block categories shown in the toolbox.
 *
 * Each file in js/blocks/ owns one hardware category. At load time it
 * defines its Blockly block(s) + Python generator(s), then calls
 * EZBOTIX.registerCategory() once to describe its toolbox entry.
 *
 * toolbox.js reads this registry to assemble the toolbox - so adding a
 * brand new hardware feature (a servo, a sensor, a buzzer...) never
 * requires touching toolbox.js or any other block file.
 */

window.EZBOTIX = window.EZBOTIX || {};
EZBOTIX.hardwareCategories = [];

/**
 * @param {{name: string, colour: number, blocks: string[]}} categoryDef
 */
EZBOTIX.registerCategory = function (categoryDef) {
    EZBOTIX.hardwareCategories.push(categoryDef);
};
