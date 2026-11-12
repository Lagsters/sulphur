// Font preview: every glyph of both styles, EN/PL samples and numbers over dark, busy and light
// backgrounds, plus the cycle cost of one 40-character body line.
//   python tools/build.py tools/font/preview.c font_preview
// page 1 (frames < 400 of the program): body glyphs and samples; page 2: title glyphs.
#include "video.h"
#include "time.h"
#include "misc.h"
#include "string.h"

#include "../../src/gen/core.h"
#include "../../src/text.h"

int[ 18 ] s_pl1 = { 90, 97, 136, 133, 131, 129, 32, 103, 130, 134, 108, 128, 32, 106, 97, 135, 132, 0 };
int[ 18 ] s_pl2 = { 90, 65, 145, 142, 140, 138, 32, 71, 139, 143, 76, 137, 32, 74, 65, 144, 141, 0 };
int[ 6 ] s_sl = { 143, 76, 139, 145, 65, 0 };
int[ 7 ] s_kr = { 75, 82, 65, 75, 142, 87, 0 };
// "Zażółć gęślą jaźń, smok z Wawelu ginie!!": 40 characters
int[ 41 ] s_line40 = { 90, 97, 136, 133, 131, 129, 32, 103, 130, 134, 108, 128, 32, 106, 97, 135, 132, 44, 32, 115, 109, 111, 107, 32, 122, 32, 87, 97, 119, 101, 108, 117, 32, 103, 105, 110, 105, 101, 33, 33, 0 };
int[ 19 ] s_ch = { 82, 111, 122, 100, 122, 105, 97, 131, 32, 51, 58, 32, 75, 114, 97, 107, 133, 119, 0 };

int[ 128 ] glyphs;

void fill( int x, int y, int w, int h, int color )
{
    select_texture( core_tex[ CORE_WHITE ] );
    select_region( core_reg[ CORE_WHITE ] );
    set_multiply_color( color );
    set_drawing_scale( w / 16.0, h / 16.0 );
    draw_region_zoomed_at( x, y );
    set_multiply_color( color_white );
}

int pick_color( int i )
{
    int k = ( i / 6 ) % 4;
    if( k == 0 ) return 0xFF2C6A9C;
    if( k == 1 ) return 0xFF7AB0D8;
    if( k == 2 ) return 0xFF3C8040;
    return 0xFFE0E0E0;
}

// stripes of painted-looking colours: text has to read over this
void busy( int x, int y, int w, int h )
{
    for( int i = 0; i < w; i += 6 )
      fill( x + i, y, 6, h, pick_color( i ) );
}

// glyph codes from..to (skipping 127) into glyphs[], zero-terminated
void glyph_run( int from, int to )
{
    int n = 0;
    for( int c = from; c <= to; c++ ) if( c != 127 ) glyphs[ n++ ] = c;
    glyphs[ n ] = 0;
}

int measured = 0;

void page_body()
{
    fill( 0, 0, 640, 180, 0xFF201810 );
    busy( 0, 180, 640, 90 );
    fill( 0, 270, 640, 90, 0xFFD8E8F0 );

    glyph_run( 32, 95 );   text_draw( 6, 4, glyphs, color_white );
    glyph_run( 96, 145 );  text_draw( 6, 26, glyphs, color_white );
    text_draw( 6, 50, s_pl1, color_white );
    text_draw( 200, 50, s_pl2, 0xFF60D0FF );
    text_draw( 420, 50, "Dratewka 0123456789", 0xFF80FF80 );

    int before = get_cycle_counter();
    text_draw( 6, 74, s_line40, color_white );
    measured = get_cycle_counter() - before;
    text_draw( 400, 74, "cycles/40 chars:", 0xFF60D0FF );
    text_number( 560, 74, measured, 0xFF60D0FF );

    text_draw_big( 160, 100, s_sl, color_white, 2 );
    text_draw_big( 470, 100, s_kr, color_white, 2 );
    text_draw_big( 320, 136, s_ch, color_white, 3 );

    glyph_run( 32, 95 );   text_draw( 6, 186, glyphs, color_white );
    glyph_run( 96, 145 );  text_draw( 6, 208, glyphs, 0xFF80F0FF );
    text_draw_big( 320, 228, s_pl2, color_white, 2 );

    glyph_run( 32, 95 );   text_draw( 6, 274, glyphs, color_white );
    text_draw( 6, 296, s_pl1, 0xFF2040C0 );
    text_draw_centered( 450, 296, "-1234567  Level 10", color_white );
    text_draw_big( 320, 314, s_pl1, color_white, 2 );
}

void page_title()
{
    fill( 0, 0, 640, 176, 0xFF201810 );
    busy( 0, 176, 640, 88 );
    fill( 0, 264, 640, 96, 0xFFD8E8F0 );
    glyph_run( 32, 52 );    text_draw_big( 320, 0, glyphs, color_white, 2 );
    glyph_run( 53, 73 );    text_draw_big( 320, 44, glyphs, color_white, 2 );
    glyph_run( 74, 94 );    text_draw_big( 320, 88, glyphs, color_white, 2 );
    glyph_run( 95, 115 );   text_draw_big( 320, 132, glyphs, color_white, 2 );
    glyph_run( 116, 136 );  text_draw_big( 320, 176, glyphs, color_white, 2 );
    glyph_run( 137, 145 );  text_draw_big( 320, 220, glyphs, color_white, 2 );
    text_draw_big( 320, 266, s_ch, 0xFFC0C0FF, 2 );
    text_draw_big( 320, 310, s_pl2, color_white, 2 );
}

void main()
{
    define_core_regions();
    text_init();
    int frame = 0;
    while( true )
    {
        clear_screen( color_black );
        if( frame < 400 ) page_body(); else page_title();
        frame++;
        end_frame();
    }
}
