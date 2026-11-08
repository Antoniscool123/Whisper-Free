import { useState } from 'react';
import './styles.css';
import LanguageSelector from './components/LanguageSelector';
import RecorderPanel from './components/RecorderPanel';
import TranscriptionPanel from './components/TranscriptionPanel';
export default function App(){const [lang,setLang]=useState('en'); return <div className='app'><aside className='sidebar'><h1>Whisper-Free</h1></aside><main className='content'><h2>{lang==='da'?'Kontrolpanel':'Dashboard'}</h2><LanguageSelector value={lang} onChange={setLang}/><RecorderPanel/><TranscriptionPanel/></main></div>}