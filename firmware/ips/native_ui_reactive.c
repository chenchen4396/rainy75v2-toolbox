/* SPDX-License-Identifier: MIT
 * Interactive pixel IPS UI for rainy75-px/2 schemes: the uploaded background holds the
 * calm artwork, the firmware decodes the PackBits mask set once, then overlays the mood
 * frame (calm/caps/react/sleepy), typing particles, a breathing pulse layer and the
 * status cluster. The player is advanced every tick so the overlay can animate.
 */
#include "native_ui.h"
#include "px_assets.h"
#include "px_font.h"
#define R(a) (*(volatile u32*)(a))
#define LCD_BUSY R(0x20001c6c)
#define SCR_W 320u
#define SCR_H 172u
#if defined(PX_MOTION_COUNT) && PX_MOTION_COUNT > 0
#define FX_MOTION 1
#endif
#if defined(PX_KEYPANEL) && PX_KEYPANEL > 0
#define FX_PANEL 1
#endif
#if defined(PX_TOPBAR) && PX_TOPBAR > 0
#define FX_TOPBAR 1
#endif
#if FX_COUNT || FX_TRIGGER_CONT
#define FX_PARTS 1
#endif
extern u8 __live_bss_start__,__live_bss_end__;

typedef short i16;
typedef int i32;
#if FX_PARTS
typedef struct {i16 x,y,vx,vy;u16 life,color;} Particle;
#endif

static u8 masks[PX_MASK_RAM_BYTES];
#if FX_PANEL
static u8 panel_mask[((unsigned)PX_KEY_W*(unsigned)PX_KEY_H+7u)/8u];
#endif
#if !FX_TOPBAR
/* Static outline of the 20x8 battery gauge; the charge bar is ORed in per draw. */
static const unsigned char batt[20]={255,255,136,0,8,128,0,200,0,12,128,0,200,0,12,128,0,143,255,248};
#endif

static struct {
 u32 rng;
 u32 pointer,object,caps_at,last_tick,last_key_ms,last_cont,energy_start;
 u16 x,y,w,h,key;
#if FX_PANEL
 u16 panel_key;
#endif
#if FX_PARTS
 Particle parts[FX_MAX_ALIVE];
#endif
 u8 active,suspended,has_surface,dirty,known,battery,charge,mode,modifiers,caps,caps_inv,count,frm,hits,keys;
} ui;

static u32 clock_ms(void){return ((u32(*)(void))0x0803a2bb)();}

static void load_masks(void){
 const u8 *s=px_mask_rle;unsigned n=(unsigned)sizeof(px_mask_rle),i=0,k;u8 *d=masks;
 while(i<n){u8 c=s[i++];
  if(c&0x80u){k=(c&0x7fu)+1u;do{*d++=s[i++];}while(--k);}
  else{k=(unsigned)c+1u;{u8 v=s[i++];do{*d++=v;}while(--k);}}
 }
}

#if FX_PARTS
static u32 rnd(void){ui.rng=ui.rng*1664525u+1013904223u;return ui.rng>>8;}
static int irange(int a,int b){int d=b-a;return a+(int)(rnd()%(u32)(d>0?d:1));}
static void spawn(unsigned n){
 unsigned k,i;
 for(k=0;k<n;k++){
  Particle *q=0;
  for(i=0;i<FX_MAX_ALIVE;i++)if(!ui.parts[i].life){q=&ui.parts[i];break;}
  if(!q)return;
  q->x=(i16)irange(FX_SPAWN_X,FX_SPAWN_X+(int)FX_SPAWN_W);
  q->y=(i16)irange(FX_SPAWN_Y,FX_SPAWN_Y+(int)FX_SPAWN_H);
  q->vx=(i16)irange(FX_VX_MIN,FX_VX_MAX);
  q->vy=(i16)irange(FX_VY_MIN,FX_VY_MAX);
  q->life=(u16)FX_LIFE_MS;
  q->color=fx_colors[k%FX_COLORS];
 }
}
#endif

