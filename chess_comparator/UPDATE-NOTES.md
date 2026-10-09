ROBOCHESS — UPDATE NOTES
Updated: October 9, 2026

RECENT CHANGES

- Fixed a startup crash in the Lichess Video Library. The error was:
  TypeError: LichessVideo.__init__() got an unexpected keyword argument 'close_callback'
  It happened when a newer app.py was used with an older lichess_video.py. The application passed close_callback, but the older module did not accept it. The application and video-module files are now synchronized. Install files from the same update together. Do not mix app.py and lichess_video.py from different versions.

- Added a Close Videos control to the Lichess Video Library. It stops and closes the temporary video view and returns to the Study screen. This view is limited to the video library. Lichess login and game pages are blocked. The analysis board remains available beside the video.

- Added an automatic DGT board reset. When every piece is returned to its standard starting square, RoboChess resets the game, stops the engine and the clock, and restores White to move. Temporary piece lifts and incomplete placements are ignored. The reset is unavailable in editor, puzzle, review, Engine Match, and Quad tournament modes.

- Localized the Game > Personalities dialog for English and Spanish. Controls, champion titles, countries, and playing-style descriptions are translated for all 18 grandmasters. Names, Elo values, and algebraic opening statistics are unchanged.

FEATURES IN THIS BUILD

- Compare engine analysis, including Stockfish candidate lines and Crafty's principal line, with an evaluation bar and board arrows.
- Save analysis as PGN or text for later review in other chess software.
- Play against configured engines, use game clocks and game controls, and review training progress with local profiles and tutor feedback.
- Connect a DGT Smart Board through its serial port and enter moves on the physical board.
- Use the chess resources and exercises bundled with the project, including opening books, piece styles, endgame tables, and training positions.

SETUP NOTES

- Keep the folder structure when extracting an update.
- For the Lichess crash fix, update the matching app.py and lichess_video.py files together.
- DGT use requires a working DGT driver and the optional dependencies listed in requirements-dgt.txt. The embedded video library may require the Windows WebView2 Runtime.
- Engine strength and analysis depend on the selected engine, its settings, and the available search time. Elo settings are approximate and are not an official rating.
