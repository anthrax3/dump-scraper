__author__ = 'Davide Tampellini'
__copyright__ = '2015 Davide Tampellini - FabbricaBinaria'
__license__ = 'GNU GPL version 3 or later'

import argparse
import json
import logging
import logging.handlers
from colorlog import ColoredFormatter
from os import path as os_path
from requests import get as requests_get
from textwrap import dedent as textwrap_dedent
from lib.exceptions import exceptions
from distutils.version import StrictVersion

# Sadly there is a problem with shipping the certificate in the single executable, so I have to skip HTTPS verification
# This is turn will raise an InsecureRequestWarning, so we have to suppress it
# It's an ugly workaround while we found a way to make HTTPS connection work...
try:
    from requests import packages as requests_packages
    requests_packages.urllib3.disable_warnings()
except ImportError:
    # Guess what? Under Linux I don't have the packages attribute
    pass

class DumpScraper:
    def __init__(self):

        self.settings = None
        self.version = '0.2.0'

        parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=textwrap_dedent('''
Dump Scraper - A better way of scraping
 This is the main entry point of Dump Scraper, where you can perform all the actions.
 Type:
    dumpscraper [command] [options]
 to run a specific command

 Type:
    dumpscraper [command] -h
 to display the help for the specific command
        '''))

        parser.add_argument('--verbose', action='store_true', help="Verbose flag")

        subparsers = parser.add_subparsers(dest='command')

        subparsers.add_parser('scrape')

        parser_getscore = subparsers.add_parser('getscore')
        parser_getscore.add_argument('-s', '--since',
                                     help='Starting date for the analysis, format YYYY-MM-DD',
                                     required=True)
        parser_getscore.add_argument('-u', '--until',
                                     help='Stopping date for the analysis, format YYYY-MM-DD. If not supplied only the SINCE date will be processed')
        parser_getscore.add_argument('-f', '--force',
                                     help="Force a specific dump filename to process, used for debug only")
        parser_getscore.add_argument('-l', '--level',
                                     help='How greedy we want to be. Higher level will give you more results, but also more false positives',
                                     default=1,
                                     type=int,
                                     choices=[1, 2, 3])

        parser_training = subparsers.add_parser('training')
        parser_training.add_argument('-d', '--getdata',
                                     help='Move some dump files interactively in order to create training data',
                                     action='store_true')
        parser_training.add_argument('-s', '--getscore',
                                     help='Create the score for the training data',
                                     action='store_true')

        parser_classify = subparsers.add_parser('classify')
        parser_classify.add_argument('-s', '--since',
                                     help='Starting date for the analysis, format YYYY-MM-DD',
                                     required=True)
        parser_classify.add_argument('-f', '--force',
                                     help="Force a specific dump filename to process, used for debug only")
        parser_classify.add_argument('-u', '--until',
                                     help='Stopping date for the analysis, format YYYY-MM-DD. If not supplied only the SINCE date will be processed')
        parser_classify.add_argument('-c', '--clean',
                                     help='Before moving the dumps of a day, clears the entire folder',
                                     action='store_true')
        parser_classify.add_argument('-l', '--level',
                                     help='How greedy we want to be. Higher level will give you more results, but also more false positives',
                                     default=1,
                                     type=int,
                                     choices=[1, 2, 3])

        parser_extract = subparsers.add_parser('extract')
        parser_extract.add_argument('-s', '--since',
                                    help='Starting date for the analysis, format YYYY-MM-DD',
                                    required=True)
        parser_extract.add_argument('-u', '--until',
                                    help='Stopping date for the analysis, format YYYY-MM-DD. If not supplied only the SINCE date will be processed')
        parser_extract.add_argument('-f', '--force',
                                    help="Force a specific dump filename to process, used for debug only")
        parser_extract.add_argument('-c', '--clean',
                                    help='Before extracting the dumps of a day, clears the entire folder',
                                    action='store_true')

        parser_review = subparsers.add_parser('review')
        parser_review.add_argument('-d', '--dir',
                                   help='Date to analyze, format YYYY-MM-DD',
                                   required=True)

        self.args = parser.parse_args()

        # Logging information
        # TODO - Add a rotation logic
        dump_logger = logging.getLogger('dumpscraper')
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s|%(levelname)-8s: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            filename='dumpscraper.log')

        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG if self.args.verbose else logging.INFO)

        formatter = ColoredFormatter("%(log_color)s[%(levelname)-4s] %(message)s%(reset)s")
        console.setFormatter(formatter)
        dump_logger.addHandler(console)

        # Let's silence the requests package logger
        logging.getLogger("requests").setLevel(logging.WARNING)

        if self.args.command == 'training':
            self.args.force = None
            if not self.args.getdata and not self.args.getscore:
                dump_logger.error("With the [training] command you have to supply the [getdata] or [getscore] argument")
                from sys import exit
                exit(2)

    def banner(self):
        print("Dump Scraper " + self.version + " - A better way of scraping")
        print("Copyright (C) 2015 FabbricaBinaria - Davide Tampellini")
        print("===============================================================================")
        print("Dump Scraper is Free Software, distributed under the terms of the GNU General")
        print("Public License version 3 or, at your option, any later version.")
        print("This program comes with ABSOLUTELY NO WARRANTY as per sections 15 & 16 of the")
        print("license. See http://www.gnu.org/licenses/gpl-3.0.html for details.")
        print("===============================================================================")

    def checkenv(self):
        if not os_path.exists(os_path.realpath("settings.json")):
            raise exceptions.InvalidSettings("Please rename the file settings-dist.json to settings.json and fill the required info")

        json_data = open(os_path.realpath("settings.json"))
        settings = json.load(json_data)
        json_data.close()

        # At the moment there aren't required key, let's leave this check for future use
        required_keys = []

        for required in required_keys:
            try:
                value = settings[required]

                if value == '':
                    raise exceptions.InvalidSettings("Please fill the required info '" + required + "' before continuing")

            except KeyError:
                raise exceptions.InvalidSettings("Please fill the required info '" + required + "' before continuing")

        try:
            if not settings['data_dir']:
                settings['data_dir'] = os_path.realpath("data/raw/")
            else:
                if not os_path.exists(settings['data_dir']):
                    logging.getLogger('dumpscraper').warn("Path " + settings['data_dir'] + " does not exist, using the default 'data/raw' one")
                    settings['data_dir'] = os_path.realpath("data/raw/")
        except KeyError:
            settings['data_dir'] = os_path.realpath("data/raw/")

        self.settings = settings

    def check_updates(self):
        r = requests_get('https://api.github.com/repos/tampe125/dump-scraper/releases/latest')
        json_data = json.loads(r.content)

        if StrictVersion(json_data['tag_name']) > StrictVersion(self.version):
            logging.getLogger('dumpscraper').warn("A new version is available, please download it from https://github.com/tampe125/dump-scraper/releases")

    def run(self):
        self.banner()
        self.check_updates()

        dump_logger = logging.getLogger('dumpscraper')

        # Peform some sanity checks
        try:
            self.checkenv()
        except exceptions.InvalidSettings as error:
            dump_logger.error(error)
            return

        # Let's ouput some info

        if hasattr(self.args, 'level') and self.args.level > 0:
            dump_logger.debug('\tUsing a greedy level of ' + str(self.args.level))

        if hasattr(self.args, 'clean') and self.args.clean:
            dump_logger.debug("\tClean the target folder before attempting to write inside it")

        if hasattr(self.args, 'force') and self.args.force:
            dump_logger.debug("\tForcing the execution only on file " + str(self.args.force))

        # Let's load the correct object
        if self.args.command == 'scrape':
            from lib.runner import scrape
            runner = scrape.DumpScraperScrape(self.settings, self.args)
        elif self.args.command == 'getscore':
            from lib.runner import getscore
            runner = getscore.DumpScraperGetscore(self.settings, self.args)
        elif self.args.command == 'training':
            from lib.runner import training
            runner = training.DumpScraperTraining(self.settings, self.args)
        elif self.args.command == 'classify':
            from lib.runner import classify
            runner = classify.DumpScraperClassify(self.settings, self.args)
        elif self.args.command == 'extract':
            from lib.runner import extract
            runner = extract.DumpScraperExtract(self.settings, self.args)
        elif self.args.command == 'review':
            from lib.runner import review
            runner = review.DumpScraperReview(self.settings, self.args)
        else:
            dump_logger.error("Unrecognized command " + self.args.command)
            return

        # And away we go!
        try:
            runner.check()
            runner.run()
        # Ehm.. something wrong happened?
        except exceptions.RunningError as error:
            dump_logger.error(error)
        # Always save the updated settings
        finally:
            with open(os_path.realpath("settings.json"), 'w+') as update_settings:
                json.dump(self.settings, update_settings, indent=4)


try:
    scraper = DumpScraper()
    logging.getLogger('dumpscraper').debug("=========================================")
    logging.getLogger('dumpscraper').debug("Application Started")
    logging.getLogger('dumpscraper').debug("=========================================")
    scraper.run()
except KeyboardInterrupt:
    print("")
    logging.getLogger('dumpscraper').info("Operation aborted")
