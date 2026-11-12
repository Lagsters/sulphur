// Entry point of the Vircon32 web emulator for Sulphur.
// Replaces upstream WebEmulator's Main.cpp, GUI.cpp and Settings.cpp (they need Dear ImGui and
// run a blocking loop); the startup sequence and the frame loop follow upstream Main.cpp.
// Added on top of upstream: browser gamepads (Gamepad API) and a memory card kept in IndexedDB.
#include "ConsoleLogic/V32Console.hpp"
#include "DesktopInfrastructure/Logger.hpp"
#include "EmulatorControl.hpp"
#include "GamepadsInput.hpp"
#include "VideoOutput.hpp"
#include "AudioOutput.hpp"
#include "GUI.hpp"
#include "Globals.hpp"
#include "StopWatch.hpp"

#include <emscripten.h>
#include <emscripten/html5.h>
#include <exception>
#include <string>

using namespace std;
using namespace V32;

static const char* MemoryCardPath = "/save/sulphur.memc";
static StopWatch Watch;
static float PendingFrames = 1;
static int EmulatedFrames = 0;
static bool BrowserPadHeld[ Constants::GamepadPorts ][ 11 ];

extern "C" EMSCRIPTEN_KEEPALIVE int web_emulated_frames() { return EmulatedFrames; }

static void ShowError( const string& Message )
{
    LOG( "ERROR: " + Message );
    EM_ASM( { if( Module.onEmulatorError ) Module.onEmulatorError( UTF8ToString( $0 ) ); }, Message.c_str() );
}

// browser gamepad N drives console port N (port 0 is shared with the keyboard); buttons follow
// the Gamepad API "standard" layout: bottom face button is A, right B, left X, top Y
static void PollBrowserGamepads()
{
    if( emscripten_sample_gamepad_data() != EMSCRIPTEN_RESULT_SUCCESS ) return;
    int Count = emscripten_get_num_gamepads();

    for( int Port = 0; Port < Constants::GamepadPorts; Port++ )
    {
        EmscriptenGamepadEvent State;
        bool Present = Port < Count && emscripten_get_gamepad_status( Port, &State ) == EMSCRIPTEN_RESULT_SUCCESS
                       && State.connected;
        if( Port > 0 && Present != Console.HasGamepad( Port ) )
          Console.SetGamepadConnection( Port, Present );
        if( !Present ) continue;

        auto Button = [&]( int i ) { return i < State.numButtons && State.digitalButton[ i ]; };
        auto Axis = [&]( int i ) { return i < State.numAxes ? State.axis[ i ] : 0.0; };
        bool Held[ 11 ];
        Held[ (int)GamepadControls::Left ]        = Button( 14 ) || Axis( 0 ) < -0.5;
        Held[ (int)GamepadControls::Right ]       = Button( 15 ) || Axis( 0 ) > 0.5;
        Held[ (int)GamepadControls::Up ]          = Button( 12 ) || Axis( 1 ) < -0.5;
        Held[ (int)GamepadControls::Down ]        = Button( 13 ) || Axis( 1 ) > 0.5;
        Held[ (int)GamepadControls::ButtonStart ] = Button( 9 );
        Held[ (int)GamepadControls::ButtonA ]     = Button( 0 );
        Held[ (int)GamepadControls::ButtonB ]     = Button( 1 );
        Held[ (int)GamepadControls::ButtonX ]     = Button( 2 );
        Held[ (int)GamepadControls::ButtonY ]     = Button( 3 );
        Held[ (int)GamepadControls::ButtonL ]     = Button( 4 );
        Held[ (int)GamepadControls::ButtonR ]     = Button( 5 );

        // only changes are sent, so on port 0 the keyboard keeps working next to the gamepad
        for( int Control = 0; Control < 11; Control++ )
        {
            if( Held[ Control ] == BrowserPadHeld[ Port ][ Control ] ) continue;
            BrowserPadHeld[ Port ][ Control ] = Held[ Control ];
            Console.SetGamepadControl( Port, (GamepadControls)Control, Held[ Control ] );
        }
    }
}

static void SaveMemoryCardIfModified()
{
    if( !Console.HasMemoryCard() || !Console.WasMemoryCardModified() ) return;
    Console.SaveMemoryCard();
    EM_ASM( FS.syncfs( false, function( Error ) { if( Error ) console.warn( "memory card not saved", Error ); } ); );
}

