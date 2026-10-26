import {InventoryCatalogBrowser} from './InventoryCatalogBrowser.jsx';
import {favoriteWords} from './catalog-favorites-words.ts';
import {catalogWords} from './inventory-catalog-words.ts';
import {inventoryWords} from './inventory-words.ts';
import {inventoryError} from './OperationDialog.jsx';
const {useState,useEffect,useRef}=React;
export function InventoryCatalogDialog({api,session,project,lang,onClose,onRefresh}){
 const [form,setForm]=useState({catalogKey:'',catalogCategory:'',catalogQuery:'',catalogOnlyFavorites:false,catalogue:null,catalogueActor:''}),[snapshot,setSnapshot]=useState(project),[busy,setBusy]=useState(false),[error,setError]=useState(null),ref=useRef(null),f=favoriteWords[lang];
 useEffect(()=>{ref.current.showModal()},[]);
 async function refresh(){setBusy(true);try{setSnapshot(await onRefresh());setError(null)}catch(e){setError(e)}finally{setBusy(false)}}
 return <dialog ref={ref} className="ir-dialog rc-operation-dialog" data-catalog-dialog aria-labelledby="catalog-title" onCancel={e=>{if(busy)e.preventDefault();else onClose()}}><div className="rc-form" style={{minWidth:0,gridTemplateColumns:'minmax(0,1fr)',overflowWrap:'anywhere'}}><header><h2 id="catalog-title">{catalogWords[lang].catalog}</h2></header><p>{f.readOnly}</p><InventoryCatalogBrowser api={api} actorId={session.user.id} userName={session.user.userName} project={snapshot} lang={lang} form={form} setForm={setForm} disabled={busy} onRefresh={refresh}/>{error&&<p role="alert" className="rc-error">{inventoryError(error,inventoryWords[lang])}</p>}<footer><button type="button" data-catalog-close disabled={busy} onClick={onClose}>{f.close}</button></footer></div></dialog>;
}
