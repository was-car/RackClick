// Own implementation of W3C sRGB relative luminance. Closed deployment colors,
// never CSS/HTML supplied by a customer. Black/white maximize text contrast.
// https://www.w3.org/WAI/WCAG22/Understanding/relative-luminance.html
export function hardwareNumberColor(fill: string): string {
 if(typeof fill!=='string'||!/^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i.test(fill))throw Error('hardware_label_color_invalid');
 const hex=fill.length===4?fill.slice(1).split('').map(c=>c+c).join(''):fill.slice(1);
 const channels=[0,2,4].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
 const l=.2126*channels[0]+.7152*channels[1]+.0722*channels[2];
 return (l+.05)/.05>=1.05/(l+.05)?'#000000':'#ffffff';
}
