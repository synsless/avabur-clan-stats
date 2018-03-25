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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
