// Music and sound effects. PLACEHOLDER: silent. The music and sfx groups replace this file,
// keeping these names.
#ifndef SOUND_H
#define SOUND_H

#define SONG_NONE      -1
#define SONG_TITLE     0      // title and menu
#define SONG_BATTLE    1
#define SONG_WROCLAW   2      // chapter 1 stages
#define SONG_SLEZA     3      // chapter 2 stages
#define SONG_KRAKOW    4      // chapter 3 stages
#define SONG_BOSS      5      // utopiec and Baba Jaga
#define SONG_DRAGON    6
#define SONG_CALM      7      // story scenes: a still moment
#define SONG_TENSION   8      // story scenes: a threat
#define SONG_JOY       9      // story scenes: the feast, the ending
#define SONG_COUNT     10

void sound_init() {}

// starts a song (looping); the same song again keeps playing; crossfades from the last one
void music_play( int song ) {}
void music_stop() {}

// once a frame: plays the effects the game raised in events[] (state.h) and runs the music
void sound_frame() {}

// a short UI sound: menu move and confirm, and the blip of a typed letter in a scene
#define UI_MOVE        0
#define UI_CONFIRM     1
#define UI_TYPE        2
void ui_sound( int which ) {}

#endif