#if FX_PARTS
static int advance_parts(u32 dt){
 int any=0;unsigned i;
 for(i=0;i<FX_MAX_ALIVE;i++){
  Particle *q=&ui.parts[i];
  if(!q->life)continue;
  any=1;
  if((u32)q->life<=dt){q->life=0;continue;}
  q->life=(u16)((u32)q->life-dt);
  q->x=(i16)(q->x+(i32)q->vx*(i32)dt/1000);
  q->y=(i16)(q->y+(i32)q->vy*(i32)dt/1000);
  q->vy=(i16)(q->vy+(i32)FX_GRAVITY*(i32)dt/1000);
#if FX_EDGE==1
  if(q->x<0)q->x=(i16)(q->x+(i16)SCR_W);else if(q->x>=(i16)SCR_W)q->x=(i16)(q->x-(i16)SCR_W);
  if(q->y<0)q->y=(i16)(q->y+(i16)SCR_H);else if(q->y>=(i16)SCR_H)q->y=(i16)(q->y-(i16)SCR_H);
#else
  if((unsigned)q->x>=SCR_W||(unsigned)q->y>=SCR_H)q->life=0;
#endif
 }
 return any;
}
#endif

#if PX_PULSE_LAYER >= 0
static u16 pulse_color(u16 c,u32 now){
 u32 p=now%(u32)PX_PULSE_PERIOD_MS;
 if(p*2u>(u32)PX_PULSE_PERIOD_MS)p=(u32)PX_PULSE_PERIOD_MS-p;
 p=((u32)PX_PULSE_MIN+(255u-(u32)PX_PULSE_MIN)*p*2u/(u32)PX_PULSE_PERIOD_MS);
 return (u16)((((c>>11)&31u)*p/255u)<<11|(((c>>5)&63u)*p/255u)<<5|((c&31u)*p/255u));
}
#endif

static void ack(unsigned status,u16 seq){
 u8 p[8]={0xbe,0x1a,8,13,(u8)status,(u8)seq,(u8)(seq>>8),0xed};unsigned i,spins;
 for(i=0;i<8;i++){for(spins=0;spins<4096;spins++)if(R(0x40004c00)&0x40u)break;if(spins==4096)return;R(0x40004c04)=p[i];}
}
static u32 current_object(void){u32 o=R(0x2003ede8);return o>=0x20000000u&&o<=0x2005f000u-0x65cu?o:0;}
static int surface_matches(void){return ui.has_surface&&ui.object==current_object()&&R(ui.object+0x658)==ui.pointer&&*(volatile u16*)0x2003edba==ui.w&&*(volatile u16*)0x2003edbc==ui.h&&*(volatile u16*)0x2003edbe==ui.x&&*(volatile u16*)0x2003edc0==ui.y;}

#if FX_PARTS || FX_TOPBAR
static void put(u8 *p,unsigned w,unsigned h,unsigned ox,unsigned oy,unsigned x,unsigned y,u16 color){
 if(x<ox||y<oy||x>=ox+w||y>=oy+h)return;
 {unsigned at=((y-oy)*w+x-ox)*2;p[at]=(u8)color;p[at+1]=(u8)(color>>8);}
}
#endif
/* One bit-mask rectangle blit shared by the mood layers and the status cluster. */
static void blit(u8 *p,unsigned x,unsigned y,unsigned w,unsigned h,const u8 *m,unsigned off,unsigned rw,unsigned rh,unsigned rx,unsigned ry,u16 fg,u16 bg){
 unsigned x0,y0,x1,y1,px,py,bit,at,color;
 x0=x>rx?x:rx;y0=y>ry?y:ry;x1=x+w<rx+rw?x+w:rx+rw;y1=y+h<ry+rh?y+h:ry+rh;
 for(py=y0;py<y1;py++)for(px=x0;px<x1;px++){
  bit=(py-ry)*rw+px-rx;color=m[off+(bit>>3)]&(128u>>(bit&7))?fg:bg;
  at=((py-y)*w+px-x)*2;p[at]=(u8)color;p[at+1]=(u8)(color>>8);
 }
}
#if FX_PARTS
#if FX_SHAPE==1
static int part_hit(unsigned dx,unsigned dy){
 return dx==(unsigned)FX_SIZE/2u||dy==(unsigned)FX_SIZE/2u;
}
#endif
static void draw_parts(u8 *p,u16 ox,u16 oy,u16 w,u16 h){
 unsigned i,sx,sy;
 for(i=0;i<FX_MAX_ALIVE;i++){
  Particle *q=&ui.parts[i];if(!q->life)continue;
  for(sy=0;sy<(unsigned)FX_SIZE;sy++)for(sx=0;sx<(unsigned)FX_SIZE;sx++)
#if FX_SHAPE==1
   if(part_hit(sx,sy))put(p,w,h,ox,oy,(unsigned)(q->x+(i16)sx),(unsigned)(q->y+(i16)sy),q->color);
#else
   put(p,w,h,ox,oy,(unsigned)(q->x+(i16)sx),(unsigned)(q->y+(i16)sy),q->color);
#endif
 }
}
#endif

