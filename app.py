from __future__ import annotations
import json, queue, re, tempfile, threading, time, wave
from datetime import datetime
from pathlib import Path
import customtkinter as ctk
import keyboard, numpy as np, pyperclip, sounddevice as sd
from faster_whisper import WhisperModel

APP='WhisperFree'; SR=16000; CH=1
DIR=Path.home()/'.whisper_free'; SETTINGS=DIR/'settings.json'; HISTORY=DIR/'history.json'
LANGS={'Auto detect':None,'Dansk':'da','English':'en','Deutsch':'de','Español':'es','Français':'fr','Italiano':'it','Nederlands':'nl','Norsk':'no','Svenska':'sv','Suomi':'fi','Polski':'pl','Português':'pt','Čeština':'cs','Українська':'uk','Русский':'ru','Türkçe':'tr','العربية':'ar','हिन्दी':'hi','日本語':'ja','한국어':'ko','中文':'zh'}
DEFAULT={'model':'small','language':'Dansk','hotkey':'ctrl+shift+space','remove_fillers':True,'auto_paste':True,'auto_punctuation':True,'format_lists':True,'auto_capitalize':True,'dictionary':True}
BG='#090d18'; CARD='#171d2e'; CARD2='#1d2438'; BORDER='#29314a'; TEXT='#f4f5ff'; MUTED='#a8b0cc'; PURPLE='#7774ff'; PURPLE2='#a79cff'; RED='#ef334f'; GREEN='#39d98a'

def read_json(path, default):
    try: return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    except Exception: return default

def write_json(path,data):
    DIR.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def polish(text, settings):
    text=re.sub(r'\s+([,.;:!?])',r'\1',text.strip()); text=re.sub(r'\s{2,}',' ',text)
    if settings['remove_fillers']:
        text=re.sub(r'\b(um+|uh+|erm+|øh+|øhm+|altså|you know)\b[,.]?\s*','',text,flags=re.I)
        text=re.sub(r'\b(\w+)(\s+\1\b)+',r'\1',text,flags=re.I)
    if settings['format_lists']:
        text=re.sub(r'\b(?:new line|ny linje)\b','\n',text,flags=re.I)
        text=re.sub(r'\b(?:new paragraph|nyt afsnit)\b','\n\n',text,flags=re.I)
    if settings['auto_capitalize'] and text: text=text[0].upper()+text[1:]
    return text.strip()

class Pill(ctk.CTkFrame):
    def __init__(self,master,**kw): super().__init__(master,corner_radius=14,fg_color=CARD,border_width=1,border_color=BORDER,**kw)

