// Physical classification, not cable, signalling or electrical certification.
// The K vocabulary remains unchanged; L adds independently closed media.
export const extendedConnectorDescriptors=Object.freeze({
 power:Object.freeze(['schuko-f','eu-2pin-plug']),
 ipc:Object.freeze(['belden-revconnect-core']),
 fiber:Object.freeze(['lc-duplex-upc','lc-simplex-upc','sc-duplex-upc','sc-simplex-upc','sc-simplex-apc']),
 sas:Object.freeze(['sff-8644','sff-8088']),
 sfpdd:Object.freeze(['sfp-dd']),
 cfp2:Object.freeze(['cfp2']),
 dsl:Object.freeze(['dsl-8p8c','dsl-rj11']),
 telephony:Object.freeze(['voice-8p8c','voice-rj11','voice-tae']),
 isdn:Object.freeze(['isdn-8p8c']),
 expansion:Object.freeze(['avaya-ipoffice-expansion-8p8c']),
 power_dc:Object.freeze(['dc-barrel','unifi-smartpower','usb-c-pd','dc-terminal-2p','dc-terminal-3p','dc-terminal-6p']),
 console:Object.freeze(['serial-mini-din8','serial-usb-c','serial-mini-usb','serial-micro-usb'])
});
export const extendedConnectorMetadata=Object.freeze({
 ipc:Object.freeze({label:'IPC',shape:'rect',color:'#b39d6b'}),
 fiber:Object.freeze({label:'FIBER',shape:'rect',color:'#62b6ad'}),
 sfpdd:Object.freeze({label:'SFP-DD',shape:'rect',color:'#57a4d2'}),
 cfp2:Object.freeze({label:'CFP2',shape:'rect',color:'#9673c4'}),
 sas:Object.freeze({label:'SAS',shape:'rect',color:'#c39c70'}),
 dsl:Object.freeze({label:'DSL',shape:'rect',color:'#d5ad69'}),
 telephony:Object.freeze({label:'PHONE',shape:'rect',color:'#bd8fb5'}),
 isdn:Object.freeze({label:'ISDN',shape:'rect',color:'#a9a0d5'}),
 expansion:Object.freeze({label:'EXPANSION',shape:'rect',color:'#b89287'}),
 power_dc:Object.freeze({label:'DC',shape:'rect',color:'#e49f66'})
});
export const isExtendedConnector=(type,value)=>typeof value==='string'&&!!extendedConnectorDescriptors[type]?.includes(value);
export const extendedConnectorLabel=(type,value)=>isExtendedConnector(type,value)?value.replaceAll('-',' ').toUpperCase():extendedConnectorMetadata[type]?.label||type;
