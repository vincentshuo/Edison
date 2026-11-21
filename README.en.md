# Edison

Edison brings the YouTube reading library and Curriculum into one workspace.

The YouTube module hosts Daily Signal reports. Place original HTML files under `surfaces/gui/public/youtube/Channel/<channel>/`. On macOS, `scripts/daily_signal/install_watcher.sh` installs the 60-second quiet-window watcher. It indexes reports, commits the feed and publishes it to [Edison on GitHub Pages](https://vincentshuo.github.io/Edison/youtube/).

Reports retain their original layout. The channel selector and All, Unread, Read and Featured views operate on the index. Reading selections are stored in the current browser.

See the [project README](README.md) for build and development instructions.
