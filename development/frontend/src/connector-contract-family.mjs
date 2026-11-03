import {extendRc9ConnectorContract as extendSeven,physicalConnectorLabel as sevenLabel} from './connector-contract7.mjs';
export const familyConnectorMetadata=Object.freeze({idc:Object.freeze({label:'IDC',shape:'rect',color:'#a3b86c'})});
export const physicalConnectorLabel=type=>familyConnectorMetadata[type]?.label||sevenLabel(type);
export function extendRc9ConnectorContract(metadataSource,physicalSource){
 const prior=extendSeven(metadataSource,physicalSource),anchor='function IRPortShape({type,role}){';
 if(prior.physicalSource.split(anchor).length!==2)throw Error('RC9 family connector anchor mismatch');
 return {metadataSource:"import {FamilyConnectorShape} from '../src/FamilyConnectorShape.jsx';\n"+prior.metadataSource+'\nObject.assign(PT,'+JSON.stringify(familyConnectorMetadata)+');\n',physicalSource:prior.physicalSource.replace(anchor,anchor+"if(type==='idc')return <FamilyConnectorShape type={type} inline/>;")};
}