class App(ctk.CTk):
    def __init__(self):
        super().__init__(); DIR.mkdir(parents=True,exist_ok=True)
        self.settings={**DEFAULT,**read_json(SETTINGS,{})}; self.history=read_json(HISTORY,[])
        self.recording=False; self.frames=[]; self.q=queue.Queue(); self.stream=None; self.model=None; self.model_name=''; self.hotkey_handle=None
        self.title(APP); self.geometry('1480x920'); self.minsize(1120,720); self.configure(fg_color=BG)
        ctk.set_appearance_mode('dark'); self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        self.build_sidebar(); self.build_center(); self.build_inspector(); self.register_hotkey(); self.protocol('WM_DELETE_WINDOW',self.close)

    def label(self,master,text,size=14,color=TEXT,bold=False,**kw):
        return ctk.CTkLabel(master,text=text,font=ctk.CTkFont('Segoe UI',size,weight='bold' if bold else 'normal'),text_color=color,**kw)

    def build_sidebar(self):
        s=ctk.CTkFrame(self,width=235,corner_radius=0,fg_color='#0d1220'); s.grid(row=0,column=0,sticky='nsew'); s.grid_propagate(False)
        head=ctk.CTkFrame(s,fg_color='transparent'); head.pack(fill='x',padx=24,pady=(24,20))
        self.label(head,'▥',31,PURPLE2,True).pack(side='left',padx=(0,10)); box=ctk.CTkFrame(head,fg_color='transparent'); box.pack(side='left')
        self.label(box,'WhisperFree',22,TEXT,True,anchor='w').pack(anchor='w'); self.label(box,'Speak. Write. Anywhere.',11,MUTED,anchor='w').pack(anchor='w')
        self.nav={}
        for icon,name in [('⌂','Home'),('🎙','Dictation'),('≋','Snippets'),('▣','Dictionary'),('☷','Styles'),('◴','History'),('⌁','Statistics'),('⚙','Settings')]:
            b=ctk.CTkButton(s,text=f'  {icon}    {name}',anchor='w',height=50,corner_radius=12,fg_color='#202742' if name=='Home' else 'transparent',hover_color='#202742',text_color=TEXT,font=ctk.CTkFont('Segoe UI',15),command=lambda n=name:self.nav_click(n)); b.pack(fill='x',padx=16,pady=3); self.nav[name]=b
        bottom=Pill(s); bottom.pack(side='bottom',fill='x',padx=16,pady=18)
        self.side_status=self.label(bottom,'●  Ready',13,GREEN); self.side_status.pack(anchor='w',padx=14,pady=(13,5))
        self.side_model=self.label(bottom,f"Model: {self.settings['model']}",11,MUTED); self.side_model.pack(anchor='w',padx=14)
        self.side_lang=self.label(bottom,f"Language: {self.settings['language']}",11,MUTED); self.side_lang.pack(anchor='w',padx=14,pady=(0,10))
        ctk.CTkButton(bottom,text='⇩  Download Models',height=42,corner_radius=10,fg_color='#20263a',hover_color='#2b3350',command=lambda:threading.Thread(target=self.load_model,daemon=True).start()).pack(fill='x',padx=9,pady=(0,9))

    def build_center(self):
        self.center=ctk.CTkScrollableFrame(self,fg_color=BG,corner_radius=0,scrollbar_button_color='#303855'); self.center.grid(row=0,column=1,sticky='nsew',padx=16,pady=16); self.center.grid_columnconfigure(0,weight=1)
        hero=ctk.CTkFrame(self.center,height=205,corner_radius=18,fg_color='#11172a',border_width=1,border_color=BORDER); hero.grid(row=0,column=0,sticky='ew'); hero.grid_propagate(False)
        self.label(hero,'Turn your thoughts into clear, polished text.',26,TEXT,True).place(x=28,y=28)
        self.label(hero,'Dictate in any app, refine locally, and write at the speed of thought.',15,MUTED).place(x=28,y=70)
        for i,(ic,t,sub) in enumerate([('ϟ','Works anywhere','In any app or website'),('◎','Many languages','Including Danish'),('▣','100% private','Runs locally on your device')]):
            x=28+i*225; self.label(hero,ic,25,PURPLE2,True).place(x=x,y=119); self.label(hero,t,14,TEXT,True).place(x=x+43,y=117); self.label(hero,sub,11,MUTED).place(x=x+43,y=143)
        self.label(hero,'Speak freely.\nWrite better.',20,'#ddd9ff',justify='left').place(relx=.82,y=108)
        actions=ctk.CTkFrame(self.center,fg_color='transparent'); actions.grid(row=1,column=0,sticky='ew',pady=16); [actions.grid_columnconfigure(i,weight=1) for i in range(4)]
        data=[('🎙','Start dictating','Press Ctrl + Shift + Space',self.toggle),('▤','New note','Dictate in the app',lambda:self.nav_click('Dictation')),('✦','Clean text','Remove fillers locally',self.clean_current),('文','Copy text','Ready for any app',self.copy_current)]
        for i,(ic,t,sub,cmd) in enumerate(data):
            c=ctk.CTkButton(actions,text=f'{ic}\n\n{t}\n{sub}',height=145,corner_radius=16,fg_color='#a99cff' if i==0 else CARD2,hover_color='#bbb0ff' if i==0 else '#28314a',text_color='#11152a' if i==0 else TEXT,font=ctk.CTkFont('Segoe UI',14,weight='bold'),command=cmd); c.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 6,0 if i==3 else 6))
        recent=Pill(self.center); recent.grid(row=2,column=0,sticky='nsew'); recent.grid_columnconfigure(0,weight=1)
        hdr=ctk.CTkFrame(recent,fg_color='transparent'); hdr.grid(row=0,column=0,sticky='ew',padx=18,pady=(16,8)); self.label(hdr,'Recent dictations',16,TEXT,True).pack(side='left'); self.label(hdr,'View all  →',12,PURPLE2).pack(side='right')
        self.recent_frame=ctk.CTkFrame(recent,fg_color='transparent'); self.recent_frame.grid(row=1,column=0,sticky='nsew',padx=12,pady=(0,72)); self.render_history()
        self.overlay=ctk.CTkFrame(recent,height=82,corner_radius=40,fg_color='#171d31',border_width=1,border_color='#4d4c78'); self.overlay.place(relx=.5,rely=1,anchor='s',y=-10,relwidth=.72)
        self.stop_btn=ctk.CTkButton(self.overlay,text='●',width=52,height=52,corner_radius=26,fg_color=RED,hover_color='#ff4e68',font=ctk.CTkFont(size=22),command=self.toggle); self.stop_btn.pack(side='left',padx=16,pady=14)
        st=ctk.CTkFrame(self.overlay,fg_color='transparent'); st.pack(side='left'); self.overlay_status=self.label(st,'Ready to dictate',14,TEXT,True); self.overlay_status.pack(anchor='w'); self.overlay_lang=self.label(st,self.settings['language'],11,MUTED); self.overlay_lang.pack(anchor='w')
        self.wave=self.label(self.overlay,'▂▃▄▅▆▅▄▃▂  ▂▄▆█▆▄▂',20,PURPLE2,True); self.wave.pack(side='left',expand=True)
        self.label(self.overlay,'Press Esc to stop',11,MUTED).pack(side='left',padx=16); ctk.CTkButton(self.overlay,text='⚙',width=44,height=44,corner_radius=22,fg_color='#20263a',command=lambda:self.nav_click('Settings')).pack(side='right',padx=15)

    def build_inspector(self):
        r=ctk.CTkFrame(self,width=280,corner_radius=0,fg_color='#0d1220'); r.grid(row=0,column=2,sticky='nsew'); r.grid_propagate(False)
        self.label(r,'Language',13,MUTED).pack(anchor='w',padx=20,pady=(75,6)); self.lang=ctk.CTkOptionMenu(r,values=list(LANGS),height=46,corner_radius=10,fg_color=CARD2,button_color=CARD2,command=lambda _:self.save()); self.lang.set(self.settings['language']); self.lang.pack(fill='x',padx=20)
        self.label(r,'Model',13,MUTED).pack(anchor='w',padx=20,pady=(20,6)); self.model_menu=ctk.CTkOptionMenu(r,values=['tiny','base','small','medium','large-v3'],height=46,corner_radius=10,fg_color=CARD2,button_color=CARD2,command=lambda _:self.save()); self.model_menu.set(self.settings['model']); self.model_menu.pack(fill='x',padx=20)
        self.switches={}
        for key,title in [('auto_punctuation','Auto punctuation'),('remove_fillers','Remove filler words'),('format_lists','Format lists'),('auto_capitalize','Auto capitalize'),('dictionary','Use personal dictionary')]:
            sw=ctk.CTkSwitch(r,text=title,progress_color=PURPLE,button_color='#f1f2ff',command=self.save); sw.pack(fill='x',padx=20,pady=10); sw.select() if self.settings.get(key,True) else sw.deselect(); self.switches[key]=sw
        quick=Pill(r); quick.pack(fill='x',padx=16,pady=20); self.label(quick,'Quick actions',15,TEXT,True).pack(anchor='w',padx=15,pady=(14,8))
        for icon,name in [('▣','Add to dictionary'),('ϟ','Manage snippets'),('◉','Change style'),('▥','View statistics')]: ctk.CTkButton(quick,text=f'{icon}    {name}',anchor='w',fg_color='transparent',hover_color='#252d45',height=40,command=lambda n=name:self.nav_click(n)).pack(fill='x',padx=7,pady=2)
        quote=Pill(r); quote.pack(side='bottom',fill='x',padx=16,pady=18); self.label(quote,'“A faster, quieter,\n smarter way to write.”',17,'#cbc5ff').pack(anchor='w',padx=16,pady=(20,15)); self.label(quote,'♥  Open source. Always free.',12,MUTED).pack(anchor='w',padx=16,pady=(0,18))

    def render_history(self):
        for w in self.recent_frame.winfo_children(): w.destroy()
        rows=self.history[-4:][::-1] or [{'text':'Your recent dictations will appear here.','language':'—','time':'Ready','words':0}]
        for item in rows:
            row=ctk.CTkFrame(self.recent_frame,height=68,corner_radius=13,fg_color=CARD2); row.pack(fill='x',pady=5); row.pack_propagate(False)
            self.label(row,'▤',20,'#d9dcff').pack(side='left',padx=16); body=ctk.CTkFrame(row,fg_color='transparent'); body.pack(side='left',fill='both',expand=True,pady=10)
            text=item.get('text',''); self.label(body,text[:75]+('…' if len(text)>75 else ''),13,TEXT,anchor='w').pack(fill='x'); self.label(body,f"{item.get('time','')}  •  {item.get('language','')}",11,MUTED,anchor='w').pack(fill='x')
            self.label(row,f"{item.get('words',len(text.split()))} words    ⋮",11,MUTED).pack(side='right',padx=16)

    def nav_click(self,name):
        for n,b in self.nav.items(): b.configure(fg_color='#202742' if n==name else 'transparent')
        if name!='Home': self.overlay_status.configure(text=f'{name} selected'); self.after(1200,lambda:self.overlay_status.configure(text='Ready to dictate'))
    def clean_current(self):
        if self.history: self.history[-1]['text']=polish(self.history[-1]['text'],self.settings); write_json(HISTORY,self.history); self.render_history()
    def copy_current(self):
        if self.history: pyperclip.copy(self.history[-1]['text']); self.overlay_status.configure(text='Copied to clipboard')
    def save(self):
        self.settings['language']=self.lang.get(); self.settings['model']=self.model_menu.get()
        for k,s in self.switches.items(): self.settings[k]=bool(s.get())
        write_json(SETTINGS,self.settings); self.side_model.configure(text=f"Model: {self.settings['model']}"); self.side_lang.configure(text=f"Language: {self.settings['language']}"); self.overlay_lang.configure(text=self.settings['language'])
    def register_hotkey(self):
        try:
            self.hotkey_handle=keyboard.add_hotkey(self.settings['hotkey'],lambda:self.after(0,self.toggle)); keyboard.add_hotkey('esc',lambda:self.after(0,self.stop) if self.recording else None)
        except Exception: self.side_status.configure(text='●  Hotkey error',text_color=RED)
    def audio_cb(self,indata,frames,t,status):
        if self.recording: self.q.put(indata.copy())
    def toggle(self): self.stop() if self.recording else self.start()
    def start(self):
        try:
            self.frames=[]
            while not self.q.empty(): self.q.get_nowait()
            self.stream=sd.InputStream(samplerate=SR,channels=CH,dtype='float32',callback=self.audio_cb); self.stream.start(); self.recording=True
            self.overlay_status.configure(text='Listening…'); self.side_status.configure(text='●  Listening',text_color=RED); self.stop_btn.configure(text='■'); self.animate()
        except Exception as e: self.overlay_status.configure(text=f'Microphone error: {e}')
    def animate(self):
        if not self.recording:return
        patterns=['▂▃▅▇▅▃▂  ▂▄▆▄▂','▂▄▆█▆▄▂  ▃▅▇▅▃','▃▅▇▅▃  ▂▃▄▃▂']; self.wave.configure(text=patterns[int(time.time()*4)%3]); self.after(180,self.animate)
    def stop(self):
        if not self.recording:return
        self.recording=False
        if self.stream:self.stream.stop(); self.stream.close(); self.stream=None
        while not self.q.empty(): self.frames.append(self.q.get())
        self.overlay_status.configure(text='Transcribing…'); self.side_status.configure(text='●  Processing',text_color=PURPLE2); self.stop_btn.configure(text='●'); threading.Thread(target=self.transcribe,daemon=True).start()
    def load_model(self):
        name=self.settings['model']; self.after(0,lambda:self.overlay_status.configure(text=f'Loading {name} model…'))
        if self.model is None or self.model_name!=name:self.model=WhisperModel(name,device='cpu',compute_type='int8'); self.model_name=name
        self.after(0,lambda:self.overlay_status.configure(text=f'{name} model ready')); return self.model
    def transcribe(self):
        path=None
        try:
            if not self.frames: raise RuntimeError('No audio captured')
            audio=np.concatenate(self.frames,axis=0); pcm=np.clip(audio*32767,-32768,32767).astype(np.int16)
            with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as tmp:path=tmp.name
            with wave.open(path,'wb') as f:f.setnchannels(CH);f.setsampwidth(2);f.setframerate(SR);f.writeframes(pcm.tobytes())
            segs,info=self.load_model().transcribe(path,language=LANGS[self.settings['language']],vad_filter=True,beam_size=5)
            text=polish(' '.join(s.text.strip() for s in segs),self.settings); self.after(0,lambda:self.finish(text,info.language))
        except Exception as e:self.after(0,lambda:self.fail(str(e)))
        finally:
            if path:Path(path).unlink(missing_ok=True)
    def finish(self,text,language):
        if not text:return self.fail('No speech detected')
        pyperclip.copy(text)
        if self.settings['auto_paste']:
            try: keyboard.write(text,delay=.001)
            except Exception: pass
        now=datetime.now(); self.history.append({'text':text,'language':language,'time':now.strftime('%H:%M'),'words':len(text.split()),'date':now.isoformat()}); self.history=self.history[-100:]; write_json(HISTORY,self.history); self.render_history()
        self.overlay_status.configure(text='Inserted and copied'); self.side_status.configure(text='●  Ready',text_color=GREEN); self.wave.configure(text='▂▂▂▂▂  ▂▂▂▂')
    def fail(self,msg): self.overlay_status.configure(text=msg); self.side_status.configure(text='●  Ready',text_color=GREEN)
    def close(self):
        try:
            if self.hotkey_handle: keyboard.remove_hotkey(self.hotkey_handle)
            if self.stream:self.stream.close()
        finally:self.destroy()

if __name__=='__main__': App().mainloop()
