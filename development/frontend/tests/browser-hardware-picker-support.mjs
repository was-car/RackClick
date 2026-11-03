// Drive the same visible search/selection that an operator uses. Never set a hidden value.
export async function chooseHardware(tab,key,revision) {
 const value=JSON.stringify([key,revision]);
 await tab.field('[data-hardware-profile]',key+' '+revision);
 const option='[data-hardware-choice='+JSON.stringify(value)+']';
 await tab.wait(`!!document.querySelector(${JSON.stringify(option)})`,'exact hardware search result');
 await tab.click(option);
 await tab.wait(`!!document.querySelector('[data-hardware-selected]')&&document.querySelector('[data-hardware-selected]').dataset.hardwareSelected===${JSON.stringify(value)}`,'explicit hardware selection');
}