#if FX_PANEL
/* Key code -> label mapping and native key icons (profiles/keys.json). */
#include "reactive_keylabel.h"
#include "reactive_keyicons.h"
static const PxKeyIcon *key_icon(u16 k){unsigned i;for(i=0;i<PX_KEY_ICON_COUNT;i++)if(px_key_icons[i].key==k)return &px_key_icons[i];return 0;}

static void draw_panel(u8 *p,u16 x,u16 y,u16 w,u16 h){
 unsigned i,j,c,dx,dy,px,py,n,sc,width,height,ox,oy,bi,bytes;const char *s;char buf[4];
 bytes=((unsigned)PX_KEY_W*(unsigned)PX_KEY_H+7u)/8u;
 for(py=0;py<bytes;py++)panel_mask[py]=0;
 if(key_icon(ui.panel_key)){
  const PxKeyIcon *ic=key_icon(ui.panel_key);unsigned sc=0, ww, hh, stride=(ic->w+7u)/8u;
  unsigned sw=(unsigned)PX_KEY_W/ic->w, sh=(unsigned)PX_KEY_H/ic->h;
  sc=sw<sh?sw:sh;if(sc>6u)sc=6u;if(!sc)sc=1u;
  ww=ic->w*sc;hh=ic->h*sc;
  {unsigned ox=(unsigned)PX_KEY_W>ww?((unsigned)PX_KEY_W-ww)/2u:0u;
   unsigned oy=(unsigned)PX_KEY_H>hh?((unsigned)PX_KEY_H-hh)/2u:0u;
   unsigned ix,iy,sx,sy;
   for(iy=0;iy<ic->h;iy++)for(ix=0;ix<ic->w;ix++){
    if(!(px_key_icon_bits[ic->off+iy*stride+(ix>>3)]&(0x80u>>(ix&7))))continue;
    for(sy=0;sy<sc;sy++)for(sx=0;sx<sc;sx++){
     bi=(oy+iy*sc+sy)*(unsigned)PX_KEY_W+(ox+ix*sc+sx);
     panel_mask[bi>>3]|=(u8)(128u>>(bi&7));}}}
  blit((u8*)p,x,y,w,h,panel_mask,0,(unsigned)PX_KEY_W,(unsigned)PX_KEY_H,(unsigned)PX_KEY_X,(unsigned)PX_KEY_Y,PX_KEY_FG,PX_KEY_BG);
  return;}
 s=rk_key_label(ui.panel_key,buf);n=0;while(s[n])n++;
 sc=(unsigned)PX_KEY_SCALE;
 if(n>1u){sc=0u;for(j=1;j<=5;j++)if((n*6u-1u)*j<=PX_KEY_W&&7u*j<=PX_KEY_H)sc=j;if(!sc)sc=1u;}
 width=(n*6u-1u)*sc;height=7u*sc;
 ox=(unsigned)PX_KEY_W>width?((unsigned)PX_KEY_W-width)/2u:0u;
 oy=(unsigned)PX_KEY_H>height?((unsigned)PX_KEY_H-height)/2u:0u;
 for(i=0;i<n;i++){unsigned g=pxkey_index((unsigned char)s[i]);
  for(j=0;j<7;j++){unsigned r=px_key_font[g][j];
   for(c=0;c<5;c++)if(r&(16u>>c))
    for(dy=0;dy<sc;dy++)for(dx=0;dx<sc;dx++){
     px=ox+(i*6u+c)*sc+dx;py=oy+j*sc+dy;
     bi=py*(unsigned)PX_KEY_W+px;panel_mask[bi>>3]|=(u8)(128u>>(bi&7));}
  }
 }
 blit((u8*)p,x,y,w,h,panel_mask,0,(unsigned)PX_KEY_W,(unsigned)PX_KEY_H,(unsigned)PX_KEY_X,(unsigned)PX_KEY_Y,PX_KEY_FG,PX_KEY_BG);
}
#endif

