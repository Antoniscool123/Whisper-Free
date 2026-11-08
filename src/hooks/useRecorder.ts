import { useRef, useState } from 'react';
export function useRecorder(){
 const [recording,setRecording]=useState(false);
 const [audioUrl,setAudioUrl]=useState<string|null>(null);
 const mediaRecorder=useRef<MediaRecorder|null>(null);
 const chunks=useRef<Blob[]>([]);
 async function start(){
  const stream=await navigator.mediaDevices.getUserMedia({audio:true});
  const recorder=new MediaRecorder(stream);
  chunks.current=[];
  recorder.ondataavailable=(e)=>chunks.current.push(e.data);
  recorder.onstop=()=>{
   const blob=new Blob(chunks.current,{type:'audio/webm'});
   setAudioUrl(URL.createObjectURL(blob));
  };
  recorder.start();
  mediaRecorder.current=recorder;
  setRecording(true);
 }
 function stop(){
  mediaRecorder.current?.stop();
  setRecording(false);
 }
 return {recording,audioUrl,start,stop};
}