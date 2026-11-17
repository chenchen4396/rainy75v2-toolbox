/* SPDX-License-Identifier: MIT
 * Base screen with CapsLock theme switching: silver by default, pink while CapsLock is on.
 * Everything is drawn by the firmware (instant switch, no asset swap, no PC script).
 */
#include "native_ui.h"
#include "cache_font.h"
#include "ui_assets.h"
#define R(a) (*(volatile u32*)(a))
#define LCD_BUSY R(0x20001c6c)
extern u8 __live_bss_start__,__live_bss_end__;

typedef struct { u16 top, bottom, ink, accent, panel; } Theme;

static const Theme SILVER = { 0xdefcu, 0x8cb3u, 0x2966u, 0x6bafu, 0xbdf8u };
static const Theme PINK   = { 0xff1du, 0xfc57u, 0x5886u, 0xfa71u, 0xfdbau };

static struct {
 u8 status[73];
 u32 pointer,object,caps_at;
 u16 x,y,w,h,key;
 u8 active,suspended,has_surface,dirty,status_dirty,known,battery,charge,mode,modifiers,caps,caps_set;
} ui;

static u32 clock_ms(void){return ((u32(*)(void))0x0803a2bb)();}
static void zero(u8 *p,unsigned n){while(n--)*p++=0;}
static void ack(unsigned status,u16 seq){
 u8 p[8]={0xbe,0x1a,8,13,(u8)status,(u8)seq,(u8)(seq>>8),0xed};unsigned i,spins;
 for(i=0;i<8;i++){for(spins=0;spins<4096;spins++)if(R(0x40004c00)&0x40u)break;if(spins==4096)return;R(0x40004c04)=p[i];}
}
static const Theme *theme(void){return ui.caps?&PINK:&SILVER;}
static u16 lerp(u16 a,u16 b,unsigned k){
 unsigned ar=(a>>11)&31,ag=(a>>5)&63,ab=a&31,br=(b>>11)&31,bg=(b>>5)&63,bb=b&31;
 unsigned r=(ar*(256-k)+br*k)>>8,g=(ag*(256-k)+bg*k)>>8,bl=(ab*(256-k)+bb*k)>>8;
 return (u16)((r<<11)|(g<<5)|bl);
}
static void clear_slot(unsigned slot){
 unsigned off=slot==0?0u:slot==1?32u:52u,bytes=slot==0?32u:slot==1?20u:21u;
 zero(ui.status+off,bytes);
}
static void dot(unsigned slot,unsigned x,unsigned y){
 unsigned off=slot==0?0u:slot==1?32u:52u,w=slot==0?16u:slot==1?20u:23u,h=slot==0?16u:slot==1?8u:7u,bit;
 if(x>=w||y>=h)return;bit=y*w+x;ui.status[off+(bit>>3)]|=(u8)(128u>>(bit&7));
}
static void text_slot(unsigned slot,const u8 *str,unsigned n,unsigned scale){
 unsigned i,j,k,ox,oy,width;unsigned w=slot==0?16u:slot==1?20u:23u,h=slot==0?16u:slot==1?8u:7u;
 while(scale>1&&n&&(n*6u-1u)*scale>w)scale--;
 width=n?(n*6u-1u)*scale:0;ox=width>w?0u:(w-width)/2u;oy=h>7*scale?(h-7*scale)/2u:0u;
 clear_slot(slot);
 for(i=0;i<n;i++)for(j=0;j<7;j++)for(k=0;k<5;k++)if(cache_font[glyph_index(str[i])][j]&(16u>>k)){
  unsigned dx,dy;for(dy=0;dy<scale;dy++)for(dx=0;dx<scale;dx++)dot(slot,ox+(i*6u+k)*scale+dx,oy+j*scale+dy);
 }
}
static void status_masks(void){
 unsigned x,y,value,bit,icon;u8 s[4];
 clear_slot(0);clear_slot(1);clear_slot(2);
 if(ui.known&&ui.mode<5){
  icon=ui.mode==UI_USB_RAW?0:ui.mode==UI_RF_RAW?1:2;
  for(y=0;y<16;y++)for(x=0;x<16;x++)if(connection_icons[icon][y]&(1u<<(15-x)))dot(0,x,y);
 }
 value=ui.known?ui.battery:255;
 for(y=0;y<8;y++)for(x=0;x<20;x++){
  bit=(x<17&&(x==0||x==16||y==0||y==7))||(x==17&&y>=2&&y<6);
  if(x>=2&&x<14&&y>=2&&y<6)bit=value<=100?(x-2)*100u<12u*value:(y==4&&x>=6&&x<10);
  if(bit)dot(1,x,y);
 }
 if(value>100){s[0]='-';s[1]='-';text_slot(2,s,2,1);}
 else{unsigned n=0;if(value>=100){s[n++]='1';s[n++]='0';s[n++]='0';}else{if(value>=10)s[n++]=(u8)('0'+value/10);s[n++]=(u8)('0'+value%10);}s[n++]='%';text_slot(2,s,n,1);}
}
static void refresh(void){if(ui.status_dirty){status_masks();ui.status_dirty=0;ui.dirty=1;}}
static u32 current_object(void){u32 o=R(0x2003ede8);return o>=0x20000000u&&o<=0x2005f000u-0x65cu?o:0;}
static int surface_matches(void){return ui.has_surface&&ui.object==current_object()&&R(ui.object+0x658)==ui.pointer&&*(volatile u16*)0x2003edba==ui.w&&*(volatile u16*)0x2003edbc==ui.h&&*(volatile u16*)0x2003edbe==ui.x&&*(volatile u16*)0x2003edc0==ui.y;}
static void put(u8 *p,u16 w,u16 ox,u16 oy,u16 x,u16 y,u16 c){
 if(x<ox||y<oy||x>=ox+w||y>=oy+172u)return;
 {unsigned at=((y-oy)*w+x-ox)*2;p[at]=(u8)c;p[at+1]=(u8)(c>>8);}
}
static void glyph(u8 *p,u16 w,u16 ox,u16 oy,unsigned gx,unsigned gy,unsigned scale,const u8 *rows){
 unsigned j,k,dx,dy;
 for(j=0;j<7;j++)for(k=0;k<5;k++)if(rows[j]&(16u>>k))
  for(dy=0;dy<scale;dy++)for(dx=0;dx<scale;dx++)put(p,w,ox,oy,(u16)(gx+k*scale+dx),(u16)(gy+j*scale+dy),theme()->ink);
}
void rainy_hook_cached_draw(u16 x,u16 y,u16 w,u16 h,const u8 *p){
 u32 address=(u32)p,size=(u32)w*h*2;unsigned i,px,py,bit,at;const Theme *t;
 if(!ui.suspended&&w&&h&&w<=320&&h<=172&&x+w<=320&&y+h<=172&&address>=0x20000000u&&address<=0x2005f000u-size&&current_object()){
  if(LCD_BUSY)return;
  if(!ui.active){ui.active=1;ui.status_dirty=1;}
  refresh();t=theme();
  /* background: vertical silver/pink gradient over the whole frame */
  for(py=y;py<y+h;py++){
   unsigned k=(unsigned)py*255u/171u;u16 c=lerp(t->top,t->bottom,k);
   for(px=x;px<x+w;px++){at=((py-y)*w+px-x)*2;((u8*)p)[at]=(u8)c;((u8*)p)[at+1]=(u8)(c>>8);}
  }
  /* metallic highlight + shadow lines */
  for(px=x;px<x+w;px++){
   if(y<=10&&10<y+h)put((u8*)p,w,x,y,px,10,t->panel);
   if(y<=11&&11<y+h)put((u8*)p,w,x,y,px,11,t->panel);
   if(y<=160&&160<y+h)put((u8*)p,w,x,y,px,160,t->accent);
   if(y<=161&&161<y+h)put((u8*)p,w,x,y,px,161,t->accent);
  }
  /* big Aa glyph */
  {
   unsigned gx=140,gy=44;const u8 *rows=(const u8*)(ui.caps?cache_font[glyph_index('A')]:cache_font[glyph_index('a')]);
   glyph((u8*)p,w,x,y,gx,gy,8,rows);
  }
  /* label: CAPS LOCK  +  ON/OFF */
  {
   const char *lab="CAPS LOCK";unsigned n=9,i2,j,k,ox=(320u-n*12u)/2u;
   for(i2=0;i2<n;i2++)for(j=0;j<7;j++)for(k=0;k<5;k++)
    if(cache_font[glyph_index((u8)lab[i2])][j]&(16u>>k))
     for(py=0;py<2;py++)for(px=0;px<2;px++)put((u8*)p,w,x,y,(u16)(ox+i2*12u+k*2u+px),(u16)(116u+j*2u+py),t->ink);
  }
  {
   const char *lab=ui.caps?"ON":"OFF";unsigned n=ui.caps?2u:3u,i2,j,k,ox=(320u-n*18u)/2u;
   for(i2=0;i2<n;i2++)for(j=0;j<7;j++)for(k=0;k<5;k++)
    if(cache_font[glyph_index((u8)lab[i2])][j]&(16u>>k))
     for(py=0;py<3;py++)for(px=0;px<3;px++)put((u8*)p,w,x,y,(u16)(ox+i2*18u+k*3u+px),(u16)(136u+j*3u+py),t->accent);
  }
  /* status cluster (top right) */
  {
   const u16 geo[3][4]={{233,12,16,16},{264,17,20,8},{287,17,23,7}};
   for(i=0;i<3;i++){
    unsigned off=i==0?0u:i==1?32u:52u,rw=geo[i][2],rh=geo[i][3],rx=geo[i][0],ry=geo[i][1];
    unsigned x0=x>rx?x:rx,y0=y>ry?y:ry,x1=x+w<rx+rw?x+w:rx+rw,y1=y+h<ry+rh?y+h:ry+rh;
    for(py=y0;py<y1;py++)for(px=x0;px<x1;px++){
     bit=(py-ry)*rw+px-rx;
     if(ui.status[off+(bit>>3)]&(128u>>(bit&7)))put((u8*)p,w,x,y,px,py,t->ink);
    }
   }
  }
  ui.pointer=address;ui.object=current_object();ui.x=x;ui.y=y;ui.w=w;ui.h=h;
  ui.has_surface=R(ui.object+0x658)==address;ui.dirty=0;
 }
 ((void(*)(u16,u16,u16,u16,const u8*))0x0805d6f3)(x,y,w,h,p);
}
int rainy_hook_start(void){volatile u8 *p=&__live_bss_start__;while(p<&__live_bss_end__)*p++=0;ui.caps=0;ui.caps_set=1;return ((int(*)(void))0x0807a601)();}
void rainy_hook_gui(void){if(!ui.active)((void(*)(void))0x0802dca9)();}
void rainy_hook_misc(void){if(!ui.active)((void(*)(void))0x0805b031)();}
void rainy_hook_image(void){
 u32 now=clock_ms();
 if(!ui.suspended)rtc_tick(now);
 if(!ui.active){((void(*)(void))0x0805b245)();return;}
 refresh();
 if(ui.dirty&&!LCD_BUSY){*(volatile u16*)0x2003edec=1u;*(volatile u32*)0x2003edf0=0u;}
 if(!LCD_BUSY){((void(*)(void))0x0805b245)();if(!LCD_BUSY&&ui.dirty&&surface_matches())rainy_hook_cached_draw(ui.x,ui.y,ui.w,ui.h,(const u8*)ui.pointer);}
}
void rainy_hook_native_key(int key,unsigned raw5,unsigned raw6){
 u32 now=clock_ms();
 ui.modifiers=(u8)raw6;
 if((u16)key){
  if((u16)key==57u){
   u32 dt=(u32)(now-ui.caps_at);
   if(dt>600u){ui.caps^=1u;ui.caps_set=1;ui.dirty=1;}
   ui.caps_at=now;
  }
  ui.key=(u16)key;
 }
 ((void(*)(int,unsigned,unsigned))0x0805ac73)(key,raw5,raw6);
}
void rainy_hook_native_status(unsigned battery,unsigned charge,unsigned mode){
 ui.battery=battery>100?100:(u8)battery;ui.charge=(u8)charge;ui.mode=(u8)mode;ui.known=1;ui.status_dirty=1;
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
 if((op==2||op==5)&&n==11){if(LCD_BUSY){ack(BUSY,seq);return;}ui.suspended=op==2;ui.active=0;ui.has_surface=0;ack(DONE,seq);return;}
 if(op==12&&n==18){ack(rtc_schedule(p+8,seq,clock_ms()),seq);return;}
 if(op==23&&n==12){ui.caps=(u8)(p[8]&1u);ui.caps_set=1;ui.dirty=1;ack(DONE,seq);return;}
 if(op==11&&n==11){
  switch(seq){case 0:v=0x5537;break;case 1:v=ui.key;break;case 2:v=ui.known?(ui.battery|(ui.charge<<8)):0xffff;break;case 3:v=ui.known?ui.mode:0xffff;break;case 4:v=rtc_state();break;case 5:v=rtc_value()&65535u;break;case 6:v=rtc_value()>>16;break;case 7:v=ui.active;break;case 8:v=ui.modifiers;break;case 14:v=*(volatile u16*)0x1ffff7e0u;break;case 15:v=*(volatile u8*)0x1ffff7f3u;break;default:ack(RANGE,seq);return;}
  ack(0xb0+seq,(u16)v);return;
 }
 ack(FORMAT,seq);
}
