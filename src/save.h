// The story's progress and the language on the memory card; without a card they live until
// the console is switched off.
#ifndef SAVE_H
#define SAVE_H

#include "state.h"

#define SAVE_WORDS 4
#define SAVE_AT    20       // the data follows the game signature (game_signature: 20 words)

game_signature save_signature = "SULPHUR SAVE 1";
int[ SAVE_WORDS ] save_data;    // stage reached (0 = none), language

int saved_stage = 0;

void load_save()
{
    if( !card_is_connected() || !card_signature_matches( &save_signature ) ) return;
    card_read_data( save_data, SAVE_AT, SAVE_WORDS );
    saved_stage = save_data[ 0 ];
    lang = save_data[ 1 ];
    if( lang != 1 ) lang = 0;
}

void write_save()
{
    if( !card_is_connected() ) return;
    save_data[ 0 ] = saved_stage;
    save_data[ 1 ] = lang;
    card_write_signature( &save_signature );
    card_write_data( save_data, SAVE_AT, SAVE_WORDS );
}

#endif
