import assert from 'node:assert/strict';
import { runScenario, infrastructure, snapshot, normalize, fixture as ids } from './browser-quince-support.mjs';
import { inventoryLayoutWords } from '../src/inventory-layout-words.ts';

const baseline = process.env.RACKCLICK_LAYOUT_BASELINE === '1';
await runScenario(async ({ first, session, checks, shot, origin }) => {
  assert.equal(await first.evaluate(`document.querySelectorAll('[data-customer-id]').length`), 10);
  await infrastructure(first);
  const original = normalize(await snapshot(first));
  const firstCard = `[data-rack-id="${ids.firstRack}"] .rc-rack-open`;
  const metrics = () => first.evaluate(`(()=>{const n=document.querySelector(${JSON.stringify(firstCard)}),r=n.getBoundingClientRect();return {top:r.top,height:r.height,viewport:innerHeight,visible:r.width>0&&r.height>0}})()`);
  if (baseline) {
    const before = await metrics();
    assert.ok(before.top > before.viewport, 'historical layout places the first rack below the viewport');
    await shot(first, 'before-client.png');
    checks.push('Historical build reproduces first rack below the initial viewport with original synthetic data');
    return;
  }
  async function primaryVisible() {
    const position = await metrics();
    assert.ok(position.visible && position.top < position.viewport - 40, JSON.stringify(position));
    assert.equal(await first.evaluate(`document.querySelector('[data-hierarchy-details]').open`), false);
    assert.equal(await first.evaluate(`document.querySelector('[data-poe-budget-summary]').open`), false);
    assert.ok(await first.evaluate(`!!(document.querySelector('[data-primary-inventory]').compareDocumentPosition(document.querySelector('[data-secondary-information]'))&Node.DOCUMENT_POSITION_FOLLOWING)`));
  }
  await primaryVisible();
  await shot(first, 'after-client-desktop.png');
  checks.push('Racks precede hierarchy, PoE and reports; hierarchy and read-only PoE start collapsed');

  for (const lang of ['en', 'de', 'es']) {
    await first.click('.ir-all-clients');
    await first.wait(`!!document.querySelector('.rc-settings select')`, 'language control');
    await first.field('.rc-settings select', lang);
    await infrastructure(first);
    await primaryVisible();
    assert.equal(await first.evaluate(`document.querySelector('[data-secondary-tools]').textContent`), inventoryLayoutWords[lang].tools);
    assert.equal(await first.evaluate(`document.querySelector('[data-back-to-racks]').textContent`), inventoryLayoutWords[lang].back);
    assert.equal(normalize(await snapshot(first)).racks.find(r => r.id === ids.rack).name, original.racks.find(r => r.id === ids.rack).name);
  }
  checks.push('EN/DE/ES labels correct; literal inventory names unchanged');
  await first.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await first.evaluate('scrollTo(0,0)');
  await primaryVisible();
  assert.ok(await first.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), 'no horizontal overflow at 390px');
  await shot(first, 'after-client-mobile.png');
  await first.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });

  await first.click('[data-secondary-tools]');
  assert.equal(await first.evaluate(`document.activeElement.hasAttribute('data-secondary-information')`), true);
  await first.send('Page.bringToFront');
  await first.evaluate(`document.querySelector('[data-poe-budget-summary]>summary').focus()`);
  assert.equal(await first.evaluate(`document.activeElement===document.querySelector('[data-poe-budget-summary]>summary')`), true);
  await first.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' });
  await first.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  await first.wait(`document.querySelector('[data-poe-budget-summary]').open`, 'native keyboard disclosure');
  await first.send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, text: ' ', unmodifiedText: ' ' });
  await first.send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 });
  await first.wait(`!document.querySelector('[data-poe-budget-summary]').open`, 'native disclosure close');
  await first.click('[data-back-to-racks]');
  assert.equal(await first.evaluate(`document.activeElement.hasAttribute('data-primary-inventory')`), true);
  checks.push('Secondary shortcut/back focus correctly; native PoE disclosure works with keyboard');

  await first.click(`[data-rack-id="${ids.rack}"] .rc-rack-open`);
  await first.wait(`!!document.querySelector('[data-vport="${ids.port}"]')`, 'physical rack');
  assert.ok(await first.evaluate(`document.querySelector('[data-primary-inventory]').getBoundingClientRect().top<innerHeight`));
  await first.evaluate(`document.querySelector('[data-vport="${ids.port}"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);
  await first.wait(`!!document.querySelector('.ir-connect-hint')`, 'Click-Click selection');
  const selection = await first.evaluate(`document.querySelector('.ir-connect-hint').textContent`);
  await first.click('[data-secondary-tools]');
  await first.click('[data-rack-svg-toggle]');
  await first.field('[data-rack-svg-rack]', ids.rack);
  await first.field('[data-rack-svg-face]', 'rear');
  await first.click('[data-back-to-racks]');
  assert.equal(await first.evaluate(`document.querySelector('.ir-connect-hint').textContent`), selection);
  await first.click('[data-secondary-tools]');
  assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-rack]').value`), ids.rack);
  assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-face]').value`), 'rear');
  checks.push('Rack/Click-Click selection and report form survive secondary navigation without remounting');

  await first.send('Network.setBlockedURLs', { urls: [origin + '/api/v1/customers/' + ids.customer + '/reports/rack-svg'] });
  await first.click('[data-rack-svg-generate]');
  await first.wait(`!!document.querySelector('[data-rack-svg-pending]')&&!!document.querySelector('[data-rack-svg-error]')`, 'uncertain report request');
  const requestId = await first.evaluate(`document.querySelector('[data-rack-svg-request]').textContent`);
  assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-toggle]').disabled`), true);
  await first.click('[data-back-to-racks]');
  await first.click('[data-secondary-tools]');
  assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-request]').textContent`), requestId);
  assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-error]').getBoundingClientRect().height>0`), true);
  await first.send('Network.setBlockedURLs', { urls: [] });
  await first.click('[data-rack-svg-retry]');
  await first.wait(`!!document.querySelector('[data-rack-svg-download]')&&!document.querySelector('[data-rack-svg-pending]')`, 'same report request confirmed');
  assert.deepEqual(normalize(await snapshot(first)), original);
  checks.push('Uncertain report/error stays visible and retained; same request retry confirms without inventory writes');

  await first.click('[data-read-toggle]');
  await first.field('[data-read-filter="kind"]', 'site');
  await first.wait(`!!document.querySelector('[data-read-navigate="${ids.site}"]')`, 'site search result');
  await first.click('[data-read-navigate="' + ids.site + '"]');
  await first.wait(`document.querySelector('[data-hierarchy-details]').open&&document.activeElement?.getAttribute('data-site-id')===${JSON.stringify(ids.site)}`, 'hierarchy opened before navigation focus');
  checks.push('Search navigation opens the folded hierarchy before focusing the site');

  const second = await session();
  await infrastructure(second);
  assert.equal(await second.evaluate(`document.querySelector('[data-hierarchy-details]').open`), false);
  assert.equal(await second.evaluate(`document.querySelector('[data-poe-budget-summary]').open`), false);
  assert.deepEqual(normalize(await snapshot(second)), original);
  await first.send('Page.reload');
  await first.wait(`!!document.querySelector('[data-customer-id="${ids.customer}"]')`, 'reload');
  await infrastructure(first);
  await first.evaluate('scrollTo(0,0)');
  await primaryVisible();
  assert.deepEqual(normalize(await snapshot(first)), original);
  await shot(first, 'after-reload.png');
  checks.push('Reload and independent browser session retain exact original inventory and start with racks first');
});