#if FX_TOPBAR
/* Top status bar: replaces the default status cluster (whale-girl scheme). */
#ifndef PX_TOPBAR_BATTERY
#define PX_TOPBAR_BATTERY 1
#endif
#ifndef PX_TOPBAR_CAPS
#define PX_TOPBAR_CAPS 1
#endif
#define TB_GREEN 0x4ef0u   /* #4ade80 */
#define TB_AMBER 0xfde4u   /* #fbbf24 */
#define TB_RED   0xea28u   /* #ef4444 */
#define TB_BLUE  0x3b5bu   /* #3f6bd8 */
#define TB_OFF   0xef9fu   /* #eef2fb */
#define TB_BORDER 0xc67du  /* #c3cee8 */
#define TB_INK   0x3a2eu  /* #3a4670: battery shell, tip and percent text */
#define TB_GREY  0xadbbu   /* #aab6d8 */
#if PX_TOPBAR_BATTERY
static const unsigned char tb_bolt[9]={6,4,8,31,2,4,8,16,0};
#endif
#if PX_TOPBAR_CAPS
static const unsigned char tb_chev[5]={8,28,62,127,0};
#endif
static void tb_fill(u8 *p,unsigned x,unsigned y,unsigned w,unsigned h,unsigned rx,unsigned ry,unsigned rw,unsigned rh,u16 c){
 unsigned x0,y0,x1,y1,px,py;
 x0=x>rx?x:rx;y0=y>ry?y:ry;x1=x+w<rx+rw?x+w:rx+rw;y1=y+h<ry+rh?y+h:ry+rh;
 for(py=y0;py<y1;py++)for(px=x0;px<x1;px++)put(p,w,h,x,y,px,py,c);
}
#if PX_TOPBAR_CAPS
static void tb_text(u8 *p,unsigned x,unsigned y,unsigned w,unsigned h,unsigned tx,unsigned ty,const char *s,unsigned n,u16 c){
 unsigned i,j,k;
 for(i=0;i<n;i++){unsigned g=pxkey_index((unsigned char)s[i]);
  for(j=0;j<7;j++){unsigned r=px_key_font[g][j];
   for(k=0;k<5;k++)if(r&(16u>>k))put(p,w,h,x,y,tx+i*6u+k,ty+j,c);
  }
 }
}
#endif
#if PX_TOPBAR_BATTERY
static void tb_battery(u8 *p,unsigned x,unsigned y,unsigned w,unsigned h){
 unsigned pct=ui.known?ui.battery:255u,fill,n,px,py,i;u16 c;
 u8 s[4];
 c=pct>40u?TB_GREEN:(pct>=16u?TB_AMBER:TB_RED);
 tb_fill(p,x,y,w,h,14,13,28,11,TB_INK);
 tb_fill(p,x,y,w,h,16,15,24,7,px_status_bg[0]);
 tb_fill(p,x,y,w,h,42,16,3,6,TB_INK);
 if(pct<=100){fill=(22u*pct+50u)/100u;tb_fill(p,x,y,w,h,17,15,fill,7,c);}
 if(ui.charge)for(py=0;py<9;py++){unsigned r=tb_bolt[py];
  for(px=0;px<5;px++)if(r&(16u>>px))put(p,w,h,x,y,25+px,14+py,0xffffu);}
 n=0;
 if(pct>100){s[n++]='-';s[n++]='-';}
 else{if(pct>=100){s[n++]='1';s[n++]='0';s[n++]='0';}
  else{if(pct>=10)s[n++]=(u8)('0'+pct/10u);s[n++]=(u8)('0'+pct%10u);}
  s[n++]='%';}
 for(i=0;i<n;i++){unsigned g=pxglyph((unsigned char)s[i]);
  for(py=0;py<7;py++){unsigned r=px_font[g][py];
   for(px=0;px<5;px++)if(r&(16u>>px))put(p,w,h,x,y,50+i*6u+px,15+py,TB_INK);
  }
 }
}
#endif
#if PX_TOPBAR_CAPS
static void tb_caps(u8 *p,unsigned x,unsigned y,unsigned w,unsigned h){
 unsigned px,py;u8 caps=(u8)(ui.caps^ui.caps_inv);u16 fg=caps?0xffffu:TB_GREY;
 tb_fill(p,x,y,w,h,252,10,60,17,caps?TB_BLUE:TB_BORDER);
 if(!caps)tb_fill(p,x,y,w,h,253,11,58,15,TB_OFF);
 tb_text(p,x,y,w,h,260,14,"CAPS",4,fg);
 for(py=0;py<5;py++){unsigned r=tb_chev[py];
  for(px=0;px<7;px++)if(r&(64u>>px))put(p,w,h,x,y,297+px,17+py,fg);}
}
#endif
static void draw_topbar(u8 *p,u16 x,u16 y,u16 w,u16 h){
 (void)p;(void)x;(void)y;(void)w;(void)h;
#if !PX_TOPBAR_BATTERY
 (void)pxglyph;
#endif
#if PX_TOPBAR_BATTERY
 tb_battery((u8*)p,x,y,w,h);
#endif
#if PX_TOPBAR_CAPS
 tb_caps((u8*)p,x,y,w,h);
#endif
}
#endif

