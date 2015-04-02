__author__ = 'Davide Tampellini'
__copyright__ = '2015 Davide Tampellini - FabbricaBinaria'
__license__ = 'GNU GPL version 3 or later'

import re
from lib.detector.abstract import AbstractDetector


class HashDetector(AbstractDetector):
    def __init__(self):
        self.functions = {
            'fewLines'       : 1,
            'longLines'      : 1,
            'detectMd5'      : 1,
            'detectMd5Crypt' : 1,
            'detectSha512Crypt' : 1,
            'phpassMd5'      : 1,
            'phpassGen'      : 1,
            'detectSha1'     : 1,
            'detectMySQL'    : 1,
            'detectCrypt'    : 1,
            'detectDrupal'   : 1,
            'detectBlowfish' : 1,
        }

        super(HashDetector, self).__init__()

        # Let's compile some regexes to speed up the execution
        self.regex['md5'] = re.compile('[a-f0-9]{32}', re.I | re.M)
        # Example (unsalted) $1$sCGfZOwq$K9M3ULuacSQln/e3/KnPN.
        self.regex['md5Crypt'] = re.compile('\$1\$.{8}\$.{22}', re.I | re.M)
        self.regex['sha512Crypt'] = re.compile('\$6\$[a-z0-9./]{8}\$[a-z0-9./]+', re.I | re.M)
        # Example $H$9V1cX/WqUhsSWM0ipyB7HwFQqTQKxP1
        self.regex['phpassMd5'] = re.compile('\$H\$9.{30}', re.M)
        # Example $P$B52zg0z/Y5e96IpD4KJ7a9ByqcrKb01
        self.regex['phpassGen'] = re.compile('\$P\$.{31}', re.M)
        self.regex['sha1'] = re.compile('\b[0-9a-f]{40}\b', re.I | re.M)
        self.regex['mysql'] = re.compile('\*[a-f0-9]{40}', re.I | re.M)
        self.regex['crypt'] = re.compile('[\s\t:][a-zA-Z0-9/\.]{13}[,\s\n]?$', re.M)
        # Drupal $S$DugG4yZmhfIGhNJJZMzKzh4MzOCkpsPBR9HtDIvqQeIyqLM6wyuM
        self.regex['drupal'] = re.compile('\$S\$[a-zA-Z0-9/\.]{52}', re.M)
        self.regex['blowfish'] = re.compile('\$2[axy]?\$[a-zA-Z0-9./]{8}\$[a-zA-Z0-9./]+', re.M)

    def analyze(self, results):
        # If the Trash Detector has an high value, don't process the file, otherwise we could end up with a false positive
        # Sadly debug files LOVE to use hashes...
        if results['trash'] >= 0.95:
            self.score = 0
            return
        
        for function, coefficient in self.functions.iteritems():
            score = getattr(self, function)() * coefficient
            
            # Did I get a negative score? This means that this file is NOT an hash one!
            # Set the global score to 0 and stop here
            if score < 0:
                self.score = 0
                break
                
            self.score += score
            
            # I already reached the maximum value, there's no point in continuing
            if self.score >= 3:
                break

    def returnkey(self):
        return 'hash'
    
    def fewLines(self):
        # If I just have few lines, most likely it's trash. I have to do this since sometimes some debug output are
        # crammed into a single line, screwing up all the stats
        if self.lines < 3:
            return -1
        
        return 0
    
    def longLines(self):
        lines = self.data.split("\n")

        for line in lines:
            if len(line) > 1000:
                return -1

        return 0

    def detectMd5(self):
        hashes = len(re.findall(self.regex['md5'], self.data))

        return hashes / self.lines

    def detectMd5Crypt(self):
        hashes = len(re.findall(self.regex['md5Crypt'], self.data))

        return hashes / self.lines

    def detectSha512Crypt(self):
        hashes = len(re.findall(self.regex['sha512Crypt'], self.data))

        return hashes / self.lines

    def phpassMd5(self):
        hashes = len(re.findall(self.regex['phpassMd5'], self.data))

        return hashes / self.lines

    def phpassGen(self):
        hashes = len(re.findall(self.regex['phpassGen'], self.data))

        return hashes / self.lines

    def detectSha1(self):
        hashes = len(re.findall(self.regex['sha1'], self.data))

        return hashes / self.lines

    def detectMySQL(self):
        hashes = len(re.findall(self.regex['mysql'], self.data))

        return hashes / self.lines

    def detectCrypt(self):
        # Sadly the crypt hash is very used and has a very common signature, this means that I can't simply search for it
        # in the whole document, or I'll have TONS of false positive. I have to shrink the range using more strict regex
        hashes = len(re.findall(self.regex['crypt'], self.data))

        return hashes / self.lines

    def detectDrupal(self):
        hashes = len(re.findall(self.regex['drupal'], self.data))

        return hashes / self.lines

    def detectBlowfish(self):
        hashes = len(re.findall(self.regex['blowfish'], self.data))

        return hashes / self.lines