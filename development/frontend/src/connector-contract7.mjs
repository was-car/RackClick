// Build-time adaptation only; the adopted RC9 source and previous PT values stay intact.
export const additionalConnectorMetadata=Object.freeze({
 sfp56:Object.freeze({label:'SFP56',shape:'rect',color:'#06b6d4'}),
 qsfpdd:Object.freeze({label:'QSFP-DD',shape:'wide',color:'#f97316'})
});
export const physicalConnectorLabel=type=>additionalConnectorMetadata[type]?.label||type;
export function extendRc9ConnectorContract(metadataSource,physicalSource){
 const anchor='function IRPortShape({type,role}){';
 if(typeof metadataSource!=='string'||metadataSource.split('const PT =').length!==2||typeof physicalSource!=='string'||physicalSource.split(anchor).length!==2)throw Error('RC9 connector contract anchor mismatch');
 return {metadataSource:"import {OpticalConnectorShape} from '../src/OpticalConnectorShape.jsx';\n"+metadataSource+'\nObject.assign(PT,'+JSON.stringify(additionalConnectorMetadata)+');\n',physicalSource:physicalSource.replace(anchor,anchor+"if(type==='sfp56'||type==='qsfpdd')return <OpticalConnectorShape type={type} inline/>;")};
}
