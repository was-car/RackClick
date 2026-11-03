// Secondary model notes remain available without pushing the rack face down.
export function HardwareFaceCaption({words,children}) {
 const summary=words?.front==='Frontal'?'Detalles de esta cara':words?.front==='Vorderseite'?'Details dieser Seite':'Face details';
 return <details className="rc-face-details"><summary>{summary}</summary><p className="rc-mount-caption" data-shell-caption>{children}</p></details>;
}
