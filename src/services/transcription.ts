export interface TranscriptResult { text:string; language:string; }
export async function transcribeAudio(file:File):Promise<TranscriptResult>{
 return { text:'Transcription placeholder - Whisper integration coming next.', language:'auto' };
}