import {hardwareChoiceValue} from './hardware-mounting.ts';
import {profileLabel} from './hardware-words.ts';
import {searchHardwareProfiles} from './hardware-profile-search.ts';
const {useState,useMemo,useRef,useEffect,useId}=React;
export function HardwareProfilePicker({choices,selected,onChoose,onSearch,disabled,w}) {
 const id=useId(),input=useRef(null),root=useRef(null);
 const [query,setQuery]=useState(''),[expanded,setExpanded]=useState(false),[active,setActive]=useState(-1);
 const matches=useMemo(()=>searchHardwareProfiles(choices,query),[choices,query]);
 const open=expanded&&!disabled;
 useEffect(()=>{if(disabled){setExpanded(false);setActive(-1)}},[disabled]);
 useEffect(()=>{input.current?.setCustomValidity(selected?'':w.chooseProduct)},[selected,w]);
 useEffect(()=>{if(open&&active>=0)root.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({block:'nearest'})},[active,open]);
 function choose(profile){if(disabled)return;onChoose(profile);setQuery('');setExpanded(false);setActive(-1);input.current?.focus()}
 function keyboard(event){
  if(event.key==='Escape'&&open){event.preventDefault();event.stopPropagation();setExpanded(false);setActive(-1)}
  else if(event.key==='ArrowDown'||event.key==='ArrowUp'){
   event.preventDefault();setExpanded(true);
   setActive(current=>matches.length?Math.max(0,Math.min(matches.length-1,current+(event.key==='ArrowDown'?1:-1))):-1);
  }else if(event.key==='Enter'&&open){event.preventDefault();if(active>=0&&matches[active])choose(matches[active])}
 }
 return <div className="rc-hardware-picker" ref={root} onBlur={event=>{if(!event.currentTarget.contains(event.relatedTarget)){setExpanded(false);setActive(-1)}}}>
  <label htmlFor={id}>{w.profile}</label>
  <div className="rc-hardware-search-row"><input id={id} ref={input} data-hardware-profile role="combobox" aria-autocomplete="list" aria-expanded={open} aria-controls={id+'-list'} aria-activedescendant={open&&active>=0?id+'-option-'+active:undefined} aria-describedby={id+'-hint'+(selected?' '+id+'-selected':'')} autoComplete="off" maxLength={200} placeholder={w.searchProduct} value={query} disabled={disabled} onClick={()=>setExpanded(true)} onKeyDown={keyboard} onChange={event=>{setQuery(event.target.value);setExpanded(true);setActive(-1);onSearch()}}/>
   <button type="button" data-hardware-toggle aria-label={w.showProducts} aria-expanded={open} aria-controls={id+'-list'} disabled={disabled} onClick={()=>{input.current?.focus();setExpanded(!open);setActive(-1)}}>▾</button></div>
  {open&&<div className="rc-hardware-popup"><p role="status">{w.productCount.replace('{n}',String(matches.length))}</p><ul id={id+'-list'} role="listbox" aria-label={w.profile} data-hardware-options>
   {matches.map((profile,index)=><li key={hardwareChoiceValue(profile)} id={id+'-option-'+index} role="option" aria-selected={index===active} data-hardware-choice={hardwareChoiceValue(profile)} onMouseDown={event=>event.preventDefault()} onClick={()=>choose(profile)}>
    <strong>{profileLabel(profile,w)}</strong><small>{profile.identity?.sku||profile.key} · {profile.revision}</small></li>)}
   {!matches.length&&<li role="presentation">{w.noProducts}</li>}
  </ul></div>}
  <small id={id+'-hint'}>{w.searchHint}</small>
  {selected&&<p id={id+'-selected'} role="status" data-hardware-selected={hardwareChoiceValue(selected)}><strong>{profileLabel(selected,w)}</strong> · {selected.identity?.sku||selected.key}</p>}
  <small>{w.customTemplateHint}</small>
 </div>;
}