// same as upstream GUI.cpp, without the menu overlay
void ShowEmulatorWindow()
{
    glEnable( GL_BLEND );
    GPUColor PreviousMultiplyColor = Video.GetMultiplyColor();
    IOPortValues PreviousBlendingMode = Video.GetBlendingMode();
    Video.SetMultiplyColor( GPUColor{ 255, 255, 255, 255 } );
    Video.SetBlendingMode( IOPortValues::GPUBlendingMode_Alpha );
    Video.RenderToScreen();

    if( Emulator.IsPowerOn() )
      Video.DrawFramebufferOnScreen();
    else
      Video.ClearScreen( GPUColor{ 0, 0, 0, 255 } );

    Video.SetMultiplyColor( PreviousMultiplyColor );
    Video.SetBlendingMode( PreviousBlendingMode );
}

static void RunFrame()
{
    try
    {
        SDL_Event Event;
        while( SDL_PollEvent( &Event ) )
        {
            if( Event.type == SDL_KEYDOWN && !Event.key.repeat && Event.key.keysym.sym == SDLK_F5 )
              Emulator.Reset();
            Gamepads.ProcessEvent( Event );
        }
        PollBrowserGamepads();

        Video.RenderToFramebuffer();
        Video.BeginFrame();

        // emulate at 60 fps whatever the display rate; after a stall (hidden tab)
        // catch up by a few frames at most instead of fast-forwarding
        PendingFrames += Watch.GetStepTime() * 60.0;
        if( PendingFrames > 3 ) PendingFrames = 3;
        if( PendingFrames < 0.9 ) return;

        while( PendingFrames >= 0.9 )
        {
            Emulator.RunNextFrame();
            EmulatedFrames++;
            PendingFrames -= 1;
        }

        ShowEmulatorWindow();
        SDL_GL_SwapWindow( Video.GetWindow() );

        // a game saves rarely; checking every second keeps IndexedDB writes cheap
        if( EmulatedFrames % 60 == 0 )
          SaveMemoryCardIfModified();
    }
    catch( const exception& e )
    {
        ShowError( e.what() );
        emscripten_cancel_main_loop();
    }
}

static void LoadMemoryCard()
{
    try
    {
        FILE* Existing = fopen( MemoryCardPath, "rb" );
        if( Existing ) fclose( Existing );
        else Console.CreateMemoryCard( MemoryCardPath );
        Console.LoadMemoryCard( MemoryCardPath );
    }
    catch( const exception& e )
    {
        // the game still runs without a card, it only cannot save
        LOG( string( "memory card unavailable: " ) + e.what() );
    }
}

// the page mounts /save from IndexedDB and puts the cartridge in the file system before main()
int main( int NumberOfArguments, char* Arguments[] )
{
    string CartridgePath = NumberOfArguments > 1 ? Arguments[ 1 ] : "/sulphur.v32";

    try
    {
        LOG_TO_CONSOLE();
        EmulatorFolder = "/";
        InitializeGlobalVariables();

        if( SDL_Init( SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_TIMER | SDL_INIT_EVENTS ) != 0 )
          THROW( string( "Cannot initialize SDL: " ) + SDL_GetError() );

        Video.CreateOpenGLWindow();
        Video.InitRendering();
        Video.CreateFramebuffer();
        Video.RenderToScreen();
        glEnable( GL_BLEND );
        Video.SetBlendingMode( IOPortValues::GPUBlendingMode_Alpha );

        // upstream SetDefaultSettings(): keyboard on port 0, other ports empty
        Audio.SetMute( false );
        Audio.SetOutputVolume( 1.0 );
        Console.SetGamepadConnection( 0, true );
        Gamepads.MappedGamepads[ 0 ].Type = DeviceTypes::Keyboard;
        for( int i = 1; i < Constants::GamepadPorts; i++ )
        {
            Console.SetGamepadConnection( i, false );
            Gamepads.MappedGamepads[ i ].Type = DeviceTypes::NoDevice;
        }

        Emulator.Initialize();
        Console.LoadBios( EmulatorFolder + "Bios/" + BiosFileName );
        Console.LoadCartridge( CartridgePath );
        LoadMemoryCard();
        Emulator.SetPower( true );
    }
    catch( const exception& e )
    {
        ShowError( e.what() );
        return 1;
    }

    // 0 = browser's own rate (requestAnimationFrame); RunFrame keeps the console at 60 fps
    emscripten_set_main_loop( RunFrame, 0, false );
    return 0;
}
