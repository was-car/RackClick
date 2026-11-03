import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareNumberColor} from '../src/hardware-label-contrast.ts';

test('silver product panels use dark port numbers and dark panels retain light numbers',()=>{
 assert.equal(hardwareNumberColor('#c7cbcf'),'#000000');
 assert.equal(hardwareNumberColor('#ffffff'),'#000000');
 assert.equal(hardwareNumberColor('#111923'),'#ffffff');
 assert.equal(hardwareNumberColor('#000000'),'#ffffff');
});

test('all RGB channels and both accepted hex widths affect the contrast decision',()=>{
 assert.equal(hardwareNumberColor('#0f0'),'#000000');
 assert.equal(hardwareNumberColor('#00ff00'),'#000000');
 assert.equal(hardwareNumberColor('#0000FF'),'#ffffff');
 assert.equal(hardwareNumberColor('#f00'),'#000000');
});

test('non-deployment colors cannot become a CSS value in the SVG',()=>{
 for(const value of [null,17,'red','#1234','url(example)','#000;display:none','<svg>'])
  assert.throws(()=>hardwareNumberColor(value),/hardware_label_color_invalid/);
});
