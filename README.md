# Relics of Avabur: Clan Stats

A script that gathers stats on your [Relics of Avabur](http://www.avabur.com/?ref=12110) clan. This is *not* a turn-key solution! You'll need to be willing to get your hands a little dirty. 

The latest version supports the new API introduced with the 2018 game update.

## Getting Started

* Put the two scripts on a machine somewhere.
* Make it run periodically either with a cronjob or manually.
* Post an HTML page showing the results.

### Prerequisites

The scripts are written in Python 3 and use SQLite as the storage engine.

### Installing

Just copy the scripts where you want them and run them. There is one file that is not in the repository, though.

You need to create a `settings.json` file matching the following structure:

```
{
	"username": "XXX",
	"password": "YYY",
	"dbfile": "/path/to/database/avabur.db",
	"csvdir": "/path/to/final/csv/files"
}
```

You need to log in as a real user to collect the data. This will log you out of any other sessions.

The code currently uses absolute paths because of how cronjobs work. You will need to edit those as appropriate.

There are also three other settings you can set to change how the graphs are rendered:

  * `actions_total_whatiswide`: Applies to the "Total Clan Actions" graph. Determines how wide the swing has to be to trim it. Defaults to 500000. (Swings are caused by membership changes.)
  * `actions_average_whatiswide`: Applies to the "Average Clan Actions" graph. Determines how wide the swing has to be to trim it. Defaults to 50000. (Swings are caused by membership changes.)
  * `actions_outliers_percent`: Applies to the individual average and median actions graphs. Determines how much to chop off each end of the player's action counts before calculating the average/median. Defaults to 0.1 (10%).

Currently, the defaults are hard coded into the HTML file. So if you change them, you'll want to update the graph captions where appropriate. Sorry. One day I'll automate that.

## Graphs

The current version displays the following graphs and tables:

  * Daily clan XP gain 
  * Individual xp donated
  * Average clan actions (big swings are trimmed; swings happen as membership changes)
  * Individual total actions
  * Average daily actions per user (top and bottom 10% ignored)
  * Median daily actions per user (top and bottom 10% ignored)
  * Aggregate platinum donations
  * Individual platinum donations
  * Aggregate gold donations
  * Individual gold donations
  * Clan treasury levels
  * Table listing clan members with top-100 ranks in various skills
  * Member inactivity
  * Battler/TS ratio (the ratio of battling actions and crafting/profession actions)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## ToDo

  - [ ] Make `index.html` update the captions based on settings.
  - [X] Fix the code so it ignores applicants.
