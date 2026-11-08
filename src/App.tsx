import { useState } from 'react';
import './styles.css';
import LanguageSelector from './components/LanguageSelector';

export default function App(){
 const [lang,setLang]=useState('en');
 const t=lang==='da'?{dashboard:'Kontrolpanel',record:'Optag lyd',open:'Åbn fil',language:'Sprog'}:{dashboard:'Dashboard',record:'Record Audio',open:'Open File',language:'Language'};
 return (<div className='app'><aside className='sidebar'><h1>Whisper-Free</h1></aside><main className='content'><h2>{t.dashboard}</h2><LanguageSelector value={lang} onChange={setLang}/><div className='actions'><button className='primary'>{t.record}</button><button>{t.open}</button></div></main></div>);
}