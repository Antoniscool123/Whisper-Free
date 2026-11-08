import { useRecorder } from '../hooks/useRecorder';
export default function RecorderPanel(){
 const {recording,audioUrl,start,stop}=useRecorder();
 return <div className='card'><h3>Recorder</h3><button onClick={recording?stop:start}>{recording?'Stop Recording':'Start Recording'}</button>{audioUrl && <audio controls src={audioUrl}></audio>}</div>;
}