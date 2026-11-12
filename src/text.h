// Text on screen. PLACEHOLDER on the BIOS font (no Polish letters); the font group replaces
// this file, keeping these functions. Strings are int arrays of character codes (ASCII, and
// 128..145 for Polish letters, see tools/assetlib.py).
#ifndef TEXT_H
#define TEXT_H

#define TEXT_H_PX 20          // line height at scale 1

int[ 256 ] text_buf;

void text_init() {}

int text_width( int* s ) { return strlen( s ) * 10; }

void text_draw( int x, int y, int* s, int color )
{
    select_texture( -1 );
    set_multiply_color( color );
    print_at( x, y, s );
    set_multiply_color( color_white );
}

// the first n characters only: a line being typed
void text_draw_n( int x, int y, int* s, int n, int color )
{
    int i = 0;
    while( s[ i ] && i < n && i < 255 ) { text_buf[ i ] = s[ i ]; i++; }
    text_buf[ i ] = 0;
    text_draw( x, y, text_buf, color );
}

void text_draw_centered( int cx, int y, int* s, int color ) { text_draw( cx - text_width( s ) / 2, y, s, color ); }

// a bigger title line; scale 2 or 3
void text_draw_big( int cx, int y, int* s, int color, int scale ) { text_draw_centered( cx, y, s, color ); }

void text_number( int x, int y, int v, int color )
{
    int[ 16 ] digits;
    itoa( v, digits, 10 );
    text_draw( x, y, digits, color );
}

#endif
