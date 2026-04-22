import socket
import ipaddress
import threading
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import get_color_from_hex as C

BG=C("#0d1117");PANEL=C("#161b22");ORANGE=C("#f6821f")
GREEN=C("#3fb950");YELLOW=C("#e3b341");RED=C("#f85149")
GRAY=C("#8b949e");WHITE=C("#e6edf3");BORDER=C("#30363d")
Window.clearcolor=BG

CF_RANGES=["173.245.48.0/20","103.21.244.0/22","103.22.200.0/22",
"103.31.4.0/22","141.101.64.0/18","108.162.192.0/18",
"190.93.240.0/20","188.114.96.0/20","197.234.240.0/22",
"198.41.128.0/17","162.158.0.0/15","104.16.0.0/13",
"104.24.0.0/14","172.64.0.0/13","131.0.72.0/22"]
CF_NETS=[ipaddress.ip_network(r) for r in CF_RANGES]

def is_cf(ip):
    try:
        a=ipaddress.ip_address(ip)
        return any(a in n for n in CF_NETS)
    except:return False

def valid(host):
    try:
        if not host or len(host)>253:return False
        for lb in host.encode("ascii").split(b"."):
            if not(0<len(lb)<=63):return False
        return True
    except:return False

def check(host):
    host=host.strip()
    if not host or host.startswith("#"):return host,"skip",""
    if not valid(host):return host,"skip","bad"
    try:ip=socket.gethostbyname(host)
    except:return host,"not_cf","DNS"
    if not is_cf(ip):return host,"not_cf",ip
    for scheme in("https","http"):
        try:
            r=urllib.request.urlopen(
                urllib.request.Request(f"{scheme}://{host}",
                headers={"User-Agent":"Mozilla/5.0","Host":host}),timeout=5)
            sv=r.headers.get("Server","")
            return host,"live",f"{ip}|{r.status}|{sv}"
        except urllib.error.HTTPError as e:
            sv=e.headers.get("Server","") if hasattr(e,"headers") else ""
            if "cloudflare" in sv.lower():return host,"live",f"{ip}|{e.code}|{sv}"
            return host,"cf_dead",f"{ip}|{e.code}"
        except:continue
    return host,"cf_dead",f"{ip}|no resp"

class FilePicker(Popup):
    def __init__(self,cb,**kw):
        super().__init__(**kw)
        self.cb=cb;self.title="Pick .txt file"
        self.title_color=ORANGE;self.background_color=PANEL
        self.size_hint=(0.95,0.85)
        lay=BoxLayout(orientation="vertical",spacing=dp(6),padding=dp(6))
        self.fc=FileChooserListView(path=str(Path.home()),filters=["*.txt"],size_hint=(1,0.85))
        lay.add_widget(self.fc)
        row=BoxLayout(size_hint=(1,None),height=dp(46),spacing=dp(6))
        b1=Button(text="SELECT",background_color=ORANGE,color=BG,bold=True,size_hint=(.5,1))
        b1.bind(on_press=self._sel)
        b2=Button(text="CANCEL",background_color=PANEL,color=RED,size_hint=(.5,1))
        b2.bind(on_press=self.dismiss)
        row.add_widget(b1);row.add_widget(b2)
        lay.add_widget(row);self.content=lay
    def _sel(self,*a):
        if self.fc.selection:self.cb(self.fc.selection[0]);self.dismiss()

class LogView(ScrollView):
    def __init__(self,**kw):
        super().__init__(**kw)
        self.lay=GridLayout(cols=1,size_hint_y=None,spacing=dp(1),padding=[dp(4),dp(2)])
        self.lay.bind(minimum_height=self.lay.setter("height"))
        self.add_widget(self.lay)
    def add(self,txt,col=None):
        l=Label(text=txt,color=col or WHITE,size_hint_y=None,
            text_size=(Window.width-dp(20),None),halign="left",valign="top",font_size=dp(11))
        l.bind(texture_size=lambda i,v:setattr(i,"height",v[1]))
        self.lay.add_widget(l)
        Clock.schedule_once(lambda dt:setattr(self,"scroll_y",0),.05)
    def clear(self):self.lay.clear_widgets()

