/* SPDX-License-Identifier: MIT
 * Pixel-layer IPS UI: the uploaded background already contains the LOWERCASE artwork,
 * the firmware only overlays the UPPERCASE stickers when CapsLock is on. Switching is a
 * single mask swap, so it is instant (no asset upload).
 */
#include "native_ui.h"
#include "cache_font.h"
#include "ui_assets.h"
#define R(a) (*(volatile u32*)(a))
#define LCD_BUSY R(0x20001c6c)
extern u8 __live_bss_start__,__live_bss_end__;

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
static void status_clear(unsigned slot){
 unsigned off=slot==0?0u:slot==1?32u:52u,bytes=slot==0?32u:slot==1?20u:21u;
 zero(ui.status+off,bytes);
}
static void status_dot(unsigned slot,unsigned x,unsigned y){
 unsigned off=slot==0?0u:slot==1?32u:52u,w=slot==0?16u:slot==1?20u:23u,h=slot==0?16u:slot==1?8u:7u,bit;
 if(x>=w||y>=h)return;bit=y*w+x;ui.status[off+(bit>>3)]|=(u8)(128u>>(bit&7));
}
static void status_text(unsigned slot,const u8 *s,unsigned n,unsigned scale){
 unsigned w=slot==0?16u:slot==1?20u:23u,h=slot==0?16u:slot==1?8u:7u;
 unsigned i,j,k,dx,dy,x,y,width;while(scale>1&&n&&(n*6u-1u)*scale>w)scale--;
 width=n?(n*6u-1u)*scale:0;x=width>w?0:(w-width)/2;y=h>7*scale?(h-7*scale)/2:0;status_clear(slot);
 for(i=0;i<n;i++)for(j=0;j<7;j++)for(k=0;k<5;k++)if(cache_font[glyph_index(s[i])][j]&(16u>>k))
  for(dy=0;dy<scale;dy++)for(dx=0;dx<scale;dx++)status_dot(slot,x+(i*6+k)*scale+dx,y+j*scale+dy);
}
static void status_masks(void){
 unsigned x,y,value,bit,icon;u8 s[4];
 status_clear(0);status_clear(1);
 if(ui.known&&ui.mode<5){
  icon=ui.mode==UI_USB_RAW?0:ui.mode==UI_RF_RAW?1:2;
  for(y=0;y<16;y++)for(x=0;x<16;x++)if(connection_icons[icon][y]&(1u<<(15-x)))status_dot(0,x,y);
 }
 value=ui.known?ui.battery:255;
 for(y=0;y<8;y++)for(x=0;x<20;x++){
  bit=(x<17&&(x==0||x==16||y==0||y==7))||(x==17&&y>=2&&y<6);
  if(x>=2&&x<14&&y>=2&&y<6)bit=value<=100?(x-2)*100u<12u*value:(y==4&&x>=6&&x<10);
  if(bit)status_dot(1,x,y);
 }
 if(value>100)status_text(2,(const u8*)"--",2,1);
 else{unsigned n=0;if(value>=100){s[n++]='1';s[n++]='0';s[n++]='0';}else{if(value>=10)s[n++]=(u8)('0'+value/10);s[n++]=(u8)('0'+value%10);}s[n++]='%';status_text(2,s,n,1);}
}
static void refresh(void){if(ui.status_dirty){status_masks();ui.status_dirty=0;ui.dirty=1;}}
static u32 current_object(void){u32 o=R(0x2003ede8);return o>=0x20000000u&&o<=0x2005f000u-0x65cu?o:0;}
static int surface_matches(void){return ui.has_surface&&ui.object==current_object()&&R(ui.object+0x658)==ui.pointer&&*(volatile u16*)0x2003edba==ui.w&&*(volatile u16*)0x2003edbc==ui.h&&*(volatile u16*)0x2003edbe==ui.x&&*(volatile u16*)0x2003edc0==ui.y;}
void rainy_hook_cached_draw(u16 x,u16 y,u16 w,u16 h,const u8 *p){
 u32 address=(u32)p,size=(u32)w*h*2;unsigned i,x0,y0,x1,y1,px,py,bit,at,color;const PxLayer *L;
 if(!ui.suspended&&w&&h&&w<=320&&h<=172&&x+w<=320&&y+h<=172&&address>=0x20000000u&&address<=0x2005f000u-size&&current_object()){
  if(LCD_BUSY)return;
  if(!ui.active){ui.active=1;ui.status_dirty=1;}
  refresh();
  if(ui.caps){
   for(i=0;i<PX_LAYER_COUNT;i++){
    L=&px_layers[i];
    x0=x>L->x?x:L->x;y0=y>L->y?y:L->y;x1=x+w<L->x+L->w?x+w:L->x+L->w;y1=y+h<L->y+L->h?y+h:L->y+L->h;
    for(py=y0;py<y1;py++)for(px=x0;px<x1;px++){
     bit=(py-L->y)*L->w+px-L->x;color=px_masks[L->off1+(bit>>3)]&(128u>>(bit&7))?L->fg1:L->bg1;
     at=((py-y)*w+px-x)*2;((u8*)p)[at]=(u8)color;((u8*)p)[at+1]=(u8)(color>>8);
    }
   }
  }
  {
   const u16 geo[3][4]={{233,12,16,16},{264,17,20,8},{287,17,23,7}};
   for(i=0;i<3;i++){
    unsigned off=i==0?0u:i==1?32u:52u,rw=geo[i][2],rh=geo[i][3],rx=geo[i][0],ry=geo[i][1];
    x0=x>rx?x:rx;y0=y>ry?y:ry;x1=x+w<rx+rw?x+w:rx+rw;y1=y+h<ry+rh?y+h:ry+rh;
    for(py=y0;py<y1;py++)for(px=x0;px<x1;px++){
     bit=(py-ry)*rw+px-rx;color=ui.status[off+(bit>>3)]&(128u>>(bit&7))?PX_STATUS_INK:px_status_bg[i];
     at=((py-y)*w+px-x)*2;((u8*)p)[at]=(u8)color;((u8*)p)[at+1]=(u8)(color>>8);
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
 u32 now=clock_ms();if(!ui.suspended)rtc_tick(now);
 if(!ui.active){((void(*)(void))0x0805b245)();return;}
 refresh();
 if(!LCD_BUSY){((void(*)(void))0x0805b245)();if(!LCD_BUSY&&ui.dirty&&surface_matches())rainy_hook_cached_draw(ui.x,ui.y,ui.w,ui.h,(const u8*)ui.pointer);}
}
void rainy_hook_native_key(int key,unsigned raw5,unsigned raw6){
 u32 now=clock_ms();
 ui.modifiers=(u8)raw6;
 if((u16)key){
  if((u16)key==57u){
   u32 dt=(u32)(now-ui.caps_at);
   if(dt<=400u){ui.caps=0u;}          /* double tap: resync to lowercase */
   else if(dt>600u){ui.caps^=1u;}     /* single tap: toggle */
   ui.caps_set=1;ui.caps_at=now;ui.dirty=1;
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
