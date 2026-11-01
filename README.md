# SLRE WebEngine
### Simple Lightweight Rendering Engine
SLRE is an simple and independent web rendering engine that is designed to load simple text-based websites, single image sites or reading. Although it couldn't do much, it uses only about **20~80 MB of RAM**, according to macOS Activity Monitor.

---
## Features
- **Custom Rendering Engine**: Supports Minimal JavaScript, Text Styling, images and links
- **JavaScript Support**: As mentioned before, SLRE can load minimal Javascript including Buttons, Textboxes, links and interactive elements using js2py.
- **Appearance**: You can choose between Dark or Light mode.
- **Search**: DuckDuckGo Lite or FrogFind!. DuckDuckGo is a bit buggy but has a massive search index. FrogFind! is less buggy but has less pages and often not work.
- **Custom Pages**: Built-in slre://home and slre://about pages.

---
## Installation
Remember, you will need to **install Python** before you can proceed.
You will also need:
- PyQt6 v6.0.0 or later
- js2py v0.71 or later
- psutil v5.0.0 or later
1. Clone the Repo:
 ```bash
 git clone https://github.com/DanDevProjects/slre-webengine.git
 ```
2. Navigate to the directory:
   ```bash
   cd slre-webengine
   ```
3. Install Dependencies:
```bash
python3 -m pip install pyqt6 & python3 -m pip install js2py & python3 -m pip install psutil
```
4. Run now!
```bash
python3 slre.py
```
## Compile Application (Optional)
If you want to compile the file into an standalone app, follow the instructions below:
1. Install PyInstaller
```bash
python3 -m pip install PyInstaller
```
2. Use PyInstaller to compile the app
First navigate to the folder with slre.py in it
```
cd slre-webengine
```
Then, compile
```
pyinstaller --noconsole --onefile slre.py
```
--noconsole: launches as a standalone application.
Remove the flag if you like to debug or see logs.

--onefire or onedir: choose between one file or one directory.

--icon=: add this flag if you would like to add an icon.

4. Find Your App
PyInstaller will create 2 new folders named "dist" and "build". Navigate to the list folder, and click on the executable file.
- .exe: Windows
- .app: macOS
- No file extension shown: Linux (Will display as a executable file)

5. Start using
You can first type in your search query or URL on the search bar and press enter or click on Go.

## Pros
- **Lightweight Size**: This browser only consumes about 20~80 MB of RAM, similar to Dillo Browser.
- **Security**: Zero telemetry and Open-Source.
- **Independent**: Built on its very own WebEngine called SLRE (Simple Lightweight Rendering Engine).
- **Simplicity**: No menu-inside-of-menus or multiple buttons just for one setting.
- **Portability**: You can run this browser on anything that supports the required dependencies.

## Cons
- **No Tab Browsing**: You cannot open tabs. If a link automatically directs you to a new tab, SLRE Browser will open in a new window.
- **Minimal JavaScript**: If you didn't install js2py, that's fine. It will just load websites without JS. If you did, the browser still couldn't load most modern or complex websites.
- **Small font library**: The engine couldn't load most fonts and only has a tiny amount of fonts.
- **Lack of advanced styling**: Couldn't load any styling, everything will default to the left.
- **Customization**: You cannot customize anything except the theme and then search engine (requires a search engine pack).

## License
This Project uses the MIT License. You can read it in LICENSE.md.

## Contribution
You can read the Contributing.md file.

## Recommendations
You are welocme to recommend features, updates or bug fixes.
