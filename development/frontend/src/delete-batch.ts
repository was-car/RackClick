import {ApiError} from './api.ts';
import {type Project} from './inventory-model.ts';

// Keep the user's exact selection. A refreshed snapshot may invalidate the whole
// batch, but must never turn it into a smaller, silently filtered deletion.
export function prepareDeleteBatch(project:Project,deviceIds:string[]){
 const uuid=(x:unknown):x is string=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
 if(!Array.isArray(deviceIds)||!deviceIds.length||deviceIds.length>64||!deviceIds.every(uuid)||new Set(deviceIds.map(id=>id.toLowerCase())).size!==deviceIds.length)throw new ApiError(422,'device_selection_invalid');
 if(deviceIds.some(id=>!project.devices.some(d=>d.id.toLowerCase()===id.toLowerCase())))throw new ApiError(422,'device_selection_stale');
 return {type:'devices.delete',payload:{deviceIds:[...deviceIds]}};
}
