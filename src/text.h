// Text on screen in the font group's two bitmap styles (tools/font/make.py): body (white with a
// dark outline, tinted by the colour) and title (gilded, for text_draw_big). Strings are int
// arrays of character codes: ASCII 32..126 and 128..145 for Polish letters (tools/assetlib.py).
// y is the top of the line; one draw_region_at per visible glyph, no scaling.
#ifndef TEXT_H
#define TEXT_H

#include "gen/font.h"
#include "gen/font_metrics.h"

#define TEXT_H_PX FONT_BODY_LINE_H     // body line height
#define TEXT_BIG_H_PX FONT_TITLE_LINE_H

void text_init()
{
    define_font_regions();
}

// frame of a character code in a style's sprite, -1 for codes without a glyph
int text_glyph( int c )
{
    if( c >= 32 && c <= 126 ) return c - 32;
    if( c >= 128 && c <= 145 ) return c - 33;
    return -1;
}

int text_width_in( int* s, int* advances )
{
    int w = 0;
    for( int i = 0; s[ i ]; i++ )
    {
        int g = text_glyph( s[ i ] );
        if( g >= 0 ) w += advances[ g ];
    }
    return w;
}

int text_width( int* s ) { return text_width_in( s, font_body_adv ); }

// the first n characters of s in one style; n < 0 draws all of them
void text_draw_style( int x, int y, int* s, int n, int color, int sprite, int* advances )
{
    select_texture( font_tex[ sprite ] );
    set_multiply_color( color );
    int first = font_reg[ sprite ];
    for( int i = 0; s[ i ] && i != n; i++ )
    {
        int g = text_glyph( s[ i ] );
        if( g < 0 ) continue;
        if( g > 0 )
        {
            select_region( first + g );
            draw_region_at( x, y );
        }
        x += advances[ g ];
    }
    set_multiply_color( color_white );
}

void text_draw( int x, int y, int* s, int color ) { text_draw_style( x, y, s, -1, color, FONT_BODY, font_body_adv ); }

// the first n characters only: a line being typed
void text_draw_n( int x, int y, int* s, int n, int color )
{
    if( n <= 0 ) return;
    text_draw_style( x, y, s, n, color, FONT_BODY, font_body_adv );
}

void text_draw_centered( int cx, int y, int* s, int color ) { text_draw( cx - text_width( s ) / 2, y, s, color ); }

// a heading centred on cx: scale 2 or more is the gilded title style (TEXT_BIG_H_PX tall),
// which color_white leaves gold and other colours tint; scale 1 is the body style
void text_draw_big( int cx, int y, int* s, int color, int scale )
{
    if( scale < 2 ) { text_draw_centered( cx, y, s, color ); return; }
    text_draw_style( cx - text_width_in( s, font_title_adv ) / 2, y, s, -1, color, FONT_TITLE, font_title_adv );
}

void text_number( int x, int y, int v, int color )
{
    int[ 16 ] digits;
    itoa( v, digits, 10 );
    text_draw( x, y, digits, color );
}

#endif
