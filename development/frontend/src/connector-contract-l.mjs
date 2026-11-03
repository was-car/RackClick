import {extendRc9ConnectorContract as extendFamily,physicalConnectorLabel as familyLabel} from './connector-contract-family.mjs';
import {extendedConnectorMetadata} from './hardware-connector-family-l.mjs';
export const physicalConnectorLabel=type=>extendedConnectorMetadata[type]?.label||familyLabel(type);
export function extendRc9ConnectorContract(metadataSource,physicalSource){
 const prior=extendFamily(metadataSource,physicalSource),anchor='function IRPortShape({type,role}){';
 if(prior.physicalSource.split(anchor).length!==2)throw Error('RC9 extended connector anchor mismatch');
 return {metadataSource:"import {ExtendedConnectorShape} from '../src/ExtendedConnectorShape.jsx';\n"+prior.metadataSource+'\nObject.assign(PT,'+JSON.stringify(extendedConnectorMetadata)+');\n',physicalSource:prior.physicalSource.replace(anchor,anchor+'if('+JSON.stringify(Object.keys(extendedConnectorMetadata))+'.includes(type))return <ExtendedConnectorShape type={type} inline/>;')};
}
