/* SPDX-License-Identifier: MIT
 * Base screen (GIF untouched) with a bigger top bar and a CapsLock flame effect:
 *  - top bar: big "A"/"a" caps indicator, big connection icon, big battery + percent
 *  - no clock
 *  - CapsLock on: animated flames above the character (right side of the screen)
 */
#include "native_ui.h"
#include "cache_font.h"
#include "ui_assets.h"
#define R(a) (*(volatile u32*)(a))
#define LCD_BUSY R(0x20001c6c)
extern u8 __live_bss_start__,__live_bss_end__;

static struct {
 u32 pointer,object,caps_at,last_draw;
 u16 x,y,w,h,key;
 u8 active,suspended,has_surface,dirty,status_dirty,known,battery,charge,mode,modifiers,caps;
} ui;

static u32 clock_ms(void){return ((u32(*)(void))0x0803a2bb)();}
static void ack(unsigned status,u16 seq){
 u8 p[8]={0xbe,0x1a,8,13,(u8)status,(u8)seq,(u8)(seq>>8),0xed};unsigned i,spins;
 for(i=0;i<8;i++){for(spins=0;spins<4096;spins++)if(R(0x40004c00)&0x40u)break;if(spins==4096)return;R(0x40004c04)=p[i];}
}
static void put(u8 *p,u16 w,u16 ox,u16 oy,u16 x,u16 y,u16 c){
 if(x<ox||y<oy||x>=ox+w||y>=oy+172u)return;
 {unsigned at=((y-oy)*w+x-ox)*2;p[at]=(u8)c;p[at+1]=(u8)(c>>8);}
}
static u32 current_object(void){u32 o=R(0x2003ede8);return o>=0x20000000u&&o<=0x2005f000u-0x65cu?o:0;}
static int surface_matches(void){return ui.has_surface&&ui.object==current_object()&&R(ui.object+0x658)==ui.pointer&&*(volatile u16*)0x2003edba==ui.w&&*(volatile u16*)0x2003edbc==ui.h&&*(volatile u16*)0x2003edbe==ui.x&&*(volatile u16*)0x2003edc0==ui.y;}
static void glyph_at(u8 *p,u16 w,u16 ox,u16 oy,u16 gx,u16 gy,unsigned scale,u16 color,const u8 *rows){
 unsigned j,k,dx,dy;
 for(j=0;j<7;j++)for(k=0;k<5;k++)if(rows[j]&(16u>>k))
  for(dy=0;dy<scale;dy++)for(dx=0;dx<scale;dx++)put(p,w,ox,oy,(u16)(gx+k*scale+dx),(u16)(gy+j*scale+dy),color);
}
static void text_at(u8 *p,u16 w,u16 ox,u16 oy,unsigned x,unsigned y,const char *s,unsigned n,unsigned scale,u16 color){
 unsigned i,j,k,dx,dy;
 for(i=0;i<n;i++)for(j=0;j<7;j++)for(k=0;k<5;k++)if(cache_font[glyph_index((u8)s[i])][j]&(16u>>k))
  for(dy=0;dy<scale;dy++)for(dx=0;dx<scale;dx++)put(p,w,ox,oy,(u16)(x+(i*6u+k)*scale+dx),(u16)(y+j*scale+dy),color);
}
/* connection icon, drawn at 2x (32x32) */
static void conn_icon(u8 *p,u16 w,u16 ox,u16 oy,unsigned x,unsigned y,u16 color){
 unsigned i,j,icon=ui.known?(ui.mode==UI_USB_RAW?0:ui.mode==UI_RF_RAW?1:2):2,dx,dy;
 for(j=0;j<16;j++)for(i=0;i<16;i++)if(connection_icons[icon][j]&(1u<<(15-i)))
  for(dy=0;dy<2;dy++)for(dx=0;dx<2;dx++)put(p,w,ox,oy,(u16)(x+i*2+dx),(u16)(y+j*2+dy),color);
}
/* big battery 56x22 at (x,y) */
static void battery_big(u8 *p,u16 w,u16 ox,u16 oy,unsigned x,unsigned y,u16 color){
 unsigned i,level=ui.known?(ui.battery>100?100:ui.battery):0,fillw;
 for(i=0;i<56;i++){
  put(p,w,ox,oy,(u16)(x+i),(u16)y,color);put(p,w,ox,oy,(u16)(x+i),(u16)(y+21),color);
 }
 for(i=0;i<22;i++){
  put(p,w,ox,oy,(u16)x,(u16)(y+i),color);put(p,w,ox,oy,(u16)(x+55),(u16)(y+i),color);
  if(i>=6&&i<16){put(p,w,ox,oy,(u16)(x+56),(u16)(y+i),color);put(p,w,ox,oy,(u16)(x+57),(u16)(y+i),color);put(p,w,ox,oy,(u16)(x+58),(u16)(y+i),color);}
 }
 fillw=(unsigned)((50u*level)/100u);
 for(i=2;i<20;i++){unsigned k;for(k=0;k<fillw;k++)put(p,w,ox,oy,(u16)(x+3+k),(u16)(y+i),color);}
}
/* flames above the character head: 3 tongues, animated */
static void flames(u8 *p,u16 w,u16 ox,u16 oy,u32 now){
 static const u16 RED=0xf8a3u,ORG=0xfb80u,YEL=0xfe60u; /* 565 */
 unsigned f,phase=(unsigned)((now/90u)&7u);
 for(f=0;f<3;f++){
  unsigned cx=232u+f*24u, base=40u, h=14u+((phase+f*3u)&7u), i;
  for(i=0;i<h;i++){
   unsigned yy=base-i, half=(i*10u)/h+1u, k;
   for(k=0;k<half;k++){
    u16 c=(k==0||k+1>=half)?RED:(k+1>=half-1?ORG:YEL);
    put(p,w,ox,oy,(u16)(cx-half+k),(u16)yy,c);
    put(p,w,ox,oy,(u16)(cx+half-k),(u16)yy,c);
   }
  }
 }
}
void rainy_hook_cached_draw(u16 x,u16 y,u16 w,u16 h,const u8 *p){
 u32 address=(u32)p,size=(u32)w*h*2;u32 now;
 if(!ui.suspended&&w&&h&&w<=320&&h<=172&&x+w<=320&&y+h<=172&&address>=0x20000000u&&address<=0x2005f000u-size&&current_object()){
  if(LCD_BUSY)return;
  if(!ui.active)ui.active=1;
  now=clock_ms();
  /* top bar: caps indicator, connection, battery, percent (white with dark shadow) */
  {
   const u8 *rows=(const u8*)(ui.caps?cache_font[glyph_index('A')]:cache_font[glyph_index('a')]);
   glyph_at((u8*)p,w,x,y,10,8,5,0x10a2u,rows);
   glyph_at((u8*)p,w,x,y,9,7,5,0xffffu,rows);
   conn_icon((u8*)p,w,x,y,46,9,0x10a2u);
   battery_big((u8*)p,w,x,y,86,10,0x10a2u);
   conn_icon((u8*)p,w,x,y,44,7,0xffffu);
   battery_big((u8*)p,w,x,y,84,8,0xffffu);
   {
    char s[4];unsigned n=0,v=ui.known?ui.battery:0;
    if(!ui.known){s[0]='-';s[1]='-';n=2;}
    else{if(v>=100){s[n++]='1';s[n++]='0';s[n++]='0';}else{if(v>=10)s[n++]=(char)('0'+v/10);s[n++]=(char)('0'+v%10);}s[n++]='%';}
    text_at((u8*)p,w,x,y,150,14,s,n,2,0x10a2u);
    text_at((u8*)p,w,x,y,148,12,s,n,2,0xffffu);
   }
  }
  if(ui.caps)flames((u8*)p,w,x,y,now);
  ui.pointer=address;ui.object=current_object();ui.x=x;ui.y=y;ui.w=w;ui.h=h;
  ui.has_surface=R(ui.object+0x658)==address;ui.dirty=0;ui.last_draw=now;
 }
 ((void(*)(u16,u16,u16,u16,const u8*))0x0805d6f3)(x,y,w,h,p);
}
int rainy_hook_start(void){volatile u8 *p=&__live_bss_start__;while(p<&__live_bss_end__)*p++=0;ui.caps=0;return ((int(*)(void))0x0807a601)();}
void rainy_hook_gui(void){if(!ui.active)((void(*)(void))0x0802dca9)();}
void rainy_hook_misc(void){if(!ui.active)((void(*)(void))0x0805b031)();}
void rainy_hook_image(void){
 u32 now=clock_ms();if(!ui.suspended)rtc_tick(now);
 if(!ui.active){((void(*)(void))0x0805b245)();return;}
 if(ui.caps&&(u32)(now-ui.last_draw)>=80u)ui.dirty=1;   /* animate flames */
 if(ui.dirty){*(volatile u16*)0x2003edec=1u;*(volatile u32*)0x2003edf0=0u;}
 if(!LCD_BUSY){((void(*)(void))0x0805b245)();if(!LCD_BUSY&&ui.dirty&&surface_matches())rainy_hook_cached_draw(ui.x,ui.y,ui.w,ui.h,(const u8*)ui.pointer);}
}
void rainy_hook_native_key(int key,unsigned raw5,unsigned raw6){
 u32 now=clock_ms();
 ui.modifiers=(u8)raw6;
 if((u16)key){
  if((u16)key==57u){u32 dt=(u32)(now-ui.caps_at);if(dt>600u){ui.caps^=1u;ui.dirty=1;}ui.caps_at=now;}
  ui.key=(u16)key;
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
 if((op==2||op==5)&&n==11){if(LCD_BUSY){ack(BUSY,seq);return;}ui.suspended=op==2;ui.active=0;ui.has_surface=0;ack(DONE,seq);return;}
 if(op==12&&n==18){ack(rtc_schedule(p+8,seq,clock_ms()),seq);return;}
 if(op==23&&n==12){ui.caps=(u8)(p[8]&1u);ui.dirty=1;ack(DONE,seq);return;}
 if(op==11&&n==11){
  switch(seq){case 0:v=0x5537;break;case 1:v=ui.key;break;case 2:v=ui.known?(ui.battery|(ui.charge<<8)):0xffff;break;case 3:v=ui.known?ui.mode:0xffff;break;case 4:v=rtc_state();break;case 5:v=rtc_value()&65535u;break;case 6:v=rtc_value()>>16;break;case 7:v=ui.active;break;case 8:v=ui.modifiers;break;case 14:v=*(volatile u16*)0x1ffff7e0u;break;case 15:v=*(volatile u8*)0x1ffff7f3u;break;default:ack(RANGE,seq);return;}
  ack(0xb0+seq,(u16)v);return;
 }
 ack(FORMAT,seq);
}