class Root(BoxLayout):
    def __init__(self,**kw):
        super().__init__(orientation="vertical",spacing=dp(5),padding=dp(7),**kw)
        self._run=False;self._t=self._l=self._d=self._s=0
        self._build()
    def _build(self):
        self.add_widget(Label(
            text="[b][color=f6821f]CF Scanner[/color][/b] Cloudflare Live Filter",
            markup=True,size_hint=(1,None),height=dp(34),font_size=dp(14),color=WHITE))
        r1=BoxLayout(size_hint=(1,None),height=dp(42),spacing=dp(5))
        self.f_in=TextInput(hint_text="Tap folder to pick .txt",multiline=False,
            background_color=PANEL,foreground_color=WHITE,hint_text_color=GRAY,
            cursor_color=ORANGE,size_hint=(.8,1),font_size=dp(11))
        bp=Button(text="📂",size_hint=(.2,1),background_color=BORDER,color=ORANGE,font_size=dp(17))
        bp.bind(on_press=lambda x:FilePicker(cb=self._picked).open())
        r1.add_widget(self.f_in);r1.add_widget(bp);self.add_widget(r1)
        r2=BoxLayout(size_hint=(1,None),height=dp(42),spacing=dp(5))
        r2.add_widget(Label(text="[color=f6821f]Out:[/color]",markup=True,size_hint=(.15,1),font_size=dp(12)))
        self.f_out=TextInput(text="cf_live.txt",multiline=False,
            background_color=PANEL,foreground_color=WHITE,cursor_color=ORANGE,
            size_hint=(.85,1),font_size=dp(11))
        r2.add_widget(self.f_out);self.add_widget(r2)
        r3=BoxLayout(size_hint=(1,None),height=dp(42),spacing=dp(5))
        r3.add_widget(Label(text="[color=8b949e]Thr:[/color]",markup=True,size_hint=(.18,1),font_size=dp(11)))
        self.sp=Spinner(text="100",values=["20","50","100","150","200"],
            size_hint=(.22,1),background_color=PANEL,color=WHITE,font_size=dp(12))
        self.b_go=Button(text="START",size_hint=(.35,1),
            background_color=ORANGE,color=BG,bold=True,font_size=dp(12))
        self.b_go.bind(on_press=self.go)
        bc=Button(text="CLR",size_hint=(.25,1),background_color=PANEL,color=GRAY,font_size=dp(12))
        bc.bind(on_press=lambda x:self.log.clear())
        r3.add_widget(self.sp);r3.add_widget(self.b_go);r3.add_widget(bc)
        self.add_widget(r3)
        self.pb=ProgressBar(max=100,value=0,size_hint=(1,None),height=dp(14))
        self.add_widget(self.pb)
        sg=GridLayout(cols=4,size_hint=(1,None),height=dp(28),spacing=dp(2))
        self.lt=Label(text="Total:0",color=GRAY,font_size=dp(10))
        self.ll=Label(text="Live:0",color=GREEN,font_size=dp(10))
        self.ld=Label(text="CF:0",color=YELLOW,font_size=dp(10))
        self.ls=Label(text="Skip:0",color=RED,font_size=dp(10))
        for w in[self.lt,self.ll,self.ld,self.ls]:sg.add_widget(w)
        self.add_widget(sg)
        self.log=LogView(size_hint=(1,1));self.add_widget(self.log)
    def _picked(self,p):
        self.f_in.text=p
        try:
            n=sum(1 for _ in open(p,encoding="utf-8",errors="ignore"))
            self.log.add(f"📄 {Path(p).name} — {n} lines",ORANGE)
        except:self.log.add(f"📄 {p}",ORANGE)
    def _upd(self,dt=None):
        self.lt.text=f"Total:{self._t}";self.ll.text=f"Live:{self._l}"
        self.ld.text=f"CF:{self._d}";self.ls.text=f"Skip:{self._s}"
    def go(self,*a):
        if self._run:return
        inf=self.f_in.text.strip();outf=self.f_out.text.strip()
        thr=int(self.sp.text)
        if not inf:self.log.add("Pick a file!",RED);return
        if not Path(inf).exists():self.log.add(f"Not found:{inf}",RED);return
        self._run=True;self._t=self._l=self._d=self._s=0
        self.b_go.disabled=True;self.b_go.background_color=BORDER;self.pb.value=0
        threading.Thread(target=self._scan,args=(inf,outf,thr),daemon=True).start()
    def _scan(self,inf,outf,thr):
        Clock.schedule_once(lambda dt:self.log.add(f"Scanning {Path(inf).name}...",ORANGE))
        hosts=[]
        with open(inf,encoding="utf-8",errors="ignore") as f:
            for ln in f:
                h=ln.strip()
                if h and not h.startswith("#"):hosts.append(h)
        self._t=len(hosts)
        Clock.schedule_once(lambda dt:self.log.add(f"{self._t} hosts · {thr} threads",GRAY))
        Clock.schedule_once(lambda dt:setattr(self.pb,"max",max(self._t,1)))
        Clock.schedule_once(self._upd)
        live=[];dead=[];done=0
        with ThreadPoolExecutor(max_workers=thr) as ex:
            futs={ex.submit(check,h):h for h in hosts}
            for fu in as_completed(futs):
                try:host,st,info=fu.result()
                except:
                    self._s+=1;done+=1
                    Clock.schedule_once(lambda dt,d=done:setattr(self.pb,"value",d));continue
                done+=1
                if st=="live":
                    self._l+=1;live.append(host)
                    m=f"🟢 {host} {info}"
                    Clock.schedule_once(lambda dt,x=m:self.log.add(x,GREEN))
                elif st=="cf_dead":
                    self._d+=1;dead.append(host)
                    m=f"🟡 {host} {info}"
                    Clock.schedule_once(lambda dt,x=m:self.log.add(x,YELLOW))
                elif st=="skip":self._s+=1
                Clock.schedule_once(lambda dt,d=done:setattr(self.pb,"value",d))
                Clock.schedule_once(self._upd)
        od=Path(inf).parent
        if live:
            lp=od/outf
            open(lp,"w").write("\n".join(live))
            Clock.schedule_once(lambda dt,x=str(lp):self.log.add(f"LIVE {len(live)} saved→{x}",GREEN))
        if dead:
            dp2=od/("cf_"+outf)
            open(dp2,"w").write("\n".join(dead))
            Clock.schedule_once(lambda dt,x=str(dp2):self.log.add(f"CF dead {len(dead)}→{x}",YELLOW))
        if not live and not dead:
            Clock.schedule_once(lambda dt:self.log.add("No CF hosts found.",RED))
        self._run=False
        Clock.schedule_once(lambda dt:(
            setattr(self.b_go,"disabled",False),
            setattr(self.b_go,"background_color",ORANGE)))

class CFApp(App):
    def build(self):
        self.title="CF Scanner";return Root()

CFApp().run()