void rainy_hook_cached_draw(u16 x,u16 y,u16 w,u16 h,const u8 *p){
 u32 address=(u32)p,size=(u32)w*h*2;unsigned i,f;const PxLayer *L;
#if !FX_TOPBAR
 unsigned px,py,n;u8 b[32];u8 s[4];u16 val;
#endif
 if(!ui.suspended&&w&&h&&w<=320&&h<=172&&x+w<=320&&y+h<=172&&address>=0x20000000u&&address<=0x2005f000u-size&&current_object()){
  if(LCD_BUSY)return;
  if(!ui.active){ui.active=1;ui.dirty=1;}
  f=ui.frm;
  for(i=0;i<PX_LAYER_COUNT;i++){
   u16 fg,bg;
   L=&px_layers[i];fg=L->fg[f];bg=L->bg[f];
#if FX_MOTION
   if(f==PX_FRAME_REACT&&(unsigned)L->motion<(unsigned)PX_MOTION_COUNT){
    const PxMotion *M=&px_motions[L->motion];
    if(M->count){
     unsigned mi=M->firstOff+(unsigned)((clock_ms()/(u32)(M->keyPeriodMs?M->keyPeriodMs:1u)+(u32)ui.keys*M->advancePerKey)%M->count);
     int ox=0,oy=0,X,Y;
     if(M->travelRange){int tr=(int)ui.keys*(int)M->stepPerKey;if(tr>(int)M->travelRange)tr=(int)M->travelRange;if(M->axis)oy=tr;else ox=tr;}
     X=(int)L->x+ox+(int)px_motion_dx[mi];Y=(int)L->y+oy+(int)px_motion_dy[mi];
     if(X<0)X=0;else if(X>(int)(SCR_W-L->w))X=(int)(SCR_W-L->w);
     if(Y<0)Y=0;else if(Y>(int)(SCR_H-L->h))Y=(int)(SCR_H-L->h);
     blit((u8*)p,x,y,w,h,masks,L->off[f],L->w,L->h,L->x,L->y,bg,bg);
     blit((u8*)p,x,y,w,h,masks,px_motion_maskoff[mi],L->w,L->h,(unsigned)X,(unsigned)Y,L->fg[2],bg);
     continue;
    }
   }
#endif
#if PX_PULSE_LAYER >= 0
   if(i==(unsigned)PX_PULSE_LAYER)fg=pulse_color(fg,clock_ms());
#endif
   blit((u8*)p,x,y,w,h,masks,L->off[f],L->w,L->h,L->x,L->y,fg,bg);
  }
#if FX_PARTS
  draw_parts((u8*)p,x,y,w,h);
#endif
#if FX_PANEL
  draw_panel((u8*)p,x,y,w,h);
#endif
#if FX_TOPBAR
  draw_topbar((u8*)p,x,y,w,h);
#else
  /* status cluster: connection icon (16x16), battery gauge (20x8), percent (23x7) */
  n=(ui.known&&ui.mode<5)?(ui.mode==1u?0u:ui.mode==0u?1u:2u):3u;
  for(py=0;py<16;py++){unsigned r=n<3?connection_icons[n][py]:0;b[py*2]=(u8)(r>>8);b[py*2+1]=(u8)r;}
  blit((u8*)p,x,y,w,h,b,0,16,16,233,12,PX_STATUS_INK,px_status_bg[0]);
  val=ui.known?ui.battery:255u;
  for(px=0;px<20;px++)b[px]=batt[px];
  if(val<=100){unsigned f=(12u*val+99u)/100u;
   for(py=2;py<6;py++){unsigned bi=py*20+2u;for(px=0;px<f;px++,bi++)b[bi>>3]|=(u8)(128u>>(bi&7));}
  }
  blit((u8*)p,x,y,w,h,b,0,20,8,264,17,PX_STATUS_INK,px_status_bg[1]);
  n=0;
  if(val>100){s[n++]='-';s[n++]='-';}
  else{if(val>=100){s[n++]='1';s[n++]='0';s[n++]='0';}else{if(val>=10)s[n++]=(u8)('0'+val/10);s[n++]=(u8)('0'+val%10);}s[n++]='%';}
  for(py=0;py<21;py++)b[py]=0;
  for(i=0;i<n;i++){unsigned g=pxglyph(s[i]);
   for(py=0;py<7;py++){unsigned r=px_font[g][py];
    for(px=0;px<5;px++)if(r&(16u>>px)){unsigned bi=py*23+12u-3u*n+i*6u+px;b[bi>>3]|=(u8)(128u>>(bi&7));}}
  }
  blit((u8*)p,x,y,w,h,b,0,23,7,287,17,PX_STATUS_INK,px_status_bg[2]);
#endif
  ui.pointer=address;ui.object=current_object();ui.x=x;ui.y=y;ui.w=w;ui.h=h;
  ui.has_surface=R(ui.object+0x658)==address;ui.dirty=0;ui.count++;
 }
 ((void(*)(u16,u16,u16,u16,const u8*))0x0805d6f3)(x,y,w,h,p);
}
int rainy_hook_start(void){
 volatile u8 *p=&__live_bss_start__;while(p<&__live_bss_end__)*p++=0;
 load_masks();
 ui.rng=0x1234567u;
 ui.last_tick=clock_ms();ui.last_key_ms=ui.last_cont=ui.energy_start=ui.last_tick;
 return ((int(*)(void))0x0807a601)();
}
void rainy_hook_gui(void){if(!ui.active)((void(*)(void))0x0802dca9)();}
void rainy_hook_misc(void){if(!ui.active)((void(*)(void))0x0805b031)();}
void rainy_hook_image(void){
 u32 now=clock_ms(),dt=now-ui.last_tick;ui.last_tick=now;
 if(dt<40u)dt=40u;if(dt>500u)dt=500u;
 if(!ui.suspended)rtc_tick(now);
 if(!ui.active){((void(*)(void))0x0805b245)();return;}
#if FX_PARTS
 if(advance_parts(dt))ui.dirty=1;
#endif
#if FX_TRIGGER_CONT
 if((u32)(now-ui.last_cont)>=140u){ui.last_cont=now;spawn(1);}
#endif
 {unsigned f;u32 idle=now-ui.last_key_ms;
  if(ui.caps^ui.caps_inv)f=PX_FRAME_CAPS;
  else if(idle<=(u32)FX_REACT_HOLD_MS)f=PX_FRAME_REACT;
  else if(idle>=(u32)FX_SLEEPY_MS)f=PX_FRAME_SLEEPY;
#if FX_CHARGE_REACT
  else if(ui.charge)f=PX_FRAME_REACT;
#endif
  else f=PX_FRAME_CALM;
  if(f!=ui.frm){
#if FX_MOTION
   if(ui.frm==PX_FRAME_REACT)ui.keys=0;
#endif
   ui.frm=(u8)f;ui.dirty=1;}}
#if PX_PULSE_LAYER >= 0
 ui.dirty=1;
#endif
 *(volatile u16*)0x2003edec=1;
 *(volatile u32*)0x2003edf0=0u;
 if(!LCD_BUSY){((void(*)(void))0x0805b245)();if(!LCD_BUSY&&ui.dirty&&surface_matches())rainy_hook_cached_draw(ui.x,ui.y,ui.w,ui.h,(const u8*)ui.pointer);}
}
void rainy_hook_native_key(int key,unsigned raw5,unsigned raw6){
 u32 now=clock_ms();
 if((u16)key){
  if((u16)key==57u){
   u32 dt=(u32)(now-ui.caps_at);
   if(dt>25u){
    ui.caps^=1u;
#if FX_PANEL
    /* a quick second tap cancels the pair and flips the display offset instead:
       use it to align the badge with the keyboard LED without reflashing */
    if(ui.caps_at&&dt<=150u)ui.caps_inv^=1u;
#endif
#if FX_COUNT
    spawn(FX_COUNT/2u+1u);
#endif
   }
   ui.caps_at=now;
#if FX_PANEL
   ui.panel_key=57u;
#endif
   /* always repaint immediately, even when a repeat event did not toggle */
   ui.dirty=1;
   ui.frm=(u8)((ui.caps^ui.caps_inv)?PX_FRAME_CAPS:PX_FRAME_REACT);
  }
#if FX_TRIGGER_KEY || FX_MOTION
  else{
#if FX_MOTION
   ui.keys++;
#endif
#if FX_TRIGGER_KEY
   ui.dirty=1;
#if FX_COUNT
   {unsigned n=FX_COUNT;
#if FX_ENERGY_BONUS
    if((u32)(now-ui.energy_start)<=1500u)ui.hits++;else{ui.hits=1;ui.energy_start=now;}
    if(ui.hits>=3u)n+=FX_COUNT/2u;
#endif
    spawn(n);}
#endif
#endif
  }
#endif
  ui.last_key_ms=now;
  ui.key=(u16)key;
#if FX_PANEL
  if((u16)key!=57u)ui.panel_key=(u16)key;
#endif
 }
 ((void(*)(int,unsigned,unsigned))0x0805ac73)(key,raw5,raw6);
}
void rainy_hook_native_status(unsigned battery,unsigned charge,unsigned mode){
 ui.battery=battery>100?100:(u8)battery;ui.charge=(u8)charge;ui.mode=(u8)mode;ui.known=1;ui.dirty=1;
 ((void(*)(unsigned,unsigned,unsigned))0x0805ae0b)(battery,charge,mode);
}
static int valid(const u8 *p,u16 n){unsigned i,sum=0;if(n<11||n>241||p[0]!=0xbe||p[1]!=0x1a||p[2]!=n||p[7]||p[n-1]!=0xed)return 0;for(i=3;i<(unsigned)n-3;i++)sum+=p[i];return (sum&65535u)==(unsigned)(p[n-3]|(p[n-2]<<8));}
void rainy_hook_ips(const u8 *p,u16 n){
 u16 seq;unsigned op,v;
 if(!p||n<4)return;
 if(rtc_receive(p,n,clock_ms()))return;
 if(p[3]!=13){if(ui.active&&p[3]!=10&&p[3]!=11){ack(FORMAT,0);return;}((void(*)(const u8*,u16))0x080596ad)(p,n);return;}
 if(!valid(p,n)){ack(FORMAT,0);return;}seq=(u16)(p[5]|(p[6]<<8));op=p[4];
 if(op==0&&n==11){ack(0xa5,0x364c);return;}
 if((op==2||op==5)&&n==11){if(LCD_BUSY){ack(BUSY,seq);return;}ui.suspended=op==2;ui.active=0;ui.has_surface=0;
#if FX_MOTION
   if(op==5)ui.keys=0;
#endif
   ack(DONE,seq);return;}
 if(op==23&&n==12){ui.caps=(u8)(p[8]&1u);ui.dirty=1;ack(DONE,seq);return;}
 if(op==11&&n==11){
  switch(seq){case 0:v=0x5537;break;case 1:v=ui.key;break;case 2:v=ui.known?(ui.battery|(ui.charge<<8)):0xffff;break;case 3:v=ui.known?ui.mode:0xffff;break;case 4:v=rtc_state();break;case 5:v=rtc_value()&65535u;break;case 6:v=rtc_value()>>16;break;case 7:v=ui.active;break;case 8:v=ui.modifiers;break;case 9:v=(u16)ui.count;break;case 14:v=*(volatile u16*)0x1ffff7e0u;break;case 15:v=*(volatile u8*)0x1ffff7f3u;break;default:ack(RANGE,seq);return;}
  ack(0xb0+seq,(u16)v);return;
 }
 ack(FORMAT,seq);
}
