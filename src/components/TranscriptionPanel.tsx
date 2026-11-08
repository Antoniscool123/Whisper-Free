import { useState } from 'react';
import { transcribeAudio } from '../services/transcription';
export default function TranscriptionPanel(){
 const [text,setText]=useState('');
 async function openFile(e:any){
  const file=e.target.files?.[0];
  if(!file) return;
  const result=await transcribeAudio(file);
  setText(result.text);
 }
 return <div className='card'><h3>Transcription</h3><input type='file' accept='audio/*'/><input type='file' accept='audio/*' onChange={openFile}/><textarea value={text} readOnly rows={8} /></div>;
}