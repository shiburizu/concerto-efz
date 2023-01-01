# <img src="res/concertoicon.png" width="40"> Concerto for EFZ
* [**Project website**](https://concerto-efz.shib.live)

## About

Concerto is a graphical front end for EFZRevival.

To use it, just drop `Concerto.exe` in the same folder as EFZRevival. You need to be using the latest version of EFZRevival and your Revival executable needs to be named `EfzRevival.exe` to work by default.

Other players can connect to your online versus host without Concerto as long as they use the same version of EFZRevival.

For best usage don't open Efz.exe or EfzRevival.exe on their own while using this program.

HIGHLY EXPERIMENTAL SOFTWARE, ENJOY AND EXPECT BUGS

## Building
This project requires Python version 3.8

### Install dependencies
```
pip install -r requirements.txt
```

### Building with Pyinstaller
```
pyinstaller concerto.spec
```
This will bundle the `Concerto.exe` executable into the `dist/` directory.

#### "winpty-agent.exe" is sourced from [winpty](https://github.com/rprichard/winpty) because we target [pywinpty](https://github.com/spyder-ide/pywinpty) version 0.5.7 for back compatibility to Windows 7 SP1. You may build and run Concerto using the latest version of pywinpty and exclude the .exe however the resulting build will only function on Windows 10.

## Customizing UI
It is possible to change the character art and background images by placing certain image file names in your EFZ game directory.

* Each character art is the name of its respective screen: Main.png, Online.png, Resources.png
* Each background art is the name of its respective screen suffixed with _bg, i.e. Main_bg.png

Each image is loaded directly onto the screen. For best results, make sure all images are 600x400px and keep in mind character arts are rendered above all other UI elements. See included files for examples.

## Audio/Visual sources
Art & sound are provided by community members for exclusive use with Concerto.

### Visuals
* UI direction in cooperation with [okk](https://github.com/okkdev) and [M-AS](https://twitter.com/matthewrobo)
* Backgrounds sourced from Unsplash

### Audio
* "Soubrette's Walkway" by [Tempxa](https://twitter.com/TempxaRK9)

## Known Issues
* Not all error messages shown by EFZRevival may appear in Concerto.
* Emojis in text will not render correctly.

## Roadmap
### 1.0.0
* Online Lobbies
* Battle Log
* Search Player/Matchup

### 1.1.0
* Discord Presence re-implemented
* Date/Time search in Battle Log
* Dedicated lobby link support

### Version TBD
* Dedicated lobby link support
* Keybinding Menu
* Quick Match